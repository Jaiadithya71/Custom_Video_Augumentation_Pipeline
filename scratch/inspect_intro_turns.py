import sys
sys.path.insert(0, ".")
import json
from src.hype_detector.audio_energy import AudioEnergyAnalyzer

with open("temp/ULvplwBTbQk_transcript.json", "r", encoding="utf-8") as f:
    transcript = json.load(f)

words = transcript["all_words"]
boundary = 208.64

# Filter words to intro
intro_words = [w for w in words if w["end"] <= boundary]
print(f"Intro words count: {len(intro_words)}")

# Let's inspect where speaker turns (>>) occur in the intro:
speaker_turns = []
for i, w in enumerate(intro_words):
    if w["word"].startswith(">>") or i == 0:
        speaker_turns.append((w["start"], w["word"], i))

print(f"\nSpeaker turns in intro ({len(speaker_turns)} turns):")
for st, word, idx in speaker_turns:
    print(f"At {st:6.2f}s: {word} (word index {idx})")
