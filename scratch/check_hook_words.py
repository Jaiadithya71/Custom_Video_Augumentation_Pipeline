import json

with open('temp/ULvplwBTbQk_transcript.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

words = data.get('all_words', [])
window_words = [w for w in words if 68.0 <= w['start'] <= 95.0]
for w in window_words:
    print(f"{w['start']:05.2f}s - {w['end']:05.2f}s: {w['word']}")
