import os, sys, tempfile
from PyQt6 import QtGui, QtWidgets, QtCore
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
import numpy as np

# IO adapters
try:
    from stegoio.image_io import load_image_rgb, save_image_rgb
    from stegoio.audio_io import load_wav_pcm16, save_wav_pcm16
except ModuleNotFoundError:
    from io.image_io import load_image_rgb, save_image_rgb  # type: ignore
    from io.audio_io import load_wav_pcm16, save_wav_pcm16  # type: ignore

from core.payload import pack_payload, try_unpack_partial
from core.capacity import image_capacity_bits, audio_capacity_bits
from core.image_lsb import encode_rgb, decode_rgb_all
from core.audio_lsb import encode_wav, decode_wav_all
from core.viz import difference_map, audio_difference_panel, render_audio_compare_panel, render_image_compare_panel


# ---------- helpers ----------
def to_qpixmap_from_pil(pil_img):
    data = pil_img.tobytes("raw", pil_img.mode)
    if pil_img.mode == "L":
        fmt = QtGui.QImage.Format.Format_Grayscale8
        qimg = QtGui.QImage(data, pil_img.width, pil_img.height, pil_img.width, fmt)
    else:
        qimg = QtGui.QImage(data, pil_img.width, pil_img.height, pil_img.width * 3,
                            QtGui.QImage.Format.Format_RGB888)
    return QtGui.QPixmap.fromImage(qimg)

def to_qpixmap_from_np_rgb(arr):
    h, w, c = arr.shape
    qimg = QtGui.QImage(arr.data, w, h, w * 3, QtGui.QImage.Format.Format_RGB888)
    return QtGui.QPixmap.fromImage(qimg.copy())

def to_text_pixmap(text, w=620, h=240):
    pm = QtGui.QPixmap(w, h); pm.fill(QtGui.QColor('black'))
    p = QtGui.QPainter(pm); p.setPen(QtGui.QColor('white')); p.drawText(10, h // 2, text); p.end()
    return pm


# ---------- pop-out dialogs ----------
class AudioCompareDialog(QtWidgets.QDialog):
    def __init__(self, cover_audio, stego_audio, sr=None, lsb=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Audio Compare (Cover vs Stego)")
        self.cover = cover_audio; self.stego = stego_audio; self.sr = sr; self.lsb = lsb
        self.imgLabel = QtWidgets.QLabel(); self.imgLabel.setMinimumSize(900, 540)
        self.imgLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.zoom = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal); self.zoom.setRange(1, 100); self.zoom.setValue(10)
        self.pan  = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal); self.pan.setRange(0, 1000); self.pan.setValue(0)
        closeBtns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close)
        closeBtns.rejected.connect(self.reject)
        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(self.imgLabel)
        lay.addWidget(QtWidgets.QLabel("Zoom (window length)")); lay.addWidget(self.zoom)
        lay.addWidget(QtWidgets.QLabel("Pan")); lay.addWidget(self.pan); lay.addWidget(closeBtns)
        self.zoom.valueChanged.connect(self._refresh); self.pan.valueChanged.connect(self._refresh)
        self._refresh()
    def _refresh(self):
        n = min(self.cover.shape[0], self.stego.shape[0])
        frac = max(1, self.zoom.value())/100.0
        length = max(512, int(n*frac)); start_max = max(0, n - length)
        start = int((self.pan.value()/1000.0)*start_max)
        panel = render_audio_compare_panel(self.cover, self.stego, start=start, length=length, sr=self.sr, lsb=self.lsb,
                                           width=900, height=540)
        self.imgLabel.setPixmap(to_qpixmap_from_pil(panel))

class ImageCompareDialog(QtWidgets.QDialog):
    def __init__(self, cover_img_np, stego_img_np, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image Compare (Cover vs Stego)")
        self.cover = cover_img_np; self.stego = stego_img_np
        self.imgLabel = QtWidgets.QLabel(); self.imgLabel.setMinimumSize(900, 540)
        self.imgLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.zoom = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal); self.zoom.setRange(1, 16); self.zoom.setValue(4)
        self.panX = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal); self.panY = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        H, W, _ = self.cover.shape; self.panX.setRange(0, max(0, W-1)); self.panY.setRange(0, max(0, H-1))
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close); btns.rejected.connect(self.reject)
        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(self.imgLabel)
        lay.addWidget(QtWidgets.QLabel("Zoom")); lay.addWidget(self.zoom)
        lay.addWidget(QtWidgets.QLabel("Pan X")); lay.addWidget(self.panX)
        lay.addWidget(QtWidgets.QLabel("Pan Y")); lay.addWidget(self.panY); lay.addWidget(btns)
        self.zoom.valueChanged.connect(self._refresh); self.panX.valueChanged.connect(self._refresh); self.panY.valueChanged.connect(self._refresh)
        self._refresh()
    def _refresh(self):
        panel = render_image_compare_panel(self.cover, self.stego, view_w=900, view_h=540,
                                           zoom=max(1, self.zoom.value()), pan_x=self.panX.value(), pan_y=self.panY.value())
        self.imgLabel.setPixmap(to_qpixmap_from_pil(panel))


# ---------- state ----------
class AppState:
    def __init__(self):
        # Encode
        self.cover_path = None
        self.cover_type = None      # 'image' or 'audio'
        self.cover_img = None       # HxWx3 uint8
        self.cover_audio = None     # (n,) or (n,ch) int16
        self.sr = None
        self.payload_path = None
        self.stego_img = None
        self.stego_audio = None
        # Decode
        self.decode_path = None
        self.decode_type = None
        self.decode_img = None
        self.decode_audio = None
        self.decode_sr = None
        # Audio player
        self.player = None
        self.audio_output = None


# ---------- bind ----------
def bind(window):
    s = AppState()

    # footer buttons
    window.openDiffPopupBtn = QtWidgets.QPushButton("Open Audio Compare"); window.openDiffPopupBtn.setEnabled(False)
    window.openImgCompareBtn = QtWidgets.QPushButton("Open Image Compare"); window.openImgCompareBtn.setEnabled(False)
    window.playAudioBtn = QtWidgets.QPushButton("▶ Play Stego Audio"); window.playAudioBtn.setEnabled(False)

    if hasattr(window, "diffPreviewEnc") and hasattr(window.diffPreviewEnc, "add_footer_widget"):
        window.diffPreviewEnc.add_footer_widget(window.openImgCompareBtn)
        window.diffPreviewEnc.add_footer_widget(window.openDiffPopupBtn)
        window.diffPreviewEnc.add_footer_widget(window.playAudioBtn)

    # ---------- capacity check ----------
    def update_capacity():
        lsb = window.lsbSpinEnc.value()
        if s.cover_type == 'image' and s.cover_img is not None:
            cap = image_capacity_bits(s.cover_img, lsb)
        elif s.cover_type == 'audio' and s.cover_audio is not None:
            cap = audio_capacity_bits(s.cover_audio, lsb)
        else:
            window.capacityLblEnc.setText("Capacity: -")
            return

        # payload size
        if window.payloadTabs.currentIndex() == 1:  # text
            plen = len(window.payloadTextEdit.toPlainText().encode("utf-8"))
        elif s.payload_path:
            plen = os.path.getsize(s.payload_path)
        else:
            plen = 0

        window.capacityLblEnc.setText(
            f"Capacity: {cap} bits (~{cap//8} bytes) | Payload: {plen} bytes"
        )

        if plen > cap//8:
            window.capacityLblEnc.setStyleSheet("color: red; font-weight: bold;")
        else:
            window.capacityLblEnc.setStyleSheet("")

    # ============== ENCODE TAB ==============
    def enc_load_cover(path):
        s.stego_img = None; s.stego_audio = None
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext in ('.bmp', '.png'):
                img = load_image_rgb(path)
                s.cover_img = img; s.cover_audio=None; s.cover_type='image'; s.sr=None
                window.imagePreviewEnc.setPixmap(to_qpixmap_from_np_rgb(img))
                window.diffPreviewEnc.setPixmap(QtGui.QPixmap())
                window.statusLblEnc.setText(f"Loaded cover: {os.path.basename(path)}")
                window.openImgCompareBtn.setEnabled(False); window.openDiffPopupBtn.setEnabled(False)
            elif ext == '.wav':
                audio, sr = load_wav_pcm16(path)
                s.cover_audio = audio; s.cover_img=None; s.cover_type='audio'; s.sr=sr
                window.imagePreviewEnc.setPixmap(to_text_pixmap(f"WAV: {audio.shape} @ {sr}Hz"))
                window.diffPreviewEnc.setPixmap(QtGui.QPixmap())
                window.statusLblEnc.setText(f"Loaded cover: {os.path.basename(path)}")
                window.openImgCompareBtn.setEnabled(False); window.openDiffPopupBtn.setEnabled(False)
            else:
                window.statusLblEnc.setText("Unsupported cover format. Use BMP/PNG or WAV.")
                return
            s.cover_path = path
            update_capacity()
        except Exception as e:
            window.statusLblEnc.setText(f"Failed to load cover: {e}")

    def enc_load_payload(path):
        s.payload_path = path
        window.statusLblEnc.setText(f"Payload loaded: {os.path.basename(path)}")
        update_capacity()

    def do_encode():
        if not s.cover_path:
            window.statusLblEnc.setText("Select a cover first.")
            return

        key = window.keySpinEnc.value()
        lsb = window.lsbSpinEnc.value()

        # File or Text payload
        use_text = (window.payloadTabs.currentIndex() == 1)
        if use_text:
            raw = window.payloadTextEdit.toPlainText().encode('utf-8')
            payload_mime = "text/plain"
            if not raw:
                window.statusLblEnc.setText("Text payload is empty.")
                return
        else:
            if not s.payload_path:
                window.statusLblEnc.setText("Select a payload file or use the Text tab.")
                return
            raw = open(s.payload_path, 'rb').read()
            payload_mime = "application/octet-stream"

        packed = pack_payload(raw, payload_mime, key_hint=(key % 1000003))

        try:
            if s.cover_type == 'image':
                stego = encode_rgb(s.cover_img, packed, lsb, key, region=None)
                s.stego_img = stego; s.stego_audio=None
                out = os.path.join(tempfile.gettempdir(), f"stego_{os.path.basename(s.cover_path)}.png")
                save_image_rgb(stego, out)
                window.imagePreviewEnc.setPixmap(to_qpixmap_from_np_rgb(stego))
                dm = difference_map(s.cover_img, stego)
                window.diffPreviewEnc.setPixmap(to_qpixmap_from_pil(dm))
                window.statusLblEnc.setText(f"Stego image saved → {out}")

                # wire image compare pop-out
                def _open_img_compare():
                    ImageCompareDialog(s.cover_img, stego, parent=window).exec()
                try: window.openImgCompareBtn.clicked.disconnect()
                except Exception: pass
                window.openImgCompareBtn.clicked.connect(_open_img_compare)
                window.openImgCompareBtn.setEnabled(True)
                window.openDiffPopupBtn.setEnabled(False)
                window.playAudioBtn.setEnabled(False)

            elif s.cover_type == 'audio':
                stego = encode_wav(s.cover_audio, lsb, key, packed, region=None)
                s.stego_audio = stego; s.stego_img=None
                out = os.path.join(tempfile.gettempdir(), f"stego_{os.path.basename(s.cover_path)}")
                save_wav_pcm16(out, stego, s.sr)
                panel_pil = audio_difference_panel(s.cover_audio, stego, sr=s.sr, lsb=lsb)
                window.diffPreviewEnc.setPixmap(to_qpixmap_from_pil(panel_pil))
                window.imagePreviewEnc.setPixmap(to_text_pixmap(f"Saved stego WAV → {out}"))
                window.statusLblEnc.setText(f"Stego WAV saved → {out}")

                # wire audio compare pop-out
                def _open_audio_compare():
                    AudioCompareDialog(s.cover_audio, stego, sr=s.sr, lsb=lsb, parent=window).exec()
                try: window.openDiffPopupBtn.clicked.disconnect()
                except Exception: pass
                window.openDiffPopupBtn.clicked.connect(_open_audio_compare)
                window.openDiffPopupBtn.setEnabled(True)
                window.openImgCompareBtn.setEnabled(False)

                # enable play stego audio
                def _play_audio():
                    if not s.player:
                        s.player = QMediaPlayer()
                        s.audio_output = QAudioOutput()
                        s.player.setAudioOutput(s.audio_output)
                    s.player.setSource(QtCore.QUrl.fromLocalFile(out))
                    s.player.play()

                try: window.playAudioBtn.clicked.disconnect()
                except Exception: pass
                window.playAudioBtn.clicked.connect(_play_audio)
                window.playAudioBtn.setEnabled(True)

            else:
                window.statusLblEnc.setText("Unsupported cover type.")
        except Exception as e:
            window.statusLblEnc.setText(f"Encode error: {e}")

    # ============== DECODE TAB ==============
    def dec_load_stego(path):
        s.decode_path = path
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext in ('.png', '.bmp'):
                s.decode_img = load_image_rgb(path); s.decode_audio=None; s.decode_type='image'; s.decode_sr=None
                window.imagePreviewDec.setPixmap(to_qpixmap_from_np_rgb(s.decode_img))
                window.statusLbl.setText(f"Loaded stego: {os.path.basename(path)}")
            elif ext == '.wav':
                a, sr = load_wav_pcm16(path)
                s.decode_audio = a; s.decode_img=None; s.decode_type='audio'; s.decode_sr=sr
                window.imagePreviewDec.setPixmap(to_text_pixmap(f"WAV: {a.shape} @ {sr}Hz"))
                window.statusLbl.setText(f"Loaded stego: {os.path.basename(path)}")
            else:
                window.statusLbl.setText("Unsupported stego format. Use PNG/BMP/WAV.")
        except Exception as e:
            window.statusLbl.setText(f"Failed to load stego: {e}")

    def do_decode():
        if not s.decode_path:
            window.statusLbl.setText("Drop a stego file first.")
            return
        key = window.keySpinDec.value()
        lsb = window.lsbSpinDec.value()
        try:
            if s.decode_type == 'image':
                blob = decode_rgb_all(s.decode_img, lsb, key, region=None, max_bits=None)
            elif s.decode_type == 'audio':
                blob = decode_wav_all(s.decode_audio, lsb, key, region=None, max_bits=None)
            else:
                window.statusLbl.setText("Unsupported stego type.")
                return

            meta, _ = try_unpack_partial(blob)
            if not meta:
                window.statusLbl.setText("Decode failed: No valid stego header found.")
                return
            if (meta.get('key_hint', 0) % 1000003) != (key % 1000003):
                window.statusLbl.setText("Decode failed: wrong key.")
                return

            ext_map = {
                "image/png": ".png", "image/bmp": ".bmp", "image/gif": ".gif",
                "audio/wav": ".wav", "text/plain": ".txt", "application/pdf": ".pdf",
            }
            ext = ext_map.get(meta.get("mime", ""), ".bin")
            out = os.path.join(tempfile.gettempdir(), "recovered_payload" + ext)
            with open(out, "wb") as f: f.write(meta["data"])
            window.statusLbl.setText(f"Decoded {meta.get('mime','unknown')} ({meta.get('length',0)} bytes) → {out}")

            # if audio payload, auto play button
            if meta.get("mime") == "audio/wav":
                def _play_decoded():
                    if not s.player:
                        s.player = QMediaPlayer()
                        s.audio_output = QAudioOutput()
                        s.player.setAudioOutput(s.audio_output)
                    s.player.setSource(QtCore.QUrl.fromLocalFile(out))
                    s.player.play()
                try: window.playAudioBtn.clicked.disconnect()
                except Exception: pass
                window.playAudioBtn.clicked.connect(_play_decoded)
                window.playAudioBtn.setText("▶ Play Decoded Audio")
                window.playAudioBtn.setEnabled(True)
            else:
                window.playAudioBtn.setEnabled(False)
        except Exception as e:
            window.statusLbl.setText(f"Decode error: {e}")

    # ---------- wire UI ----------
    window.encodeCoverDrop.fileDropped.connect(enc_load_cover)
    window.encodePayloadDrop.fileDropped.connect(enc_load_payload)
    window.encodeBtn.clicked.connect(do_encode)
    window.lsbSpinEnc.valueChanged.connect(lambda _: update_capacity())
    window.browseCoverBtn.clicked.connect(lambda: _browse_file(window, window.encodeCoverDrop))
    window.browsePayloadBtn.clicked.connect(lambda: _browse_file(window, window.encodePayloadDrop))

    window.decodeStegoDrop.fileDropped.connect(dec_load_stego)
    window.decodeBtn.clicked.connect(do_decode)
    window.browseStegoBtn.clicked.connect(lambda: _browse_file(window, window.decodeStegoDrop))

    return s


# ---------- file dialog helper ----------
def _browse_file(window, dropArea):
    path, _ = QtWidgets.QFileDialog.getOpenFileName(window, "Select File")
    if path:
        dropArea.fileDropped.emit(path)
