# core/audio_lsb.py
import numpy as np

def _rng_from_key(key: int):
    return np.random.default_rng(np.random.SeedSequence(int(key)))

def _build_indices(n_samples: int, key: int, region=None) -> np.ndarray:
    # region can be a slice over sample indices (start, length)
    idx = np.arange(n_samples, dtype=np.int64)
    if isinstance(region, tuple) and len(region) == 2:
        start, length = region
        start = max(0, int(start)); end = min(n_samples, start + int(length))
        idx = np.arange(start, end, dtype=np.int64)
    rng = _rng_from_key(key)
    return rng.permutation(idx.size)

def _bytes_to_bits(data: bytes, *, msb_first=True) -> np.ndarray:
    if not data: return np.zeros(0, dtype=np.uint8)
    b = np.frombuffer(data, dtype=np.uint8)
    if msb_first:
        return ((b[:, None] >> np.arange(7, -1, -1)) & 1).astype(np.uint8).ravel()
    else:
        return ((b[:, None] >> np.arange(0, 8, 1)) & 1).astype(np.uint8).ravel()

def _bits_to_bytes(bits: np.ndarray, *, msb_first=True) -> bytes:
    bits = np.asarray(bits, dtype=np.uint8)
    if bits.size == 0: return b""
    pad = (-bits.size) % 8
    if pad: bits = np.pad(bits, (0, pad), constant_values=0)
    bits = bits.reshape(-1,8)
    if msb_first:
        return np.packbits(bits, axis=1, bitorder='big').ravel().tobytes()
    else:
        return np.packbits(bits[:, ::-1], axis=1, bitorder='big').ravel().tobytes()

def _ensure_2d_int16(wav: np.ndarray) -> np.ndarray:
    a = np.asarray(wav)
    if a.dtype != np.int16: a = a.astype(np.int16)
    if a.ndim == 1: a = a[:, None]
    return a  # shape (n, ch)

def encode_wav(audio: np.ndarray, lsb: int, key: int, payload: bytes, region=None,
               *, msb_first=True) -> np.ndarray:
    assert 1 <= lsb <= 8
    a = _ensure_2d_int16(audio).copy()
    n, ch = a.shape
    # work on interleaved view
    flat = a.reshape(-1).view(np.int16)
    total_samples = flat.size

    order = _build_indices(total_samples, key, region)
    mask_u16     = np.uint16((1 << lsb) - 1)
    inv_mask_u16 = np.uint16(0xFFFF ^ mask_u16)

    bits = _bytes_to_bits(payload, msb_first=msb_first)
    n_chunks = int(np.ceil(bits.size / lsb))
    if n_chunks > order.size:
        raise ValueError("Payload too large for selected cover/region/lsb (audio).")

    bit_idx = 0
    for pos in order[:n_chunks]:
        val = np.uint16(np.int16(flat[pos]))  # handle negative int16
        take = 0
        if msb_first:
            for bp in range(lsb):
                take = (take << 1) | (int(bits[bit_idx + bp]) if bit_idx + bp < bits.size else 0)
        else:
            for bp in range(lsb):
                if bit_idx + bp < bits.size and bits[bit_idx + bp]:
                    take |= (1 << bp)
        bit_idx += lsb
        newv = np.uint16((val & inv_mask_u16) | (np.uint16(take) & mask_u16))
        flat[pos] = np.int16(newv)  # back to signed
        if bit_idx >= bits.size: break

    return a

def decode_wav_all(audio: np.ndarray, lsb: int, key: int, region=None, max_bits=None, *, msb_first=True) -> bytes:
    assert 1 <= lsb <= 8
    a = _ensure_2d_int16(audio)
    flat = a.reshape(-1).view(np.int16)
    total_samples = flat.size
    order = _build_indices(total_samples, key, region)
    if max_bits is None: max_bits = order.size * lsb
    out_bits = np.empty(min(max_bits, order.size * lsb), dtype=np.uint8)

    bi = 0
    for pos in order:
        if bi >= out_bits.size: break
        val = np.uint16(np.int16(flat[pos]))
        if msb_first:
            for bp in range(lsb - 1, -1, -1):
                if bi >= out_bits.size: break
                out_bits[bi] = (val >> bp) & 1; bi += 1
        else:
            for bp in range(lsb):
                if bi >= out_bits.size: break
                out_bits[bi] = (val >> bp) & 1; bi += 1

    return _bits_to_bytes(out_bits[:bi], msb_first=msb_first)
