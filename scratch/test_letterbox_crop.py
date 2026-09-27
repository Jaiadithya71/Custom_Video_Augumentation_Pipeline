import cv2
from pathlib import Path

out_dir = Path('scratch/crop_test')
out_dir.mkdir(parents=True, exist_ok=True)

cap = cv2.VideoCapture('temp/ULvplwBTbQk_video.mp4')

# Test active letterbox crop:
# top_bar = 104, active_h = 872, active_w = 490 (872 * 9/16)
# Center x = 960 -> crop_x = 715
crop_x = 715
crop_y = 104
crop_w = 490
crop_h = 872

test_times = [72.5, 76.0, 82.0, 90.0]
for t in test_times:
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ret, frame = cap.read()
    if ret:
        cropped = frame[crop_y:crop_y+crop_h, crop_x:crop_x+crop_w]
        # Resize to standard 1080x1920
        scaled = cv2.resize(cropped, (1080, 1920), interpolation=cv2.INTER_CUBIC)
        fn = out_dir / f'crop_{t:.1f}s.jpg'
        cv2.imwrite(str(fn), scaled)
        print(f'Saved {fn}')

cap.release()
