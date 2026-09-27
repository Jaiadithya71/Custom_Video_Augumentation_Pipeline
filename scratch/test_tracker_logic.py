import cv2
import numpy as np
from pathlib import Path

# Load Cascade
local_model = Path("assets/models/haarcascade_frontalface_default.xml")
cascade = cv2.CascadeClassifier(str(local_model))

def detect_letterbox_bars(video_path: str, sample_time_sec: float = 60.0):
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_MSEC, sample_time_sec * 1000)
    ret, frame = cap.read()
    cap.release()
    if not ret: return 0, 1080
    h, w, _ = frame.shape
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    row_means = np.mean(gray, axis=1)
    top_bar = 0
    while top_bar < h // 4 and row_means[top_bar] < 14:
        top_bar += 1
    bottom_bar = h
    while bottom_bar > 3 * (h // 4) and row_means[bottom_bar - 1] < 14:
        bottom_bar -= 1
    top_bar += top_bar % 2
    bottom_bar -= bottom_bar % 2
    return top_bar, bottom_bar

top, bottom = detect_letterbox_bars('temp/ULvplwBTbQk_video.mp4', 80.0)
active_h = bottom - top
active_w = int(active_h * 9 / 16)
active_w -= active_w % 2
active_h -= active_h % 2

print(f"Top bar: {top}, Bottom bar: {bottom}, Active H: {active_h}, Active W: {active_w}")
