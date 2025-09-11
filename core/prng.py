import random

def permute_indices(n: int, seed: int):
    """Deterministic Fisher–Yates permutation of range(n) using integer seed."""
    idx = list(range(n))
    rng = random.Random(int(seed) & 0xFFFFFFFF)
    for i in range(n-1, 0, -1):
        j = rng.randrange(i+1)
        idx[i], idx[j] = idx[j], idx[i]
    return idx
