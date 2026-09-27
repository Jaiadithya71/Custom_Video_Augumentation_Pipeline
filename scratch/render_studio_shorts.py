import os
import sys
sys.path.insert(0, ".")
import json
from pathlib import Path
from src.video_engine.tracker import FaceTracker
from src.video_engine.subtitle_gen import SubtitleGenerator
from src.video_engine.composer import VideoComposer

raw_video = "temp/ULvplwBTbQk_video.mp4"
with open("temp/ULvplwBTbQk_transcript.json", "r", encoding="utf-8") as f:
    transcript = json.load(f)

all_words = transcript.get("all_words", [])

tracker = FaceTracker()
subtitle_gen = SubtitleGenerator(font_size=54, margin_bottom=420)
composer = VideoComposer()

clips_def = [
    {
        "id": "ULvplwBTbQk_short_1",
        "start": 71.84,
        "end": 93.31,
        "title": "Satellite Explosion in Orbit • Sunita Williams",
        "banner": "SATELLITE EXPLOSION IN SPACE",
        "badge": "SATELLITE EXPLOSION IN SPACE",
        "score": 0.94,
    },
    {
        "id": "ULvplwBTbQk_short_2",
        "start": 126.24,
        "end": 158.19,
        "title": "Remembering Kalpana Chawla • NASA Tragedy",
        "banner": "THE TRAGEDY OF COLUMBIA",
        "badge": "THE TRAGEDY OF COLUMBIA",
        "score": 0.91,
    },
    {
        "id": "ULvplwBTbQk_short_3",
        "start": 2574.0,
        "end": 2614.0,
        "title": "Stuck in Space: Did You Lose Hope?",
        "banner": "STUCK IN SPACE: DID YOU LOSE HOPE?",
        "badge": "STUCK IN SPACE: DID YOU LOSE HOPE?",
        "score": 0.88,
    }
]

rendered_shorts = []

for c in clips_def:
    cid = c["id"]
    start = c["start"]
    end = c["end"]
    dur = round(end - start, 2)
    print(f"\n==========================================")
    print(f"Rendering {cid}: {start}s -> {end}s ({dur}s)")
    print(f"Title: {c['title']}")
    
    # 1. Slice words
    c_words = [w for w in all_words if w["end"] >= start and w["start"] <= end]
    text = " ".join([w["word"] for w in c_words])
    
    # 2. Subtitles
    ass_path = f"temp/{cid}.ass"
    subtitle_gen.generate_ass_file(c_words, start, ass_path)
    print(f"Generated subtitles: {ass_path} ({len(c_words)} words)")
    
    # 3. Calculate 9:16 crop window with letterbox removal
    crop_box = tracker.calculate_crop_window(raw_video, start, end)
    print(f"Crop window: {crop_box}")
    
    # 4. Render video
    out_mp4 = f"output/{cid}.mp4"
    composer.render_short(
        input_video_path=raw_video,
        start_sec=start,
        end_sec=end,
        crop_box=crop_box,
        ass_subtitle_path=ass_path,
        output_path=out_mp4,
        hook_banner_text=c["banner"],
        zoom_factor=1.05,
        banner_duration=4.5
    )
    print(f"Rendered: {out_mp4}")
    
    rendered_shorts.append({
        "id": cid,
        "video_path": out_mp4,
        "ass_path": ass_path,
        "title": c["title"],
        "banner_text": c["banner"],
        "score": c["score"],
        "start": start,
        "end": end,
        "duration": dur,
        "text": text
    })

# Update jobs.json
with open("temp/jobs.json", "r", encoding="utf-8") as f:
    jobs = json.load(f)

if "cb21787d" in jobs:
    jobs["cb21787d"]["finished_shorts"] = rendered_shorts
    with open("temp/jobs.json", "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2)
    print("\nUpdated temp/jobs.json with 3 brand-new studio shorts!")

print("\nALL 3 SHORTS RENDERED SUCCESSFULLY!")
