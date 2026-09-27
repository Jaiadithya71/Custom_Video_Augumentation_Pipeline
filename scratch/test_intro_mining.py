import sys
sys.path.insert(0, ".")
import json
from src.hype_detector.fusion import HypeFusionEngine
from src.hype_detector.llm_scorer import LLMSemanticScorer

with open("temp/ULvplwBTbQk_transcript.json", "r", encoding="utf-8") as f:
    transcript = json.load(f)

with open("temp/jobs.json", "r", encoding="utf-8") as f:
    jobs = json.load(f)

# Inspect transcript segments in the first 240s
words = transcript["all_words"]
print(f"Total words: {len(words)}")

# Let's see boundary detection
def detect_intro_boundary(words, segments, duration):
    # Transition keywords indicating start of regular episode
    transition_phrases = [
        "before starting today",
        "before we get started",
        "before we start",
        "before starting this",
        "welcome to",
        "welcome back to",
        "in today's episode",
        "today's guest",
        "our guest today",
        "my guest today",
        "without further ado",
        "let's dive in",
        "brought to you by",
        "sponsor"
    ]
    for seg in segments:
        if 40.0 <= seg["start"] <= 260.0:
            text_lower = seg["text"].lower()
            for phrase in transition_phrases:
                if phrase in text_lower:
                    print(f"Found transition marker '{phrase}' at {seg['start']}s: {seg['text']}")
                    return seg["start"]
    # Fallback for long videos (>10 mins)
    if duration > 600.0:
        return min(210.0, duration)
    return duration

boundary = detect_intro_boundary(words, transcript.get("segments", []), 3200.0)
print(f"Detected Intro Boundary: {boundary}s")

# Let's inspect candidate clips in this window
from src.hype_detector.audio_energy import AudioEnergyAnalyzer

with open("temp/jobs.json", "r", encoding="utf-8") as f:
    jobs = json.load(f)

job_data = jobs.get("cb21787d", {})
# audio_path
audio_features = AudioEnergyAnalyzer().analyze_audio("temp/ULvplwBTbQk_audio.wav")

engine = HypeFusionEngine(min_clip_duration=16.0, max_clip_duration=45.0, sliding_step=3.0)
# We can pass duration = boundary so it only scans [0, boundary]!
fake_features = dict(audio_features)
fake_features["duration"] = boundary

llm_scorer = LLMSemanticScorer()
clips = engine.find_top_clips(
    transcript_data=transcript,
    audio_features=fake_features,
    heatmap=[],
    llm_scorer=llm_scorer,
    top_k=5
)

print(f"\n--- Discovered {len(clips)} Top Clips from Intro (0s - {boundary:.1f}s) ---")
for i, c in enumerate(clips, 1):
    print(f"\nClip {i}: [{c['start']}s -> {c['end']}s] ({c['duration']}s)")
    print(f"Title: {c.get('viral_title')}")
    print(f"Banner: {c.get('hook_banner_text')}")
    print(f"Score: {c.get('final_hype_score')}")
    print(f"Text: {c.get('text')}")

