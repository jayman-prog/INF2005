# core/viz.py
import numpy as np
from PIL import Image

def difference_map(cover_rgb: np.ndarray, stego_rgb: np.ndarray) -> Image.Image:
    # visualize absolute diff across channels, amplified
    diff = np.abs(stego_rgb.astype(np.int16) - cover_rgb.astype(np.int16)).sum(axis=2)
    diff = np.clip(diff * 32, 0, 255).astype(np.uint8)  # amplify for visibility
    return Image.fromarray(diff, mode='L')
