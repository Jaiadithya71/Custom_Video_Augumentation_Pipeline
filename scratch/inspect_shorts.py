import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(".").resolve()))
import src
import subprocess
import shutil

jobs = json.load(open('temp/jobs.json', encoding='utf-8'))['cb21787d']['finished_shorts']
frames_dir = Path("scratch/inspected_frames")
frames_dir.mkdir(parents=True, exist_ok=True)

print("FFMPEG found at:", shutil.which("ffmpeg"))
print("FFPROBE found at:", shutil.which("ffprobe"))

for i, s in enumerate(jobs, 1):
    short_id = s['id']
    video_path = Path("output") / f"{short_id}.mp4"
    print("\n" + "=" * 60)
    print(f"SHORT {i}: {short_id}")
    print(f"File Size: {video_path.stat().st_size / (1024*1024):.2f} MB")
    print(f"Viral Title: {s['title']}")
    print(f"Hook Banner: {s['banner_text']}")
    print(f"Hype Score:  {s['score']:.2f}")
    print(f"Timestamps:  {s['start']}s -> {s['end']}s (Duration: {s['duration']:.1f}s)")
    print(f"Transcript Snippet:\n  \"{s['text'][:150]}...\"")
    
    # Extract 2 sample frames per short: at 3 seconds and at 15 seconds
    frame1 = frames_dir / f"{short_id}_frame_early.jpg"
    frame2 = frames_dir / f"{short_id}_frame_mid.jpg"
    
    subprocess.run([
        "ffmpeg", "-y", "-ss", "3", "-i", str(video_path),
        "-vframes", "1", "-q:v", "2", str(frame1)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    subprocess.run([
        "ffmpeg", "-y", "-ss", "15", "-i", str(video_path),
        "-vframes", "1", "-q:v", "2", str(frame2)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print(f"Extracted frames: {frame1.name}, {frame2.name}")

print("\nDone extracting frames for visual inspection!")
