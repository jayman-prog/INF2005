# core/image_lsb.py
import numpy as np

def _rng_from_key(key: int):
    return np.random.default_rng(np.random.SeedSequence(int(key)))

def _build_index_order(img_np: np.ndarray, key: int, region=None, channel_order: str = 'RGB') -> np.ndarray:
    assert img_np.dtype == np.uint8 and img_np.ndim == 3 and img_np.shape[2] == 3
    h, w, _ = img_np.shape
    if region is None:
        pos = np.arange(h * w, dtype=np.int64)
    else:
        if isinstance(region, tuple):
            y0, x0, rh, rw = region
            yy, xx = np.mgrid[y0:y0+rh, x0:x0+rw]
            pos = (yy * w + xx).ravel().astype(np.int64)
        else:
            mask = np.asarray(region, dtype=bool).reshape(h, w)
            pos  = np.flatnonzero(mask).astype(np.int64)

    chan_seq = [0,1,2] if channel_order.upper() == 'RGB' else [2,1,0]
    per_chan = [pos * 3 + c for c in chan_seq]
    per_chan = np.concatenate(per_chan, axis=0)

    rng = _rng_from_key(key)
    order = rng.permutation(per_chan.size)
    return per_chan[order]

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

def encode_rgb(img_np: np.ndarray, payload: bytes, lsb: int, key: int,
               region=None, *, msb_first=True, channel_order='RGB') -> np.ndarray:
    assert 1 <= lsb <= 8
    assert img_np.dtype == np.uint8 and img_np.ndim == 3 and img_np.shape[2] == 3
    arr = img_np.copy()
    flat = arr.reshape(-1).view(np.uint8)

    order = _build_index_order(arr, key, region, channel_order)
    mask_u8     = np.uint8((1 << lsb) - 1)
    inv_mask_u8 = np.uint8(0xFF ^ mask_u8)

    bits = _bytes_to_bits(payload, msb_first=msb_first)
    n_chunks = int(np.ceil(bits.size / lsb))
    if n_chunks > order.size:
        raise ValueError("Payload too large for selected cover/region/lsb.")

    bit_idx = 0
    for idx in order[:n_chunks]:
        take = 0
        if msb_first:
            for bp in range(lsb):
                take = (take << 1) | (int(bits[bit_idx + bp]) if bit_idx + bp < bits.size else 0)
        else:
            for bp in range(lsb):
                if bit_idx + bp < bits.size and bits[bit_idx + bp]:
                    take |= (1 << bp)
        bit_idx += lsb
        flat[idx] = np.uint8((flat[idx] & inv_mask_u8) | (np.uint8(take) & mask_u8))
        if bit_idx >= bits.size: break

    return arr

def decode_rgb_all(img_np: np.ndarray, lsb: int, key: int,
                   region=None, max_bits=None, *, msb_first=True, channel_order='RGB') -> bytes:
    assert 1 <= lsb <= 8
    assert img_np.dtype == np.uint8 and img_np.ndim == 3 and img_np.shape[2] == 3
    flat = img_np.reshape(-1).view(np.uint8)
    order = _build_index_order(img_np, key, region, channel_order)
    if max_bits is None: max_bits = order.size * lsb

    out_bits = np.empty(min(max_bits, order.size * lsb), dtype=np.uint8)
    bi = 0
    for idx in order:
        if bi >= out_bits.size: break
        val = int(flat[idx])
        if msb_first:
            for bp in range(lsb - 1, -1, -1):
                if bi >= out_bits.size: break
                out_bits[bi] = (val >> bp) & 1; bi += 1
        else:
            for bp in range(lsb):
                if bi >= out_bits.size: break
                out_bits[bi] = (val >> bp) & 1; bi += 1

    return _bits_to_bytes(out_bits[:bi], msb_first=msb_first)
