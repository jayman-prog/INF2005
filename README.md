# Stego LSB (INF2005)

Cross-platform reference implementation for LSB steganography with **images (RGB 8-bit)** and **audio (WAV PCM16)**.
Includes:
- Selectable **1..8 LSBs**
- **Keyed** start+permutation
- **Capacity checks**
- **Drag-and-drop** cover/payload
- **Difference map** & bit-plane visualization (images)

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

## Requirements
- Python 3.10+
- See `requirements.txt`

## Notes
- Prefer **BMP/PNG** for images; WAV (PCM16) for audio.
- Decoding uses header (magic+CRC) to validate payload & key.
- Stego files are saved to your temp folder (shown in status).

## Folder layout
(see tree in the assignment prompt)
