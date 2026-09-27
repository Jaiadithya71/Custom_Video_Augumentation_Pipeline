import sys
from pathlib import Path
sys.path.insert(0, str(Path(".").resolve()))
import src
import subprocess
import shutil

out_dir = Path("scratch/deep_visual_inspection")
out_dir.mkdir(parents=True, exist_ok=True)
ffmpeg_bin = shutil.which("ffmpeg")

checks = [
    # Short 1: Start, transitions, and end
    ('output/ULvplwBTbQk_short_1.mp4', 's1_0.2s', 0.2),
    ('output/ULvplwBTbQk_short_1.mp4', 's1_3.5s', 3.5),
    ('output/ULvplwBTbQk_short_1.mp4', 's1_9.5s', 9.5),
    ('output/ULvplwBTbQk_short_1.mp4', 's1_15.5s', 15.5),
    ('output/ULvplwBTbQk_short_1.mp4', 's1_22.0s', 22.0),
    ('output/ULvplwBTbQk_short_1.mp4', 's1_33.0s', 33.0),
    
    # Short 2: Columbia disaster & Kalpana Chawla
    ('output/ULvplwBTbQk_short_2.mp4', 's2_1.0s', 1.0),
    ('output/ULvplwBTbQk_short_2.mp4', 's2_8.0s', 8.0),
    ('output/ULvplwBTbQk_short_2.mp4', 's2_18.0s', 18.0),
    ('output/ULvplwBTbQk_short_2.mp4', 's2_28.0s', 28.0),
    
    # Short 3: Space sickness & Extraterrestrial life
    ('output/ULvplwBTbQk_short_3.mp4', 's3_2.0s', 2.0),
    ('output/ULvplwBTbQk_short_3.mp4', 's3_12.0s', 12.0),
    ('output/ULvplwBTbQk_short_3.mp4', 's3_25.0s', 25.0),
    ('output/ULvplwBTbQk_short_3.mp4', 's3_38.0s', 38.0),
]

for video, label, t in checks:
    dest = out_dir / f"{label}.jpg"
    subprocess.run([
        ffmpeg_bin, "-y", "-ss", str(t), "-i", video,
        "-vframes", "1", "-q:v", "2", str(dest)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Extracted {dest.name} at {t}s")

print("All deep frames successfully extracted!")
