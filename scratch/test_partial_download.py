import sys
sys.path.insert(0, ".")
import yt_dlp
from pathlib import Path

url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"

out_file = Path("temp/test_partial_vid.mp4")
if out_file.exists():
    out_file.unlink()

ydl_opts = {
    "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    "outtmpl": str(out_file),
    "download_ranges": yt_dlp.utils.download_range_func(None, [(0, 10)]),
    "force_keyframes_at_cuts": True,
    "nocheckcertificate": True,
    "quiet": False,
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    print(f"Partial video download succeeded: {out_file} ({out_file.stat().st_size} bytes)")
except Exception as e:
    print(f"Error: {e}")
