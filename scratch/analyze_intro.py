import json

with open('temp/ULvplwBTbQk_transcript.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('=== SEGMENTS IN INTRO (0s - 220s) ===')
for s in data.get('segments', []):
    if s['start'] < 220:
        print(f"[{s['start']:6.2f}s -> {s['end']:6.2f}s] {s['text'].strip()}")
