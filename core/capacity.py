# core/capacity.py
import numpy as np

def image_capacity_bits(img_np, lsb: int) -> int:
    if img_np is None: return 0
    h, w, c = img_np.shape
    return h * w * c * lsb

def audio_capacity_bits(wav_np, lsb: int) -> int:
    if wav_np is None: return 0
    a = wav_np
    if a.ndim == 1: n = a.shape[0]
    else: n = a.shape[0] * a.shape[1]
    return n * lsb
