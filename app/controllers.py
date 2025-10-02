# app/controllers.py
import os, tempfile
from PyQt6 import QtGui, QtWidgets, QtCore
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # add parent dir to path for imports

# IO adapters
try:
    from stegoio.image_io import load_image_rgb, save_image_rgb
    from stegoio.audio_io import load_wav_pcm16, save_wav_pcm16
    from stegoio.video_io import load_video_frames, save_video_frames
    from stegoio.mime_utils import detect_mime_type, get_extension_from_mime
except ModuleNotFoundError:
    from stegoio.image_io import load_image_rgb, save_image_rgb  # type: ignore
    from stegoio.audio_io import load_wav_pcm16, save_wav_pcm16  # type: ignore
    from stegoio.video_io import load_video_frames, save_video_frames  # type: ignore


from core.payload import pack_payload, try_unpack_partial
from core.capacity import image_capacity_bits, audio_capacity_bits, video_capacity_bits
from core.image_lsb import encode_rgb, decode_rgb_all
from core.audio_lsb import encode_wav, decode_wav_all
from core.video_lsb import encode_video, decode_video_all
from core.viz import difference_map, audio_difference_panel, render_audio_compare_panel,render_image_compare_panel


# ---------------------- small helpers ----------------------

def to_qpixmap_from_pil(pil_img):
    """PIL -> QPixmap"""
    data = pil_img.tobytes("raw", pil_img.mode)
    if pil_img.mode == "L":
        fmt = QtGui.QImage.Format.Format_Grayscale8
        qimg = QtGui.QImage(data, pil_img.width, pil_img.height, pil_img.width, fmt)
    else:
        qimg = QtGui.QImage(data, pil_img.width, pil_img.height, pil_img.width * 3,
                            QtGui.QImage.Format.Format_RGB888)
    return QtGui.QPixmap.fromImage(qimg)

def to_qpixmap_from_np_rgb(arr):
    """np.uint8 HxWx3 RGB -> QPixmap"""
    h, w, c = arr.shape
    qimg = QtGui.QImage(arr.data, w, h, w * 3, QtGui.QImage.Format.Format_RGB888)
    return QtGui.QPixmap.fromImage(qimg.copy())

def to_text_pixmap(text, w=620, h=240):
    pm = QtGui.QPixmap(w, h)
    pm.fill(QtGui.QColor('black'))
    p = QtGui.QPainter(pm)
    p.setPen(QtGui.QColor('white'))
    p.drawText(10, h // 2, text)
    p.end()
    return pm


# ---------------------- audio compare dialog ----------------------

class AudioCompareDialog(QtWidgets.QDialog):
    """Pop-out: cover waveform, stego waveform, and difference with zoom/pan."""
    def __init__(self, cover_audio, stego_audio, sr=None, lsb=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Audio Compare (Cover vs Stego)")
        self.cover = cover_audio
        self.stego = stego_audio
        self.sr = sr
        self.lsb = lsb

        self.imgLabel = QtWidgets.QLabel()
        self.imgLabel.setMinimumSize(900, 540)
        self.imgLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.zoom = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.zoom.setRange(1, 100)   # 1%..100% of full length
        self.zoom.setValue(10)

        self.pan = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.pan.setRange(0, 1000)
        self.pan.setValue(0)

        closeBtns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close)
        closeBtns.rejected.connect(self.reject)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(self.imgLabel)
        lay.addWidget(QtWidgets.QLabel("Zoom (window length)"))
        lay.addWidget(self.zoom)
        lay.addWidget(QtWidgets.QLabel("Pan"))
        lay.addWidget(self.pan)
        lay.addWidget(closeBtns)

        self.zoom.valueChanged.connect(self._refresh)
        self.pan.valueChanged.connect(self._refresh)
        self._refresh()

    def _refresh(self):
        n_cover = self.cover.shape[0] if self.cover.ndim == 1 else self.cover.shape[0]
        n_stego = self.stego.shape[0] if self.stego.ndim == 1 else self.stego.shape[0]
        n = min(n_cover, n_stego)
        frac = max(1, self.zoom.value()) / 100.0
        length = max(512, int(n * frac))
        start_max = max(0, n - length)
        start = int((self.pan.value() / 1000.0) * start_max)

        panel = render_audio_compare_panel(self.cover, self.stego,
                                           start=start, length=length,
                                           sr=self.sr, lsb=self.lsb,
                                           width=900, height=540)
        self.imgLabel.setPixmap(to_qpixmap_from_pil(panel))

class ImageCompareDialog(QtWidgets.QDialog):
    """Pop-out: cover/stego/diff with zoom + pan for images."""
    def __init__(self, cover_img_np, stego_img_np, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image Compare (Cover vs Stego)")
        self.cover = cover_img_np
        self.stego = stego_img_np

        self.imgLabel = QtWidgets.QLabel()
        self.imgLabel.setMinimumSize(900, 540)
        self.imgLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.zoom = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.zoom.setRange(1, 16)   # 1x..16x
        self.zoom.setValue(4)

        self.panX = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.panY = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        H, W, _ = self.cover.shape
        self.panX.setRange(0, max(0, W - 1))
        self.panY.setRange(0, max(0, H - 1))

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(self.reject)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(self.imgLabel)
        lay.addWidget(QtWidgets.QLabel("Zoom"))
        lay.addWidget(self.zoom)
        lay.addWidget(QtWidgets.QLabel("Pan X"))
        lay.addWidget(self.panX)
        lay.addWidget(QtWidgets.QLabel("Pan Y"))
        lay.addWidget(self.panY)
        lay.addWidget(btns)

        self.zoom.valueChanged.connect(self._refresh)
        self.panX.valueChanged.connect(self._refresh)
        self.panY.valueChanged.connect(self._refresh)
        self._refresh()

    def _refresh(self):
        panel = render_image_compare_panel(
            self.cover, self.stego,
            view_w=900, view_h=540,
            zoom=max(1, self.zoom.value()),
            pan_x=self.panX.value(),
            pan_y=self.panY.value()
        )
        self.imgLabel.setPixmap(to_qpixmap_from_pil(panel))

# ---------------------- app state ----------------------

class AppState:
    def __init__(self):
        # Encode tab state
        self.cover_path = None
        self.cover_type = None      # 'image', 'audio', or 'video'
        self.cover_img = None       # np.uint8 HxWx3
        self.cover_audio = None     # np.int16 (n,) or (n,ch)
        self.cover_video = None     # np.uint8 FxHxWx3
        self.sr = None
        self.fps = None
        self.payload_path = None
        self.payload_text = None
        self.stego_img = None
        self.stego_audio = None
        self.stego_video = None
        # Decode tab state
        self.decode_path = None
        self.decode_type = None
        self.decode_img = None
        self.decode_audio = None
        self.decode_video = None
        self.decode_sr = None
        self.decode_fps = None


# ---------------------- controller bind ----------------------

def bind(window):
    s = AppState()
    window.openDiffPopupBtn = QtWidgets.QPushButton("Open Zoomed Compare")
    window.openDiffPopupBtn.setEnabled(False)

    window.openImgCompareBtn = QtWidgets.QPushButton("Open Image Compare")
    window.openImgCompareBtn.setEnabled(False)
    # put it inside the Difference Map box footer
    if hasattr(window, "diffPreviewEnc") and hasattr(window.diffPreviewEnc, "add_footer_widget"):
        window.diffPreviewEnc.add_footer_widget(window.openImgCompareBtn)
        window.diffPreviewEnc.add_footer_widget(window.openDiffPopupBtn)
    # --- tiny diagnostics ---
    def _scan_magic_prefix(blob: bytes, magic=b"STG1", scan_bytes=64):
        return blob[:scan_bytes].find(magic)

    def probe_image_decode(img_np, lsb, key):
        """Try variants to help diagnose symmetry mistakes."""
        variants = [(True, 'RGB'), (False, 'RGB'), (True, 'BGR'), (False, 'BGR')]
        for msb_first, chan in variants:
            try:
                blob = decode_rgb_all(img_np, lsb, key, region=None, max_bits=None,
                                      msb_first=msb_first, channel_order=chan)
                meta, _ = try_unpack_partial(blob)
                if meta is not None:
                    print(f"[probe] header with msb_first={msb_first}, channel_order={chan}")
                    window.statusLbl.setText(
                        f"Recovered using variant: msb_first={msb_first}, channel_order={chan}"
                    )
                    return True, meta
            except Exception:
                pass
        return False, None

    # --- capacity label (encode tab) ---
    def update_capacity():
        lsb = window.lsbSpinEnc.value()
        if s.cover_type == 'image' and s.cover_img is not None:
            cap = image_capacity_bits(s.cover_img, lsb)
            window.capacityLblEnc.setText(f"Capacity: {cap} bits (~{cap//8} bytes)")
        elif s.cover_type == 'audio' and s.cover_audio is not None:
            cap = audio_capacity_bits(s.cover_audio, lsb)
            window.capacityLblEnc.setText(f"Capacity: {cap} bits (~{cap//8} bytes)")
        elif s.cover_type == 'video' and s.cover_video is not None:
            cap = video_capacity_bits(s.cover_video, lsb)
            window.capacityLblEnc.setText(f"Capacity: {cap} bits (~{cap//8} bytes)")
        else:
            window.capacityLblEnc.setText("Capacity: -")

    # ===================== ENCODE TAB =====================

    def enc_load_cover(path):
        window.openImgCompareBtn.setEnabled(False)
        window.openDiffPopupBtn.setEnabled(False)

        # Hide by default when switching files
        window.regionGroup.setVisible(False)
        window.regionXSpin.setValue(0); window.regionYSpin.setValue(0)
        window.regionWSpin.setValue(0); window.regionHSpin.setValue(0)

        ext = os.path.splitext(path)[1].lower()
        s.stego_img = None; s.stego_audio = None; s.stego_video = None  # reset any previous stego
        try:
            if ext in ('.bmp', '.png', '.gif', '.jpg', '.jpeg'):
                img = load_image_rgb(path)
                s.cover_img = img; s.cover_audio = None; s.cover_video = None; s.cover_type = 'image'; s.sr = None; s.fps = None
                window.imagePreviewEnc.setPixmap(to_qpixmap_from_np_rgb(img))
                window.diffPreviewEnc.setPixmap(QtGui.QPixmap())

                # Show region inputs for images and set helpful max ranges
                H, W = img.shape[:2]
                window.regionXSpin.setMaximum(max(0, W-1))
                window.regionYSpin.setMaximum(max(0, H-1))
                window.regionWSpin.setMaximum(W)
                window.regionHSpin.setMaximum(H)
                window.regionGroup.setVisible(True)

                if ext in ('.jpg', '.jpeg', '.gif'):
                    window.statusLblEnc.setText(
                        f"Loaded cover: {os.path.basename(path)} (warning: {ext.upper()} is lossy; stego will be saved as PNG)."
                    )
                else:
                    msg = f"Loaded cover: {os.path.basename(path)}"
                    window.statusLblEnc.setText(msg)
                    if hasattr(window, "appStatus"): window.appStatus.showMessage(msg, 4000)
            elif ext == '.wav':
                audio, sr = load_wav_pcm16(path)
                s.cover_audio = audio; s.cover_img = None; s.cover_video = None; s.cover_type = 'audio'; s.sr = sr; s.fps = None
                window.imagePreviewEnc.setPixmap(to_text_pixmap(f"WAV: {audio.shape} @ {sr}Hz"))
                window.diffPreviewEnc.setPixmap(QtGui.QPixmap())
                msg = f"Loaded cover: {os.path.basename(path)}"
                window.statusLblEnc.setText(msg)
                if hasattr(window, "appStatus"): window.appStatus.showMessage(msg, 4000)
            elif ext in ('.mp4', '.avi'):
                frames, fps = load_video_frames(path)
                s.cover_video = frames; s.cover_img = None; s.cover_audio = None; s.cover_type = 'video'; s.fps = fps; s.sr = None
                window.imagePreviewEnc.setPixmap(to_qpixmap_from_np_rgb(frames[0]))
                window.diffPreviewEnc.setPixmap(QtGui.QPixmap())
                msg = f"Loaded cover: {os.path.basename(path)} ({len(frames)} frames @ {fps}fps)"
                window.statusLblEnc.setText(msg)
                if hasattr(window, "appStatus"): window.appStatus.showMessage(msg, 4000)
            else:
                window.statusLblEnc.setText("Unsupported cover format.")
                return
            s.cover_path = path
            update_capacity()
        except Exception as e:
            window.statusLblEnc.setText(f"Failed to load cover: {e}")

    def enc_load_payload(path):
        s.payload_path = path
        try:
            # Get file size and detected MIME type
            file_size = os.path.getsize(path)
            mime_type = detect_mime_type(path)
            size_kb = file_size / 1024
            if size_kb < 1:
                size_str = f"{file_size} bytes"
            elif size_kb < 1024:
                size_str = f"{size_kb:.1f} KB"
            else:
                size_str = f"{size_kb/1024:.1f} MB"
            
            msg = f"Payload loaded: {os.path.basename(path)} ({mime_type}, {size_str})"
        except Exception:
            msg = f"Payload loaded: {os.path.basename(path)}"
            
        if hasattr(window, "appStatus"): window.appStatus.showMessage(msg, 4000)
        window.statusLblEnc.setText(msg)
    
    def enc_text_changed():
        text = window.payloadTextEdit.toPlainText().strip()
        if text:
            s.payload_text = text
            s.payload_path = None  # Clear file when text is entered
            msg = f"Text payload: {len(text)} characters"
            window.statusLblEnc.setText(msg)
        else:
            s.payload_text = None

    def do_encode():
        if not s.cover_path or (not s.payload_path and not s.payload_text):
            window.statusLblEnc.setText("Select cover and payload first.")
            return
        key = window.keySpinEnc.value()
        lsb = window.lsbSpinEnc.value()
        
        # Debug: Show encoding attempt
        window.statusLblEnc.setText("Starting encoding process...")
        
        try:
            if s.payload_text:
                raw = s.payload_text.encode('utf-8')
                mime_type = "text/plain"   # <-- add this
                packed = pack_payload(raw, mime_type, key_hint=(key % 1000003))
            else:
                raw = open(s.payload_path, 'rb').read()
                mime_type = detect_mime_type(s.payload_path)
                packed = pack_payload(raw, mime_type, key_hint=(key % 1000003))

                # Check capacity
                payload_bits = len(packed) * 8
                if s.cover_type == 'image':
                    cover_capacity = image_capacity_bits(s.cover_img, lsb)
                    if payload_bits > cover_capacity:
                        window.statusLblEnc.setText(f"Payload too large! Need {payload_bits} bits but cover only has {cover_capacity} bits capacity at {lsb} LSB.")
                        return
                elif s.cover_type == 'audio':
                    cover_capacity = audio_capacity_bits(s.cover_audio, lsb)
                    if payload_bits > cover_capacity:
                        window.statusLblEnc.setText(f"Payload too large! Need {payload_bits} bits but cover only has {cover_capacity} bits capacity at {lsb} LSB.")
                        return

            region = None
            if (window.regionWSpin.value() > 0 and window.regionHSpin.value() > 0):
                region = (
                    window.regionYSpin.value(),   # y0
                    window.regionXSpin.value(),   # x0
                    window.regionHSpin.value(),   # height
                    window.regionWSpin.value()    # width
                )

                # Validate region against image bounds
                if region and s.cover_type == 'image':
                    y0, x0, rh, rw = region
                    if y0 + rh > s.cover_img.shape[0] or x0 + rw > s.cover_img.shape[1]:
                        window.statusLblEnc.setText("Invalid region: outside image bounds.")
                        return
                    
            if s.cover_type == 'image':
                stego = encode_rgb(s.cover_img, packed, lsb, key, region=region)
                s.stego_img = stego; s.stego_audio = None; s.stego_video = None
                base = os.path.splitext(os.path.basename(s.cover_path))[0]
                out  = os.path.join(tempfile.gettempdir(), f"stego_{base}.png")   # always lossless
                save_image_rgb(stego, out)

                window.imagePreviewEnc.setPixmap(to_qpixmap_from_np_rgb(stego))
                dm = difference_map(s.cover_img, stego)  # PIL image
                window.diffPreviewEnc.setPixmap(to_qpixmap_from_pil(dm))
                window.openDiffPopupBtn.setEnabled(False)
                def _open_img_compare():
                    ImageCompareDialog(s.cover_img, stego, parent=window).exec()
                try:
                    window.openImgCompareBtn.clicked.disconnect()
                except Exception:
                    pass
                window.openImgCompareBtn.clicked.connect(_open_img_compare)
                window.openImgCompareBtn.setEnabled(True)

                # image branch does not use audio compare button
                window.openDiffPopupBtn.setEnabled(False)
                # internal loopback (diagnostic)
                try:
                    test_blob = decode_rgb_all(stego, lsb, key)
                    test_meta, _ = try_unpack_partial(test_blob)
                    if test_meta:
                        msg = f"Encoded {mime_type} payload → Stego image saved → {out}"
                        if hasattr(window, "appStatus"): window.appStatus.showMessage(msg, 6000)
                        window.statusLblEnc.setText(msg)
                    else:
                        msg = f"Encoded {mime_type} payload → Stego image saved → {out} (verify failed)"
                        if hasattr(window, "appStatus"): window.appStatus.showMessage(msg, 6000)
                        window.statusLblEnc.setText(msg)
                except Exception:
                    window.statusLblEnc.setText(f"Encoded → {out}")

            elif s.cover_type == 'audio':
                stego = encode_wav(s.cover_audio, lsb, key, packed, region=None)
                s.stego_audio = stego; s.stego_img = None; s.stego_video = None
                out = os.path.join(tempfile.gettempdir(), f"stego_{os.path.basename(s.cover_path)}")
                save_wav_pcm16(out, stego, s.sr)

                # show diff in the panel
                panel_pil = audio_difference_panel(s.cover_audio, stego, sr=s.sr, lsb=lsb)
                window.diffPreviewEnc.setPixmap(to_qpixmap_from_pil(panel_pil))

                window.imagePreviewEnc.setPixmap(to_text_pixmap(f"Encoded {mime_type} payload → Saved stego WAV → {out}"))
                window.statusLblEnc.setText(f"Encoded {mime_type} payload → {out}")

                # enable + wire the pop-out
                def _open_compare():
                    AudioCompareDialog(s.cover_audio, stego, sr=s.sr, lsb=lsb, parent=window).exec()

                try:
                    window.openDiffPopupBtn.clicked.disconnect()
                except Exception:
                    pass
                window.openDiffPopupBtn.clicked.connect(_open_compare)
                window.openDiffPopupBtn.setEnabled(True)
            
            elif s.cover_type == 'video':
                print(f"\n=== VIDEO ENCODING START ===")
                print(f"Payload: {len(packed)} bytes")
                print(f"Cover: {s.cover_video.shape} frames")
                
                stego = encode_video(s.cover_video, packed, lsb, key)  # Use LSB method
                s.stego_video = stego; s.stego_img = None; s.stego_audio = None
                base = os.path.splitext(os.path.basename(s.cover_path))[0]
                out = os.path.join(tempfile.gettempdir(), f"stego_{base}.avi")  # FFV1 lossless
                save_video_frames(stego, out, s.fps)
                
                print(f"Stego video saved: {out}")
                print(f"=== VIDEO ENCODING COMPLETE ===\n")
                
                window.imagePreviewEnc.setPixmap(to_qpixmap_from_np_rgb(stego[0]))
                window.diffPreviewEnc.setPixmap(QtGui.QPixmap())
                window.statusLblEnc.setText(f"Encoded → {out}")
                window.openDiffPopupBtn.setEnabled(False)
                window.openImgCompareBtn.setEnabled(False)
            
            else:
                window.statusLblEnc.setText("Unsupported cover type.")
        except Exception as e:
            window.statusLblEnc.setText(f"Encode error: {e}")

    # ===================== DECODE TAB =====================

    def dec_load_stego(path):
        s.decode_path = path
        ext = os.path.splitext(path)[1].lower()

        # Reset and hide region inputs on Decode tab
        window.regionGroupDec.setVisible(False)
        window.regionXSpinDec.setValue(0); window.regionYSpinDec.setValue(0)
        window.regionWSpinDec.setValue(0); window.regionHSpinDec.setValue(0)

        try:
            if ext in ('.png', '.bmp'):
                s.decode_img = load_image_rgb(path); s.decode_audio=None; s.decode_video=None; s.decode_type='image'; s.decode_sr=None; s.decode_fps=None
                window.imagePreviewDec.setPixmap(to_qpixmap_from_np_rgb(s.decode_img))
                window.statusLbl.setText(f"Loaded stego: {os.path.basename(path)}")

                # show region inputs + bound ranges to image size
                H, W = s.decode_img.shape[:2]
                window.regionXSpinDec.setMaximum(max(0, W-1))
                window.regionYSpinDec.setMaximum(max(0, H-1))
                window.regionWSpinDec.setMaximum(W)
                window.regionHSpinDec.setMaximum(H)
                window.regionGroupDec.setVisible(True)

            elif ext == '.wav':
                a, sr = load_wav_pcm16(path)
                s.decode_audio = a; s.decode_img=None; s.decode_video=None; s.decode_type='audio'; s.decode_sr=sr; s.decode_fps=None
                window.imagePreviewDec.setPixmap(to_text_pixmap(f"WAV: {a.shape} @ {sr}Hz"))
                window.statusLbl.setText(f"Loaded stego: {os.path.basename(path)}")
            elif ext in ('.mp4', '.avi'):
                frames, fps = load_video_frames(path)
                s.decode_video = frames; s.decode_img=None; s.decode_audio=None; s.decode_type='video'; s.decode_fps=fps; s.decode_sr=None
                window.imagePreviewDec.setPixmap(to_qpixmap_from_np_rgb(frames[0]))
                window.statusLbl.setText(f"Loaded stego: {os.path.basename(path)} ({len(frames)} frames)")
            elif ext in ('.jpg', '.jpeg', '.gif'):
                window.statusLbl.setText("JPEG/GIF is lossy; LSBs destroyed. Drop the PNG/BMP stego saved during encode.")
            else:
                window.statusLbl.setText("Unsupported stego format. Use PNG/BMP/WAV/AVI.")
        except Exception as e:
            window.statusLbl.setText(f"Failed to load stego: {e}")

    def do_decode():
        lsb = window.lsbSpinDec.value()
        key = window.keySpinDec.value()
        if not s.decode_path:
            window.statusLbl.setText("Drop a stego file first (Decode tab).")
            return
        try:
            region = None
            if (window.regionWSpinDec.value() > 0 and window.regionHSpinDec.value() > 0):
                region = (
                    window.regionYSpinDec.value(),  # y0
                    window.regionXSpinDec.value(),  # x0
                    window.regionHSpinDec.value(),  # height
                    window.regionWSpinDec.value()   # width
    )
            if s.decode_type == 'image':
                # Validate region against image bounds
                if region is not None:
                    y0, x0, rh, rw = region
                    H, W = s.decode_img.shape[:2]
                    if y0 < 0 or x0 < 0 or rh <= 0 or rw <= 0 or (y0 + rh > H) or (x0 + rw > W):
                        window.statusLbl.setText("Invalid region: outside stego image bounds.")
                        return

                # Decode (with region if provided)
                blob = decode_rgb_all(s.decode_img, lsb, key, region=region, max_bits=None)
                meta, _ = try_unpack_partial(blob)
                if not meta:
                    ok, meta = probe_image_decode(s.decode_img, lsb, key)
                    if not ok:
                        off = _scan_magic_prefix(blob)
                        if off >= 0:
                            window.statusLbl.setText(
                                f"Decode failed: header at byte offset {off} (bit packing/order mismatch)."
                            )
                        else:
                            window.statusLbl.setText("Decode failed: No valid stego header found.")
                        return
            elif s.decode_type == 'audio':
                blob = decode_wav_all(s.decode_audio, lsb, key, region=None, max_bits=None)
                meta, _ = try_unpack_partial(blob)
                if not meta:
                    window.statusLbl.setText("Decode failed: No valid stego header found (audio).")
                    return
            elif s.decode_type == 'video':
                print(f"\n=== VIDEO DECODING START ===")
                print(f"Stego video: {s.decode_video.shape} frames")
                
                blob = decode_video_all(s.decode_video, lsb, key, max_bits=80000)  # Use LSB method
                meta, _ = try_unpack_partial(blob)
                if not meta:
                    print(f"Header search failed - no STG1 magic found")
                    window.statusLbl.setText(f"Decode failed: No valid stego header found (video LSB). Try different Key value.")
                    return
                
                print(f"Successfully found stego header!")
                print(f"=== VIDEO DECODING COMPLETE ===\n")
            else:
                window.statusLbl.setText("Unsupported stego type.")
                return

            # key guard
            if (meta.get('key_hint', 0) % 1000003) != (key % 1000003):
                window.statusLbl.setText("Decode failed: wrong key.")
                return

            # save recovered with proper extension based on MIME type
            mime_type = meta.get("mime", "application/octet-stream")
            ext = get_extension_from_mime(mime_type)
            out = os.path.join(tempfile.gettempdir(), "recovered_payload" + ext)
            with open(out, "wb") as f:
                f.write(meta["data"])

            window.statusLbl.setText(f"Decoded {meta.get('mime','unknown')} ({meta.get('length',0)} bytes) → {out}")

        except Exception as e:
            window.statusLbl.setText(f"Decode error: {e}")

    # ---------------- wire UI signals ----------------
    # Encode tab
    window.encodeCoverDrop.fileDropped.connect(enc_load_cover)
    window.encodePayloadDrop.fileDropped.connect(enc_load_payload)
    window.payloadTextEdit.textChanged.connect(enc_text_changed)
    window.encodeBtn.clicked.connect(do_encode)
    window.lsbSpinEnc.valueChanged.connect(lambda _: update_capacity())
    window.browseCoverBtn.clicked.connect(lambda: _browse_file(window, window.encodeCoverDrop))
    window.browsePayloadBtn.clicked.connect(lambda: _browse_file(window, window.encodePayloadDrop))

    # Decode tab
    window.decodeStegoDrop.fileDropped.connect(dec_load_stego)
    window.decodeBtn.clicked.connect(do_decode)
    window.browseStegoBtn.clicked.connect(lambda: _browse_file(window, window.decodeStegoDrop))

    return s

# ---------- file dialog helper ----------
def _browse_file(window, dropArea):
    path, _ = QtWidgets.QFileDialog.getOpenFileName(window, "Select File")
    if path:
        dropArea.fileDropped.emit(path)