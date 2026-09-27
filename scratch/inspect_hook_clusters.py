import sys
sys.path.insert(0, ".")
import json

with open("temp/ULvplwBTbQk_transcript.json", "r", encoding="utf-8") as f:
    transcript = json.load(f)

words = transcript["all_words"]
segments = transcript.get("segments", [])

# Let's define the story hook clusters from the intro:
# A story hook starts at a major question or news opener and continues until the next question or completion.

# Let's inspect all major questions in the intro:
major_hook_times = [
    0.08,    # How does India look like
    25.60,   # Stuck in space / Boeing Starliner
    55.04,   # How many situations do you plan for
    71.84,   # Was there any point where you heard some sound and got scared
    97.04,   # Did you feel lonely / cried in space
    109.44,  # Most difficult part of training
    126.24,  # Kalpana Chawla & Columbia disaster
    160.16,  # Health cost when you come back
    179.28,  # Do you believe there's life out there
]

print("=== INTRO STORY HOOK CLUSTERS ===")
for i, start_t in enumerate(major_hook_times):
    # End is either the next hook start, or 208.64
    next_t = major_hook_times[i+1] if i+1 < len(major_hook_times) else 208.64
    # Slice words
    c_words = [w for w in words if w["start"] >= start_t - 0.2 and w["end"] <= next_t + 0.1]
    if not c_words:
        continue
    # Snap ending to sentence end (. ! ?)
    for back in range(len(c_words)-1, max(0, len(c_words)-10), -1):
        if any(c_words[back]["word"].strip().endswith(p) for p in [".", "!", "?"]):
            c_words = c_words[:back+1]
            break
            
    c_start = c_words[0]["start"]
    c_end = c_words[-1]["end"]
    dur = round(c_end - c_start, 2)
    txt = " ".join([w["word"] for w in c_words])
    print(f"\nHook {i+1}: [{c_start:.2f}s -> {c_end:.2f}s] ({dur}s)")
    print(f"Text: {txt[:120]}...")
