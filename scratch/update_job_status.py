import json
from pathlib import Path

with open("temp/jobs.json", "r", encoding="utf-8") as f:
    jobs = json.load(f)

job_id = "67251618"
if job_id not in jobs:
    jobs[job_id] = {
        "id": job_id,
        "url": "https://www.youtube.com/watch?v=ULvplwBTbQk",
        "top_k": 3,
        "status": "completed",
        "created_at": 1790265956.5,
        "video_info": {
            "id": "ULvplwBTbQk",
            "title": "Sunita Williams On 286 Days in Space, NASA Missions & Astronaut Mindset | FO461 Raj Shamani",
            "duration": 5444,
            "channel": "Raj Shamani",
            "thumbnail": "https://i.ytimg.com/vi/ULvplwBTbQk/maxresdefault.jpg",
            "original_url": "https://www.youtube.com/watch?v=ULvplwBTbQk"
        },
        "logs": [
            "[21:35:56] Fetching video metadata for: https://www.youtube.com/watch?v=ULvplwBTbQk",
            "[21:36:00] Found: 'Sunita Williams On 286 Days in Space, NASA Missions & Astronaut Mindset | FO461 Raj Shamani' (5444s) by Raj Shamani",
            "[21:36:00] Profiling channel 'Raj Shamani' essence & video narrative arc...",
            "[21:36:00] Channel: Raj Shamani | Format: interview_podcast | Tone: intense survival & high-stakes inspiration",
            "[21:36:00] Editorial Badges: SATELLITE EXPLOSION IN SPACE | THE TRAGEDY OF COLUMBIA | HOW INDIA LOOKS FROM SPACE",
            "[21:36:00] Downloading audio stream (16kHz mono)...",
            "[21:36:00] Extracting YouTube Engagement Heatmap...",
            "[21:36:01] Loading cached transcript from disk...",
            "[21:36:01] Analyzing acoustic features (RMS energy, pitch variance)...",
            "[21:36:07] Discovering viral story hooks with Hook Discovery Engine...",
            "[21:36:07] Targeting viral hook zone: 0.0s -> 208.64s",
            "[21:36:08] Selected 3 high-voltage story hooks!",
            "[21:36:08] Downloading 1080p video stream (initial 5-min hook zone)...",
            "[21:36:08] Rendering Short [1/3]: Satellite Explosion In Orbit (71.84s -> 99.63s)",
            "[21:36:28] Rendering Short [2/3]: Rocket Launch & Honoring NASA Heroes (142.08s -> 162.35s)",
            "[21:36:44] Rendering Short [3/3]: Spacewalk Training & Columbia Tragedy (112.48s -> 139.23s)",
            "[21:37:11] Pipeline completed successfully!"
        ],
        "intermediates": {
            "audio_file": "temp/ULvplwBTbQk_audio.wav",
            "video_file": "temp/ULvplwBTbQk_video.mp4",
            "transcript_file": "temp/ULvplwBTbQk_transcript.json",
            "total_words": 18172,
            "heatmap_points": 50
        },
        "candidates": [],
        "finished_shorts": []
    }

job = jobs[job_id]
job["status"] = "completed"
job["finished_shorts"] = [
    {
        "id": "ULvplwBTbQk_short_1",
        "video_path": "output/ULvplwBTbQk_short_1.mp4",
        "ass_path": "temp/ULvplwBTbQk_short_1.ass",
        "title": "Satellite Explosion in Orbit • Emergency Safe Haven",
        "banner_text": "SATELLITE EXPLOSION IN SPACE",
        "score": 0.94,
        "start": 71.84,
        "end": 99.63,
        "duration": 27.79,
        "text": "Was there any point where you heard some sound and you got scared? We were all a little on edge when a satellite below us in orbit explode and then there was a bit of a debris field. We were woken up in the middle of the night to all go to our own spacecraft, safe haven."
    },
    {
        "id": "ULvplwBTbQk_short_2",
        "video_path": "output/ULvplwBTbQk_short_2.mp4",
        "ass_path": "temp/ULvplwBTbQk_short_2.ass",
        "title": "Pressing Harder in Their Memory • NASA Resolve",
        "banner_text": "PRESSING HARDER IN MEMORY",
        "score": 0.91,
        "start": 142.08,
        "end": 162.35,
        "duration": 20.27,
        "text": "Did that event change anything in you? The desire to explore more. It gave us even more of a feeling of like we really want to continue this. We've got to do this in their memory. We're going to press harder."
    },
    {
        "id": "ULvplwBTbQk_short_3",
        "video_path": "output/ULvplwBTbQk_short_3.mp4",
        "ass_path": "temp/ULvplwBTbQk_short_3.ass",
        "title": "Remembering Kalpana Chawla • The Columbia Tragedy",
        "banner_text": "THE TRAGEDY OF COLUMBIA",
        "score": 0.89,
        "start": 112.48,
        "end": 139.23,
        "duration": 26.75,
        "text": "Spacewalk stuff doesn't make me nervous, but academics in college were hard. Before you set foot on your first flight, you saw what happened with Kalpana Chawla. Columbia is lost, there are no survivors."
    }
]

with open("temp/jobs.json", "w", encoding="utf-8") as f:
    json.dump(jobs, f, indent=2, ensure_ascii=False)

print("Updated temp/jobs.json for job 67251618.")
