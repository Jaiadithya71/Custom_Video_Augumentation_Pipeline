import sys
sys.path.insert(0, '.')
import json
from src.hype_detector.fusion import HypeFusionEngine
from src.hype_detector.llm_scorer import LLMSemanticScorer

with open('temp/ULvplwBTbQk_transcript.json', 'r', encoding='utf-8') as f:
    transcript = json.load(f)

times = list(range(0, 5450))
audio_features = {
    'duration': 5444.0,
    'times': times,
    'norm_rms': [0.5] * len(times),
    'norm_pitch': [0.5] * len(times),
}

# Load heatmap from jobs.json
with open('temp/jobs.json', 'r', encoding='utf-8') as f:
    jobs = json.load(f)

job = jobs.get('cb21787d', {})
raw_heatmap = job.get('video_info', {}).get('heatmap', [])
heatmap = [(pt['start_time'], pt['value']) for pt in raw_heatmap]
profile = job.get('narrative_profile', {})

print(f"Heatmap points: {len(heatmap)}")
fusion = HypeFusionEngine(min_clip_duration=18.0)
scorer = LLMSemanticScorer()

top_clips = fusion.find_top_clips(
    transcript_data=transcript,
    audio_features=audio_features,
    heatmap=heatmap,
    llm_scorer=scorer,
    top_k=3,
    narrative_profile=profile
)

print(f"\nTop {len(top_clips)} selected clips:")
for idx, c in enumerate(top_clips):
    print(f"\n--- CLIP {idx+1} ---")
    print(f"Time: {c['start']:.2f}s -> {c['end']:.2f}s (Duration: {c['duration']}s)")
    print(f"Score: {c['final_hype_score']}")
    print(f"Title: {c.get('viral_title', '')}")
    print(f"Banner: {c.get('hook_banner_text', '')}")
    print(f"Text: {c['text'][:140]}...")
