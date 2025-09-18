# core/viz.py
import numpy as np
from PIL import Image, ImageDraw

# -------------------- IMAGE DIFF --------------------

def difference_map(cover_rgb: np.ndarray, stego_rgb: np.ndarray) -> Image.Image:
    """
    Returns a grayscale PIL image highlighting changes between cover and stego.
    """
    diff = np.abs(stego_rgb.astype(np.int16) - cover_rgb.astype(np.int16)).sum(axis=2)
    diff = np.clip(diff * 32, 0, 255).astype(np.uint8)  # amplify for visibility
    return Image.fromarray(diff, mode='L')


# -------------------- AUDIO DIFF (panel) --------------------

def _to_mono_int16(x: np.ndarray) -> np.ndarray:
    a = np.asarray(x)
    if a.ndim == 2:  # stereo/interleaved -> mono
        a = a.mean(axis=1)
    return a.astype(np.int16)

def audio_difference_panel(cover_audio: np.ndarray, stego_audio: np.ndarray,
                           sr: int | None = None, lsb: int | None = None,
                           width: int = 800, height: int = 240,
                           preview_samples: int = 4000) -> Image.Image:
    """
    Simple diff viz for audio (one panel). Shows the diff waveform + text stats.
    """
    cov = _to_mono_int16(cover_audio)
    stg = _to_mono_int16(stego_audio)
    n = min(cov.size, stg.size)
    if n == 0:
        img = Image.new("RGB", (width, height), (20, 20, 20))
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "No audio samples to visualize.", fill=(255, 255, 255))
        return img

    diff = (stg[:n].astype(np.int32) - cov[:n].astype(np.int32))

    # canvas
    img = Image.new("RGB", (width, height), (14, 14, 14))
    draw = ImageDraw.Draw(img)

    # waveform area
    pad = 10
    plot_w = width - 2 * pad
    plot_h = int(height * 0.66) - pad
    x0, y0 = pad, pad
    x1, y1 = x0 + plot_w, y0 + plot_h
    draw.rectangle([x0, y0, x1, y1], outline=(70, 70, 70))

    seg = diff[:min(preview_samples, diff.size)]
    if seg.size > 0:
        max_abs = max(1, int(np.max(np.abs(seg))))
        mid = y0 + plot_h // 2
        stride = max(1, seg.size // plot_w)
        pts = seg[::stride][:plot_w]
        last = None
        for i, v in enumerate(pts):
            x = x0 + i
            y = int(mid - (v / max_abs) * (plot_h // 2 - 1))
            y = max(y0 + 1, min(y1 - 1, y))
            if last is not None:
                draw.line([last[0], last[1], x, y], fill=(0, 200, 255))
            last = (x, y)
        draw.line([x0, mid, x1, mid], fill=(80, 80, 80))

    # stats
    nz = int(np.count_nonzero(diff))
    maxd = int(np.max(np.abs(diff))) if diff.size else 0
    ty = int(height * 0.70)
    for line in [
        "Audio difference (stego − cover)",
        f"Samples compared: {n:,}",
        f"Nonzero samples: {nz:,}",
        f"Max |diff|: {maxd}",
        f"Sample rate: {sr if sr else '-'}",
        f"LSBs used: {lsb if lsb else '-'}",
    ]:
        draw.text((pad, ty), line, fill=(230, 230, 230))
        ty += 18

    return img


# -------------------- AUDIO COMPARE (stacked) --------------------

def _mono_i16(x: np.ndarray) -> np.ndarray:
    a = np.asarray(x)
    if a.ndim == 2:
        a = a.mean(axis=1)
    return a.astype(np.int16)

def _render_waveform(a: np.ndarray, width: int, height: int, color=(0, 200, 255)) -> Image.Image:
    img = Image.new("RGB", (width, height), (18, 18, 18))
    draw = ImageDraw.Draw(img)
    pad = 8
    x0, y0 = pad, pad
    x1, y1 = width - pad, height - pad
    draw.rectangle([x0, y0, x1, y1], outline=(70, 70, 70))
    mid = (y0 + y1) // 2
    draw.line([x0, mid, x1, mid], fill=(65, 65, 65))

    if a.size == 0:
        return img

    a32 = a.astype(np.int32)
    m = int(max(1, np.max(np.abs(a32))))
    stride = max(1, a32.size // (x1 - x0))
    pts = a32[::stride][: (x1 - x0)]
    last = None
    for i, v in enumerate(pts):
        x = x0 + i
        y = int(mid - (v / m) * ((y1 - y0 - 4) // 2))
        y = max(y0 + 1, min(y1 - 1, y))
        if last is not None:
            draw.line([last[0], last[1], x, y], fill=color)
        last = (x, y)
    return img

def render_audio_compare_panel(cover: np.ndarray, stego: np.ndarray,
                               start: int = 0, length: int | None = None,
                               sr: int | None = None, lsb: int | None = None,
                               width: int = 900, height: int = 540) -> Image.Image:
    """
    Stacked panel: cover (top), stego (middle), difference (bottom).
    View window controlled via start/length (in samples). Mono view.
    """
    cov = _mono_i16(cover)
    stg = _mono_i16(stego)
    n = min(cov.size, stg.size)
    if n == 0:
        return Image.new("RGB", (width, height), (12, 12, 12))
    if length is None:
        length = n
    start = max(0, min(start, n - 1))
    end = max(start + 1, min(start + length, n))

    cov_seg = cov[start:end]
    stg_seg = stg[start:end]
    diff_seg = (stg_seg.astype(np.int32) - cov_seg.astype(np.int32)).astype(np.int32)

    img = Image.new("RGB", (width, height), (12, 12, 12))
    draw = ImageDraw.Draw(img)
    h_third = height // 3

    panels = [
        ("Cover",      cov_seg,  (0, 200, 255)),
        ("Stego",      stg_seg,  (0, 220, 130)),
        ("Difference", diff_seg, (255, 160, 0)),
    ]
    y = 0
    for title, arr, color in panels:
        sub = _render_waveform(arr, width, h_third, color=color)
        img.paste(sub, (0, y))
        draw.text((10, y + 6), title, fill=(230, 230, 230))
        y += h_third

    nz = int(np.count_nonzero(diff_seg))
    mx = int(np.max(np.abs(diff_seg))) if diff_seg.size else 0
    info = f"samples {start:,}..{end:,} | nonzero: {nz:,} | max|diff|: {mx}"
    if sr: info += f" | {sr} Hz"
    if lsb: info += f" | LSBs: {lsb}"
    draw.text((10, height - 20), info, fill=(230, 230, 230))
    return img


def _clamp_roi(x, y, w, h, W, H):
    x = max(0, min(x, W - 1))
    y = max(0, min(y, H - 1))
    w = max(1, min(w, W - x))
    h = max(1, min(h, H - y))
    return x, y, w, h

def _crop_zoom(arr_rgb: np.ndarray, x: int, y: int, w: int, h: int, scale: int) -> Image.Image:
    """Crop HxWx3 uint8 and zoom with nearest-neighbor."""
    x, y, w, h = _clamp_roi(x, y, w, h, arr_rgb.shape[1], arr_rgb.shape[0])
    crop = arr_rgb[y:y+h, x:x+w, :]
    pil = Image.fromarray(crop, mode="RGB")
    if scale > 1:
        pil = pil.resize((w*scale, h*scale), resample=Image.NEAREST)
    return pil

def _crop_zoom_gray(arr_gray: np.ndarray, x: int, y: int, w: int, h: int, scale: int) -> Image.Image:
    x, y, w, h = _clamp_roi(x, y, w, h, arr_gray.shape[1], arr_gray.shape[0])
    crop = arr_gray[y:y+h, x:x+w]
    pil = Image.fromarray(crop, mode="L")
    if scale > 1:
        pil = pil.resize((w*scale, h*scale), resample=Image.NEAREST)
    return pil

def render_image_compare_panel(cover_rgb: np.ndarray,
                               stego_rgb: np.ndarray,
                               *,
                               view_w: int = 900,
                               view_h: int = 540,
                               zoom: int = 4,
                               pan_x: int = 0,
                               pan_y: int = 0) -> Image.Image:
    """
    Stacked panel: Cover (zoomed crop), Stego (same crop), Difference map (same crop)
    - zoom: integer scale factor (1..16)
    - pan_x/pan_y: top-left pixel of the crop in the original image
    The crop size is chosen so that zoomed panels fill view_w x view_h/3 each.
    """
    assert cover_rgb.shape == stego_rgb.shape and cover_rgb.ndim == 3 and cover_rgb.shape[2] == 3
    H, W, _ = cover_rgb.shape

    # each row gets 1/3 height; compute crop size so that crop*zoom fits the row width
    row_h = view_h // 3
    # keep square-ish pixels; prioritize width
    crop_w = max(1, min(W, view_w // max(1, zoom)))
    crop_h = max(1, min(H, row_h // max(1, zoom)))
    pan_x, pan_y, crop_w, crop_h = _clamp_roi(pan_x, pan_y, crop_w, crop_h, W, H)

    # compute amplified difference (grayscale) once
    diff = np.abs(stego_rgb.astype(np.int16) - cover_rgb.astype(np.int16)).sum(axis=2)
    diff = np.clip(diff * 32, 0, 255).astype(np.uint8)

    cov_pil  = _crop_zoom(cover_rgb, pan_x, pan_y, crop_w, crop_h, zoom)
    stg_pil  = _crop_zoom(stego_rgb, pan_x, pan_y, crop_w, crop_h, zoom)
    dif_pil  = _crop_zoom_gray(diff,      pan_x, pan_y, crop_w, crop_h, zoom)

    # compose stacked canvas
    from PIL import ImageDraw
    canvas = Image.new("RGB", (view_w, view_h), (12, 12, 12))
    draw   = ImageDraw.Draw(canvas)

    # center each row horizontally
    def paste_row(img, row_idx, title):
        y0 = row_idx * row_h
        x0 = (view_w - img.width) // 2
        canvas.paste(img, (x0, y0))
        draw.rectangle([x0, y0, x0 + img.width, y0 + img.height], outline=(70, 70, 70))
        draw.text((x0 + 10, y0 + 6), title, fill=(230, 230, 230))

    paste_row(cov_pil, 0, "Cover (zoomed)")
    paste_row(stg_pil, 1, "Stego (zoomed)")
    paste_row(dif_pil, 2, "Difference map (zoomed)")

    # footer info
    info = f"pan=({pan_x},{pan_y})  crop={crop_w}x{crop_h}  zoom={zoom}x"
    draw.text((10, view_h - 20), info, fill=(230, 230, 230))
    return canvas