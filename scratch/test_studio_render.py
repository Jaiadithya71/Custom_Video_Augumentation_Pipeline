"""Test script: Re-renders Short 1 with the studio-grade fixes and extracts visual proof frames."""

import os
import sys
import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(".").resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from src.intelligence.narrative_profiler import NarrativeProfiler
from src.video_engine.subtitle_gen import SubtitleGenerator
from src.video_engine.composer import VideoComposer
from src.video_engine.tracker import FaceTracker

PROJECT_ROOT = Path(".").resolve()
temp_dir = PROJECT_ROOT / "temp"
out_dir = PROJECT_ROOT / "output"
scratch_dir = PROJECT_ROOT / "scratch" / "studio_verification"
scratch_dir.mkdir(parents=True, exist_ok=True)

# 1. Load job cb21787d
jobs_file = temp_dir / "jobs.json"
with open(jobs_file, "r", encoding="utf-8") as f:
    jobs = json.load(f)

job = jobs.get("cb21787d")
if not job:
    # Find job for ULvplwBTbQk
    for jid, jdata in jobs.items():
        if "ULvplwBTbQk" in jdata.get("url", ""):
            job = jdata
            break

print("Found job:", job["id"])

# 2. Run Narrative Profiler
profiler = NarrativeProfiler()
profile = profiler.analyze(job["video_info"])
job["narrative_profile"] = profile.to_dict()

# Save updated jobs.json
with open(jobs_file, "w", encoding="utf-8") as f:
    json.dump(jobs, f, indent=2, ensure_ascii=False)

print("Profile generated:", profile.channel_name, "|", profile.editorial_badges)

# 3. Re-render Short 1 with studio-grade fixes
clip = job["candidates"][0] # Short 1
video_path = temp_dir / "ULvplwBTbQk_video.mp4"
ass_path = temp_dir / "ULvplwBTbQk_short_1.ass"
out_short = out_dir / "ULvplwBTbQk_short_1.mp4"

# Use the profile's first editorial badge as the banner
hook_badge = profile.editorial_badges[0] if profile.editorial_badges else "SATELLITE EXPLOSION IN SPACE"

sub_gen = SubtitleGenerator()
sub_gen.generate_ass_file(
    words=clip["words"],
    clip_start=clip["start"],
    output_ass_path=str(ass_path),
)

tracker = FaceTracker()
crop_box = tracker.calculate_crop_window(
    video_path=str(video_path),
    start_sec=clip["start"],
    end_sec=clip["end"],
)

composer = VideoComposer()
composer.render_short(
    input_video_path=str(video_path),
    start_sec=clip["start"],
    end_sec=clip["end"],
    crop_box=crop_box,
    ass_subtitle_path=str(ass_path),
    output_path=str(out_short),
    hook_banner_text=hook_badge,
    zoom_factor=profile.zoom_factor,
    banner_duration=profile.banner_duration_sec,
)

print("Render complete! Extracting verification frames...")

# Extract keyframes to inspect
frames_to_extract = [
    (0.5, "verified_0.5s_banner.jpg"),       # Banner active & styled in safe zone
    (5.5, "verified_5.5s_banner_gone.jpg"),  # Banner vanished after 4.5s
    (7.0, "verified_7.0s_no_old_caps.jpg"),  # Old bottom captions pushed off-screen
    (26.0, "verified_26.0s_no_stacking.jpg"),# IN THE MIDDLE - single line, no stacking
    (33.0, "verified_33.0s_no_stacking.jpg"),# SEE YOU ON - single line, no stacking
]

for sec, fname in frames_to_extract:
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(sec),
        "-i", str(out_short),
        "-vframes", "1",
        str(scratch_dir / fname)
    ]
    subprocess.run(cmd, capture_output=True)

print("All verification frames extracted to:", scratch_dir)
