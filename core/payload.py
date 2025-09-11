# core/payload.py
import struct

MAGIC = b"STG1"
# Header: MAGIC(4) | total_len(4) | mime_len(1) | key_hint(4) | mime(..) | data(..)

def pack_payload(data: bytes, mime: str, key_hint: int = 0) -> bytes:
    mime_b = mime.encode('utf-8')[:255]
    mime_len = len(mime_b)
    body = struct.pack(">4sIBI", MAGIC, 0, mime_len, key_hint) + mime_b + data
    total_len = len(body)
    return struct.pack(">4sIBI", MAGIC, total_len, mime_len, key_hint) + mime_b + data

def try_unpack_partial(blob: bytes):
    try:
        if len(blob) < 13:  # 4+4+1+4
            return None, 0
        magic, total_len, mime_len, key_hint = struct.unpack_from(">4sIBI", blob, 0)
        if magic != MAGIC: return None, 0
        need = 13 + mime_len
        if len(blob) < need:
            return None, 0
        mime = blob[13:13+mime_len].decode('utf-8', errors='ignore')
        data = blob[13+mime_len:total_len]
        if len(blob) < total_len:
            # partial stream but header ok
            return {"mime": mime, "length": len(data), "data": data, "key_hint": key_hint}, total_len
        return {"mime": mime, "length": len(data), "data": data, "key_hint": key_hint}, total_len
    except Exception:
        return None, 0
