import sys
sys.path.insert(0, '.')
import json
from scratch.test_engine_class import HookDiscoveryEngine
from src.hype_detector.audio_energy import AudioEnergyAnalyzer
from src.hype_detector.llm_scorer import LLMSemanticScorer

with open('temp/ULvplwBTbQk_transcript.json', 'r', encoding='utf-8') as f:
    transcript = json.load(f)

audio_features = AudioEnergyAnalyzer().analyze_audio('temp/ULvplwBTbQk_audio.wav')
engine = HookDiscoveryEngine(min_clip_duration=16.0, max_clip_duration=45.0)
llm_scorer = LLMSemanticScorer()

top_clips = engine.discover_top_hooks(
    transcript_data=transcript,
    audio_features=audio_features,
    heatmap=[],
    llm_scorer=llm_scorer,
    top_k=3
)

print(f'\n=== DISCOVERED {len(top_clips)} VIRAL HOOKS ===')
for i, c in enumerate(top_clips, 1):
    print(f"\nClip {i}: [{c['start']}s -> {c['end']}s] ({c['duration']}s)")
    print(f"Title: {c.get('viral_title')}")
    print(f"Banner: {c.get('hook_banner_text')}")
    print(f"Score: {c.get('final_hype_score')}")
    print(f"Text: {c.get('text')[:120]}...")
