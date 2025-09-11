def bytes_to_bits(data: bytes):
    """Yield bits MSB->LSB for each byte in data."""
    for b in data:
        for i in range(7, -1, -1):
            yield (b >> i) & 1

def bits_to_bytes(bits_iter):
    """Collect bits (MSB->LSB) into bytes."""
    out = bytearray()
    acc = 0
    n = 0
    for bit in bits_iter:
        acc = (acc << 1) | (bit & 1)
        n += 1
        if n == 8:
            out.append(acc)
            acc = 0
            n = 0
    if n:
        # pad with zeros (encoder stores true length in header)
        out.append(acc << (8 - n))
    return bytes(out)
