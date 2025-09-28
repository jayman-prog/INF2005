# stegoio/video_io.py
import cv2
import numpy as np

def load_video_frames(path: str):
    """Load video frames as RGB arrays"""
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(frame_rgb)
    
    cap.release()
    frames_array = np.array(frames)
    
    # Store original dimensions in metadata (simple approach)
    if len(frames) > 0:
        orig_h, orig_w = frames[0].shape[:2]
        print(f"[VIDEO IO] Original size: {orig_h}x{orig_w}")
    
    return frames_array, fps

def save_video_frames(frames: np.ndarray, path: str, fps: float):
    """Save RGB frames using lossless codec"""
    if len(frames) == 0:
        return
    
    h, w = frames[0].shape[:2]
    print(f"[VIDEO IO] Saving size: {h}x{w}")
    
    # Try FFV1 lossless codec
    fourcc = cv2.VideoWriter_fourcc(*'FFV1')
    out = cv2.VideoWriter(path, fourcc, fps, (w, h))
    
    if not out.isOpened():
        print("[VIDEO IO] FFV1 failed, using MJPG")
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        out = cv2.VideoWriter(path, fourcc, fps, (w, h))
    
    for frame in frames:
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        out.write(frame_bgr)
    
    out.release()
    print(f"[VIDEO IO] Video saved successfully")