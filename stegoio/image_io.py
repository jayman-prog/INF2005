# stegoio/image_io.py
from PIL import Image
import numpy as np
import os

def load_image_rgb(path: str) -> np.ndarray:
    im = Image.open(path).convert("RGB")
    return np.array(im, dtype=np.uint8)

def save_image_rgb(arr: np.ndarray, path: str):
    # Save whatever extension caller gives; for safety your controller uses .png
    Image.fromarray(arr, mode="RGB").save(path)

def infer_mime_from_path(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return {
        '.png': 'image/png', '.bmp': 'image/bmp', '.gif':'image/gif',
        '.jpg':'image/jpeg', '.jpeg':'image/jpeg'
    }.get(ext, 'application/octet-stream')
