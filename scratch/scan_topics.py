import json

with open('temp/ULvplwBTbQk_transcript.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

segments = data.get('segments', [])
print(f"Total segments: {len(segments)}")

# Look for segments with question marks or high drama keywords
keywords = ['scared', 'death', 'died', 'lost', 'explode', 'life', 'alien', 'god', 'survive', 'danger', 'fail', 'fear', 'alone']
interesting = []

for s in segments:
    text = s.get('text', '')
    matches = [k for k in keywords if k in text.lower()]
    if matches or '?' in text:
        interesting.append({
            'start': s['start'],
            'end': s['end'],
            'duration': round(s['end'] - s['start'], 1),
            'matches': matches,
            'text': text[:100]
        })

print(f"Found {len(interesting)} interesting segments. Sample:")
for item in interesting[:15]:
    print(f"[{item['start']:06.1f}s -> {item['end']:06.1f}s] ({item['matches']}) {item['text']}")
