import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

img_path = Path("scratch/clip1_examination/clip1_7.0s.jpg")
img = Image.open(img_path).convert("RGBA")
W, H = img.size # 1080 x 1920

# 1. GENERATE YOUTUBE SHORTS SIMULATOR OVERLAY
yt_img = img.copy()
overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
draw = ImageDraw.Draw(overlay)

# Top Bar (status & search)
draw.text((60, 80), "Shorts", fill=(255, 255, 255, 240), font_size=42)
draw.text((W - 250, 80), "🔍   📷   ⋮", fill=(255, 255, 255, 230), font_size=42)

# Right Action Bar (Likes, comments, share)
action_x = W - 140
icons = [
    ("👍", "240K", 1000),
    ("👎", "Dislike", 1140),
    ("💬", "1.8K", 1280),
    ("↗️", "Share", 1420),
    ("🔀", "Remix", 1560),
]
for symbol, label, y in icons:
    # Shadow/text
    draw.text((action_x, y), symbol, fill=(255, 255, 255, 255), font_size=52)
    draw.text((action_x - 10, y + 60), label, fill=(255, 255, 255, 240), font_size=24)

# Spinning audio disc at bottom right
draw.ellipse((action_x - 10, 1700, action_x + 60, 1770), fill=(40, 40, 40, 240), outline=(255, 255, 255, 180), width=3)
draw.text((action_x + 10, 1715), "🎵", fill=(255, 255, 255, 240), font_size=30)

# Bottom Channel Bar
draw.ellipse((60, 1600, 130, 1670), fill=(37, 99, 235, 255))
draw.text((80, 1615), "@", fill=(255, 255, 255, 255), font_size=36)
draw.text((150, 1620), "@RajShamani", fill=(255, 255, 255, 255), font_size=36)
draw.rounded_rectangle((410, 1615, 590, 1665), radius=25, fill=(220, 38, 38, 255))
draw.text((435, 1625), "Subscribe", fill=(255, 255, 255, 255), font_size=28)

# Caption & Audio ticker
draw.text((60, 1690), "Sunita Williams On Space Missions & Danger #shorts #space", fill=(255, 255, 255, 230), font_size=30)
draw.text((60, 1740), "🎵 Original audio - Raj Shamani ft. Sunita Williams", fill=(255, 255, 255, 200), font_size=26)

out_yt = Image.alpha_composite(yt_img, overlay)
out_yt.convert("RGB").save("scratch/clip1_examination/clip1_yt_shorts_preview.jpg", quality=92)
print("Saved YouTube Shorts preview composite!")

# 2. GENERATE SAFE ZONES GUIDE OVERLAY
safe_img = img.copy()
safe_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sdraw = ImageDraw.Draw(safe_overlay)

# Top obstruction: top 240px
sdraw.rectangle((0, 0, W, 240), fill=(239, 68, 68, 70), outline=(239, 68, 68, 200), width=3)
sdraw.text((W//2 - 250, 100), "⚠️ TOP HEADER / STATUS OBSTRUCTION", fill=(254, 202, 202, 240), font_size=28)

# Bottom obstruction: bottom 360px
sdraw.rectangle((0, H - 360, W, H), fill=(239, 68, 68, 70), outline=(239, 68, 68, 200), width=3)
sdraw.text((W//2 - 300, H - 200), "⚠️ BOTTOM CAPTION & AUDIO OBSTRUCTION", fill=(254, 202, 202, 240), font_size=28)

# Right obstruction: right 180px
sdraw.rectangle((W - 180, 240, W, H - 360), fill=(245, 158, 11, 60), outline=(245, 158, 11, 200), width=3)

# Center Recommended Safe Zone
sdraw.rectangle((60, 280, W - 200, H - 400), outline=(52, 211, 153, 240), width=6)
sdraw.text((100, 320), "✅ RECOMMENDED SAFE ZONE (Faces, Subtitles, Hooks)", fill=(167, 243, 208, 255), font_size=32)

out_safe = Image.alpha_composite(safe_img, safe_overlay)
out_safe.convert("RGB").save("scratch/clip1_examination/clip1_safe_zones_preview.jpg", quality=92)
print("Saved Safe Zones preview composite!")
