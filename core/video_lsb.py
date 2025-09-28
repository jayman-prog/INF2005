# core/video_lsb.py
import numpy as np
import cv2

def encode_video(frames, payload, lsb, key, region=None):
    """Encode payload using LSB in red channel"""
    if len(frames) == 0:
        raise ValueError("No frames")
    
    bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8))
    print(f"[VIDEO ENCODE] Payload size: {len(payload)} bytes = {len(bits)} bits")
    print(f"[VIDEO ENCODE] Payload hex: {payload[:16].hex()}")
    print(f"[VIDEO ENCODE] First 16 bits: {bits[:16].tolist()}")
    
    frame = frames[0].copy()
    h, w = frame.shape[:2]
    print(f"[VIDEO ENCODE] Frame size: {h}x{w}")
    
    stego_frame = frame.copy()
    
    pixels_used = 0
    for i in range(min(len(bits), h * w)):
        y_pos = i // w
        x_pos = i % w
        
        # Modify 2 LSBs for robustness
        pixel_val = int(stego_frame[y_pos, x_pos, 0])  # Red channel
        new_val = (pixel_val & 0xFC) | (bits[i] * 3)  # Use 2 LSBs: 00 or 11
        stego_frame[y_pos, x_pos, 0] = new_val
        pixels_used += 1
    
    print(f"[VIDEO ENCODE] Modified {pixels_used} pixels")
    
    stego_frames = frames.copy()
    stego_frames[0] = stego_frame
    return stego_frames

def decode_video_all(frames, lsb, key, region=None, max_bits=None):
    """Decode payload from red channel LSB"""
    if len(frames) == 0:
        raise ValueError("No frames")
    
    frame = frames[0]
    h, w = frame.shape[:2]
    print(f"[VIDEO DECODE] Frame size: {h}x{w}")
    
    max_bytes = 10000 if max_bits is None else max_bits // 8
    max_bits = min(max_bytes * 8, h * w)
    bits = []
    
    for i in range(max_bits):
        y_pos = i // w
        x_pos = i % w
        pixel_val = int(frame[y_pos, x_pos, 0])  # Red channel
        bits.append(1 if (pixel_val & 3) >= 2 else 0)  # Extract from 2 LSBs
    
    print(f"[VIDEO DECODE] Extracted {len(bits)} bits")
    print(f"[VIDEO DECODE] First 16 bits: {bits[:16]}")
    
    bit_array = np.array(bits[:len(bits)//8*8])
    result = np.packbits(bit_array).tobytes()
    print(f"[VIDEO DECODE] Decoded {len(result)} bytes")
    return result