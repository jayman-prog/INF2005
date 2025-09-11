# app/controllers.py
import os, tempfile
from PyQt6 import QtGui
import numpy as np

# IO adapters (kept light)
try:
    from stegoio.image_io import load_image_rgb, save_image_rgb
    from stegoio.audio_io import load_wav_pcm16, save_wav_pcm16
except ModuleNotFoundError:
    from stegoio.image_io import load_image_rgb, save_image_rgb  # type: ignore
    from stegoio.audio_io import load_wav_pcm16, save_wav_pcm16  # type: ignore

from core.payload import pack_payload, try_unpack_partial
from core.capacity import image_capacity_bits, audio_capacity_bits
from core.image_lsb import encode_rgb, decode_rgb_all
from core.audio_lsb import encode_wav, decode_wav_all
from core.viz import difference_map

def to_qpixmap_from_pil(pil_img):
    data = pil_img.tobytes("raw", pil_img.mode)
    if pil_img.mode == "L":
        fmt = QtGui.QImage.Format.Format_Grayscale8
        qimg = QtGui.QImage(data, pil_img.width, pil_img.height, pil_img.width, fmt)
    else:
        qimg = QtGui.QImage(data, pil_img.width, pil_img.height, pil_img.width*3, QtGui.QImage.Format.Format_RGB888)
    return QtGui.QPixmap.fromImage(qimg)

def to_qpixmap_from_np_rgb(arr):
    h, w, c = arr.shape
    qimg = QtGui.QImage(arr.data, w, h, w*3, QtGui.QImage.Format.Format_RGB888)
    return QtGui.QPixmap.fromImage(qimg.copy())

class AppState:
    def __init__(self):
        # Encode tab
        self.cover_path = None
        self.cover_type = None
        self.cover_img = None
        self.cover_audio = None
        self.sr = None
        self.payload_path = None
        self.stego_img = None
        self.stego_audio = None
        # Decode tab
        self.decode_path = None
        self.decode_type = None
        self.decode_img = None
        self.decode_audio = None
        self.decode_sr = None

def bind(window):
    s = AppState()

    # --- helpers ---
    def _scan_magic_prefix(blob: bytes, magic=b"STG1", scan_bytes=64):
        return blob[:scan_bytes].find(magic)

    def probe_image_decode(img_np, lsb, key):
        variants = [(True,'RGB'), (False,'RGB'), (True,'BGR'), (False,'BGR')]
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

    def to_text_pixmap(text, w=620, h=240):
        pm = QtGui.QPixmap(w, h)
        pm.fill(QtGui.QColor('black'))
        p = QtGui.QPainter(pm); p.setPen(QtGui.QColor('white'))
        p.drawText(10, h//2, text); p.end()
        return pm

    # --- capacity label (encode tab) ---
    def update_capacity():
        lsb = window.lsbSpinEnc.value()
        if s.cover_type == 'image' and s.cover_img is not None:
            cap = image_capacity_bits(s.cover_img, lsb)
            window.capacityLblEnc.setText(f"Capacity: {cap} bits (~{cap//8} bytes)")
        elif s.cover_type == 'audio' and s.cover_audio is not None:
            cap = audio_capacity_bits(s.cover_audio, lsb)
            window.capacityLblEnc.setText(f"Capacity: {cap} bits (~{cap//8} bytes)")
        else:
            window.capacityLblEnc.setText("Capacity: -")

    # ===================== ENCODE TAB HANDLERS =====================
    def enc_load_cover(path):
        ext = os.path.splitext(path)[1].lower()
        # reset stego memory when new cover is loaded
        s.stego_img = None; s.stego_audio = None
        try:
            if ext in ('.bmp', '.png', '.gif', '.jpg', '.jpeg'):
                img = load_image_rgb(path)
                s.cover_img = img; s.cover_audio = None; s.cover_type = 'image'; s.sr = None
                window.imagePreviewEnc.setPixmap(to_qpixmap_from_np_rgb(img))
                window.diffPreviewEnc.setPixmap(QtGui.QPixmap())
                if ext in ('.jpg','.jpeg','.gif'):
                    window.statusLbl.setText(
                        f"Loaded cover: {os.path.basename(path)} (warning: {ext.upper()} is lossy; stego will be saved as PNG)."
                    )
                else:
                    window.statusLbl.setText(f"Loaded cover: {os.path.basename(path)}")
            elif ext == '.wav':
                audio, sr = load_wav_pcm16(path)
                s.cover_audio = audio; s.cover_img = None; s.cover_type = 'audio'; s.sr = sr
                window.imagePreviewEnc.setPixmap(to_text_pixmap(f"WAV: {audio.shape} @ {sr}Hz"))
                window.diffPreviewEnc.setPixmap(QtGui.QPixmap())
                window.statusLbl.setText(f"Loaded cover: {os.path.basename(path)}")
            else:
                window.statusLbl.setText("Unsupported cover format.")
                return
            s.cover_path = path
            update_capacity()
        except Exception as e:
            window.statusLbl.setText(f"Failed to load cover: {e}")

    def enc_load_payload(path):
        s.payload_path = path
        window.statusLbl.setText(f"Loaded payload: {os.path.basename(path)}")

    def do_encode():
        if not s.cover_path or not s.payload_path:
            window.statusLbl.setText("Select cover and payload first.")
            return
        key = window.keySpinEnc.value()
        lsb = window.lsbSpinEnc.value()
        try:
            raw = open(s.payload_path, 'rb').read()
            packed = pack_payload(raw, "application/octet-stream", key_hint=(key % 1000003))

            if s.cover_type == 'image':
                stego = encode_rgb(s.cover_img, packed, lsb, key, region=None)
                s.stego_img = stego; s.stego_audio = None
                base = os.path.splitext(os.path.basename(s.cover_path))[0]
                out  = os.path.join(tempfile.gettempdir(), f"stego_{base}.png")   # always lossless
                save_image_rgb(stego, out)
                window.imagePreviewEnc.setPixmap(to_qpixmap_from_np_rgb(stego))
                dm = difference_map(s.cover_img, stego)   # PIL image
                window.diffPreviewEnc.setPixmap(to_qpixmap_from_pil(dm))
                # quick internal loopback
                try:
                    test_blob = decode_rgb_all(stego, lsb, key)
                    test_meta, _ = try_unpack_partial(test_blob)
                    if test_meta:
                        window.statusLbl.setText(f"Encoded → {out}  |  Internal decode OK ({test_meta.get('length',0)} bytes)")
                    else:
                        window.statusLbl.setText(f"Encoded → {out}  |  Internal decode FAILED.")
                except Exception:
                    window.statusLbl.setText(f"Encoded → {out}")

            elif s.cover_type == 'audio':
                stego = encode_wav(s.cover_audio, lsb, key, packed, region=None)
                s.stego_audio = stego; s.stego_img = None
                out = os.path.join(tempfile.gettempdir(), f"stego_{os.path.basename(s.cover_path)}")
                save_wav_pcm16(out, stego, s.sr)
                window.imagePreviewEnc.setPixmap(to_text_pixmap(f"Saved stego WAV → {out}"))
                window.diffPreviewEnc.setPixmap(QtGui.QPixmap())
                window.statusLbl.setText(f"Encoded → {out}")
            else:
                window.statusLbl.setText("Unsupported cover type.")
        except Exception as e:
            window.statusLbl.setText(f"Encode error: {e}")

    # ===================== DECODE TAB HANDLERS =====================
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
            elif ext in ('.jpg', '.jpeg', '.gif'):
                window.statusLbl.setText("JPEG/GIF is lossy; LSBs destroyed. Drop the PNG/BMP stego saved during encode.")
            else:
                window.statusLbl.setText("Unsupported stego format. Use PNG/BMP/WAV.")
        except Exception as e:
            window.statusLbl.setText(f"Failed to load stego: {e}")

    def do_decode():
        # prefer decode tab controls
        lsb = window.lsbSpinDec.value()
        key = window.keySpinDec.value()

        if not s.decode_path:
            window.statusLbl.setText("Drop a stego file first (Decode tab).")
            return

        try:
            if s.decode_type == 'image':
                blob = decode_rgb_all(s.decode_img, lsb, key, region=None, max_bits=None)
                meta, _ = try_unpack_partial(blob)
                if not meta:
                    ok, meta = probe_image_decode(s.decode_img, lsb, key)
                    if not ok:
                        off = _scan_magic_prefix(blob)
                        if off >= 0:
                            window.statusLbl.setText(f"Decode failed: header at byte offset {off} (bit packing/order mismatch).")
                        else:
                            window.statusLbl.setText("Decode failed: No valid stego header found.")
                        return
            elif s.decode_type == 'audio':
                blob = decode_wav_all(s.decode_audio, lsb, key, region=None, max_bits=None)
                meta, _ = try_unpack_partial(blob)
                if not meta:
                    window.statusLbl.setText("Decode failed: No valid stego header found (audio).")
                    return
            else:
                window.statusLbl.setText("Unsupported stego type.")
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

        except Exception as e:
            window.statusLbl.setText(f"Decode error: {e}")

    # ---------- wire events (encode) ----------
    window.encodeCoverDrop.fileDropped.connect(enc_load_cover)
    window.encodePayloadDrop.fileDropped.connect(enc_load_payload)
    window.encodeBtn.clicked.connect(do_encode)
    window.lsbSpinEnc.valueChanged.connect(lambda _: update_capacity())

    # ---------- wire events (decode) ----------
    window.decodeStegoDrop.fileDropped.connect(dec_load_stego)
    window.decodeBtn.clicked.connect(do_decode)

    return s
