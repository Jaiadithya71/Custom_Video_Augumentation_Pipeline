import cv2
import os

os.makedirs('scratch/verification_frames', exist_ok=True)

checks = [
    ('ULvplwBTbQk_short_1.mp4', [2.0, 6.0, 15.0]),
    ('ULvplwBTbQk_short_2.mp4', [2.0, 7.0, 20.0]),
    ('ULvplwBTbQk_short_3.mp4', [2.0, 8.0, 22.0]),
]

for vname, times in checks:
    vpath = os.path.join('output', vname)
    cap = cv2.VideoCapture(vpath)
    base_name = vname.replace('.mp4', '')
    for t in times:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ret, frame = cap.read()
        if ret:
            out_img = f'scratch/verification_frames/{base_name}_t{int(t)}.jpg'
            cv2.imwrite(out_img, frame)
            print(f'Saved {out_img} ({frame.shape[1]}x{frame.shape[0]})')
    cap.release()
print('Frame extraction complete.')
