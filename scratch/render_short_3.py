import sys
sys.path.insert(0, ".")
import json
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

# Short 3: How India Looks From Space
cid = "ULvplwBTbQk_short_3"
start = 0.08
end = 17.87
dur = round(end - start, 2)
title = "How India Looks From Space • Sunita Williams"
banner = "HOW INDIA LOOKS FROM SPACE"

print(f"Rendering {cid}: {start}s -> {end}s ({dur}s)")

# 1. Words
c_words = [w for w in all_words if w["end"] >= start and w["start"] <= end]
text = " ".join([w["word"] for w in c_words])

# 2. Subtitles
ass_path = f"temp/{cid}.ass"
subtitle_gen.generate_ass_file(c_words, start, ass_path)

# 3. Crop window
crop_box = tracker.calculate_crop_window(raw_video, start, end)
print(f"Crop window: {crop_box}")

# 4. Render
out_mp4 = f"output/{cid}.mp4"
composer.render_short(
    input_video_path=raw_video,
    start_sec=start,
    end_sec=end,
    crop_box=crop_box,
    ass_subtitle_path=ass_path,
    output_path=out_mp4,
    hook_banner_text=banner,
    zoom_factor=1.05,
    banner_duration=4.5
)
print(f"Rendered: {out_mp4}")

# Update temp/jobs.json
with open("temp/jobs.json", "r", encoding="utf-8") as f:
    jobs = json.load(f)

job = jobs.get("cb21787d")
if job:
    # Update short 3 in finished_shorts
    for s in job["finished_shorts"]:
        if s["id"] == cid:
            s["start"] = start
            s["end"] = end
            s["duration"] = dur
            s["title"] = title
            s["banner_text"] = banner
            s["score"] = 0.94
            s["text"] = text

    with open("temp/jobs.json", "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2)
    print("Updated temp/jobs.json successfully!")
