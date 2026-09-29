import re
import os
import subprocess

def generate_hotclip_mouthsync():
    base_ass_path = "temp/ULvplwBTbQk_short_1.ass"
    hotclip_ass_path = "temp/demo_hotclip.ass"
    openshorts_ass_path = "temp/demo_openshorts.ass"
    
    with open(base_ass_path, "r", encoding="utf-8") as f:
        base_lines = f.readlines()
        
    events = [line for line in base_lines if line.startswith("Dialogue:")]
    print(f"Loaded {len(events)} mouth-synced dialogue events from {base_ass_path}")

    # ==========================================
    # 1. GENERATE HOTCLIP ASS (Mouth-to-Letter Sync)
    # Style: Minimalist Inter/Arial, 1080x1920, MarginV 380
    # Active Highlight: HotClip Ember/Flame Orange (&H0045FF&) + 114% kinetic pop
    # ==========================================
    hotclip_header = """[Script Info]
Title: HotClip Dynamic Mouth-Synced Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Minimal,Arial,66,&H00FFFFFF,&H0045FF,&H00151515,&H80000000,-1,0,0,0,100,100,0,0,1,5.0,2.0,2,60,60,380,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    hotclip_events = []
    for ev in events:
        # Replace Style 'Default' with 'Minimal'
        # Replace base highlight &H002EFFFF with HotClip Flame Orange &H0045FF and 114% scale
        ev_mod = ev.replace(",Default,", ",Minimal,")
        ev_mod = ev_mod.replace(r"{\c&H002EFFFF\fscx112\fscy112}", r"{\c&H0045FF&\fscx114\fscy114}")
        hotclip_events.append(ev_mod)
        
    with open(hotclip_ass_path, "w", encoding="utf-8-sig") as f:
        f.write(hotclip_header + "".join(hotclip_events))
    print(f"Created HotClip synced ASS: {hotclip_ass_path} ({len(hotclip_events)} events)")

    # ==========================================
    # 2. GENERATE OPENSHORTS ASS (Mouth-to-Letter Sync)
    # Style: Anton Uppercase, PlayResY 288, MarginV 43
    # Active Highlight: OpenShorts Yellow &H00E5FF& + 108% pop
    # ==========================================
    openshorts_header = """[Script Info]
Title: OpenShorts Deterministic Karaoke Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 162
PlayResY: 288

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Anton,26,&H00FFFFFF,&H00E5FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3.2,0.8,2,10,10,43,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    openshorts_events = []
    for ev in events:
        # In OpenShorts: yellow highlight &H00E5FF& + 108% pop, no emojis, all uppercase
        ev_clean = re.sub(r'[\U00010000-\U0010ffff]', '', ev) # Strip emojis for strict Anton look
        ev_mod = ev_clean.replace(r"{\c&H002EFFFF\fscx112\fscy112}", r"{\c&H00E5FF&\fscx108\fscy108}")
        # Ensure MarginV is 43 in dialogue event if specified or 0 to inherit style
        openshorts_events.append(ev_mod)
        
    with open(openshorts_ass_path, "w", encoding="utf-8-sig") as f:
        f.write(openshorts_header + "".join(openshorts_events))
    print(f"Created OpenShorts synced ASS: {openshorts_ass_path} ({len(openshorts_events)} events)")

    # ==========================================
    # 3. RE-RENDER HOTCLIP MASTER
    # ==========================================
    print("Re-rendering HotClip Master with Mouth-to-Letter Sync...")
    out_hotclip = "output/demo_hotclip_master.mp4"
    video_path = "temp/ULvplwBTbQk_video.mp4"
    sfx_whoosh = "temp/sfx_whoosh.wav"
    sfx_pop = "temp/sfx_pop.wav"
    clip_start = 71.84
    clip_end = 99.63
    
    escaped_hotclip_ass = hotclip_ass_path.replace("\\", "/").replace(":", "\\:")
    zoom_expr = "1.0+0.06*sin(2*3.14159*on/(30*10))+if(between(on,180,270),0.06,0)"
    
    vf_hotclip = (
        f"crop=608:1080:656:0,"
        f"scale=1080:1920,"
        f"zoompan=z='{zoom_expr}':x='iw/2-(iw/zoom)/2':y='ih*0.42-(ih/zoom)/2':d=1:fps=30:s=1080x1920,"
        f"ass='{escaped_hotclip_ass}'"
    )
    
    filter_complex = (
        f"[0:v]{vf_hotclip}[v_out];"
        f"[1:a]adelay=4000|4000,volume=0.35[sfx1];"
        f"[2:a]adelay=200|200,volume=0.4[sfx2];"
        f"[0:a][sfx1][sfx2]amix=inputs=3:dropout_transition=2:normalize=0[a_out]"
    )
    
    cmd_hotclip = [
        "ffmpeg", "-y",
        "-ss", str(clip_start), "-to", str(clip_end),
        "-i", video_path,
        "-i", sfx_whoosh,
        "-i", sfx_pop,
        "-filter_complex", filter_complex,
        "-map", "[v_out]", "-map", "[a_out]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k",
        out_hotclip
    ]
    
    res = subprocess.run(cmd_hotclip, capture_output=True, text=True)
    if res.returncode == 0:
        print(f"-> SUCCESS! HotClip Master re-rendered: {out_hotclip} ({os.path.getsize(out_hotclip)} bytes)")
    else:
        print(f"-> ERROR HotClip render: {res.stderr[-400:]}")
        return False

    # ==========================================
    # 4. RE-RENDER OPENSHORTS EDL
    # ==========================================
    print("Re-rendering OpenShorts EDL with Mouth-to-Letter Sync...")
    out_openshorts = "output/demo_openshorts_edl.mp4"
    escaped_openshorts_ass = openshorts_ass_path.replace("\\", "/").replace(":", "\\:")
    
    vf_openshorts = (
        f"crop=608:1080:656:0,"
        f"scale=1080:1920,"
        f"eq=contrast=1.10:saturation=1.25:enable='between(t,4,12)',"
        f"zoompan=z='if(between(on,120,270),1.12,1.0)':x='iw/2-(iw/zoom)/2':y='ih*0.45-(ih/zoom)/2':d=1:fps=30:s=1080x1920,"
        f"ass='{escaped_openshorts_ass}'"
    )
    
    cmd_openshorts = [
        "ffmpeg", "-y",
        "-ss", str(clip_start), "-to", str(clip_end),
        "-i", video_path,
        "-vf", vf_openshorts,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k",
        out_openshorts
    ]
    
    res_os = subprocess.run(cmd_openshorts, capture_output=True, text=True)
    if res_os.returncode == 0:
        print(f"-> SUCCESS! OpenShorts EDL re-rendered: {out_openshorts} ({os.path.getsize(out_openshorts)} bytes)")
    else:
        print(f"-> ERROR OpenShorts render: {res_os.stderr[-400:]}")
        return False
        
    print("\nAll videos successfully re-rendered with mouth-to-letter synchronization!")
    return True

if __name__ == "__main__":
    generate_hotclip_mouthsync()
