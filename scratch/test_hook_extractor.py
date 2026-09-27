import sys
sys.path.insert(0, ".")
import json
import re

with open("temp/ULvplwBTbQk_transcript.json", "r", encoding="utf-8") as f:
    transcript = json.load(f)

words = transcript["all_words"]
segments = transcript.get("segments", [])

# 1. Detect Intro Boundary
def find_intro_boundary(segments, total_duration):
    markers = [
        "before starting today",
        "before we get started",
        "before we start",
        "welcome to",
        "welcome back to",
        "today's episode",
        "in this episode",
        "my guest today",
        "our guest today",
        "without further ado",
        "brought to you by",
        "sponsor"
    ]
    for seg in segments:
        if 40.0 <= seg["start"] <= 270.0:
            txt = seg["text"].lower()
            if any(m in txt for m in markers):
                return seg["start"]
    if total_duration > 600.0:
        return min(210.0, total_duration)
    return total_duration

intro_limit = find_intro_boundary(segments, 3200.0)
print(f"Intro boundary: {intro_limit:.2f}s")

# 2. Identify Major Topic/Hook Starters in the Intro
# Major hook starts are speaker questions (Raj) or distinct news soundbites
intro_words = [w for w in words if w["end"] <= intro_limit]

question_starters = ["how", "what", "why", "was", "did", "do", "have", "before", "tell", "is", "can", "are"]

hook_points = []
for i, w in enumerate(intro_words):
    clean_w = w["word"].strip().lower()
    # If speaker turn with ">>" or at beginning
    if w["word"].startswith(">>") or i == 0:
        # Check first token after >>
        token = clean_w.replace(">>", "").strip().lower()
        if token in question_starters or i == 0 or "stuck" in clean_w or token == "this":
            hook_points.append(i)

print(f"Found {len(hook_points)} hook entry points:")
for hp in hook_points:
    w = intro_words[hp]
    snippet = " ".join([x["word"] for x in intro_words[hp:hp+8]])
    print(f"  At {w['start']:6.2f}s (idx {hp:3d}): {snippet}")
