"""
Subtitle Generator: Creates OpenShorts / Hormozi-style kinetic karaoke ASS subtitles.
Features word-by-word active scaling pulse, high-contrast outlines, and contextual emoji injection.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import re


EMOJI_KEYWORDS = {
    "explosion": "💥",
    "explode": "💥",
    "scared": "😱",
    "fear": "😨",
    "danger": "⚠️",
    "dangerous": "⚠️",
    "space": "🚀",
    "satellite": "🛰️",
    "rocket": "🚀",
    "tragedy": "💔",
    "survivors": "🕊️",
    "fire": "🔥",
    "money": "💰",
    "rich": "💰",
    "mindset": "🧠",
    "brain": "🧠",
    "secret": "🤫",
    "truth": "🎯",
    "mistake": "❌",
    "death": "💀",
    "died": "💀",
    "memory": "🕊️",
    "love": "❤️",
    "crazy": "⚡",
    "pressure": "🔥",
}


class SubtitleGenerator:
    """
    Generates Advanced SubStation Alpha (.ass) subtitle scripts with
    Hormozi-style kinetic word-by-word highlights, pop scaling, and vertical safe zones.
    """

    def __init__(
        self,
        font_name: str = "Arial Black",
        font_size: int = 58,
        margin_bottom: int = 380,
        primary_color: str = "&H00FFFFFF",    # Pure White
        highlight_color: str = "&H002EFFFF",  # Electric Yellow / Gold
        outline_color: str = "&H00000000",    # Solid Black
        back_color: str = "&H80000000",       # Deep Drop Shadow
        max_words_per_line: int = 3,
        enable_emojis: bool = True,
    ):
        self.font_name = font_name
        self.font_size = font_size
        self.margin_bottom = margin_bottom
        self.primary_color = primary_color
        self.highlight_color = highlight_color
        self.outline_color = outline_color
        self.back_color = back_color
        self.max_words_per_line = max_words_per_line
        self.enable_emojis = enable_emojis

    def generate_ass_file(
        self,
        words: List[Dict[str, Any]],
        clip_start: float,
        output_ass_path: str,
        video_width: int = 1080,
        video_height: int = 1920,
        margin_bottom: Optional[int] = None,
    ) -> Path:
        """
        Builds a .ass file where words in each phrase are highlighted sequentially
        with a kinetic pop effect as they are spoken. All timestamps are strictly monotonic.
        """
        out_path = Path(output_ass_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        eff_margin_bottom = margin_bottom if margin_bottom is not None else self.margin_bottom

        # 1. Normalize and sanitize word timestamps relative to clip_start
        rel_words = []
        for w in words:
            raw_word = str(w.get("word", "")).strip()
            # Remove bracketed sound effects like [music], [applause]
            clean_word = re.sub(r"\[.*?\]", "", raw_word).strip()
            # Strip scraper artifacts (>>, >, --)
            clean_word = re.sub(r"^[>\-\s]+", "", clean_word).strip()
            # Skip filler words (um, uh, cuz, erm, etc.)
            filler_tokens = {"um", "uh", "cuz", "erm", "hmm"}
            if clean_word.lower().strip(".,?!\"'") in filler_tokens:
                continue

            if not clean_word:
                continue

            rel_words.append({
                "word": clean_word,
                "start": max(0.0, float(w["start"]) - clip_start),
                "end": max(0.0, float(w["end"]) - clip_start),
            })

        if not rel_words:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write("[Script Info]\nTitle: Empty\n[Events]\n")
            return out_path

        # 2. Group words into short visual punchy lines (2-3 words each)
        grouped_lines = []
        current_group = []
        for idx, w in enumerate(rel_words):
            current_group.append(w)
            
            # Sentence terminal punctuation
            has_sentence_end = bool(re.search(r"[.?!]$", w["word"]))
            
            # Natural speech pause (> 0.45s)
            has_pause = False
            if idx < len(rel_words) - 1:
                pause_gap = rel_words[idx + 1]["start"] - w["end"]
                if pause_gap > 0.45:
                    has_pause = True

            if len(current_group) >= self.max_words_per_line or has_sentence_end or has_pause:
                grouped_lines.append(current_group)
                current_group = []

        if current_group:
            grouped_lines.append(current_group)

        # 3. Write ASS script header with bold styling and heavy stroke
        header = f"""[Script Info]
Title: Content Agent Kinetic Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {video_width}
PlayResY: {video_height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{self.font_name},{self.font_size},{self.primary_color},{self.highlight_color},{self.outline_color},{self.back_color},-1,0,0,0,100,100,0,0,1,5.0,2.5,2,40,40,{eff_margin_bottom},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        events = []
        for k, group in enumerate(grouped_lines):
            for i, active_word in enumerate(group):
                w_start = active_word["start"]

                # Strict Non-Stacking: Clamp w_end to the start of the next event
                if i < len(group) - 1:
                    w_end = group[i + 1]["start"]
                else:
                    w_end = active_word["end"]
                    if k < len(grouped_lines) - 1:
                        next_group_start = grouped_lines[k + 1][0]["start"]
                        if w_end > next_group_start:
                            w_end = next_group_start

                if w_end <= w_start:
                    w_end = w_start + 0.08

                w_start_str = self._format_ass_time(w_start)
                w_end_str = self._format_ass_time(w_end)

                # Build styled line: all words white, active word with 112% pop and electric highlight
                line_parts = []
                for j, item in enumerate(group):
                    raw_text = item["word"].upper()
                    base_token = item["word"].lower().strip(".,?!\"'")
                    emoji_badge = ""
                    if self.enable_emojis and base_token in EMOJI_KEYWORDS:
                        emoji_badge = f" {EMOJI_KEYWORDS[base_token]}"

                    if i == j:
                        # Active pop scaling + highlight color
                        line_parts.append(
                            f"{{\\c{self.highlight_color}\\fscx112\\fscy112}}{raw_text}{emoji_badge}{{\\r}}"
                        )
                    else:
                        line_parts.append(raw_text)

                styled_text = " ".join(line_parts)
                events.append(f"Dialogue: 0,{w_start_str},{w_end_str},Default,,0,0,0,,{styled_text}")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(header + "\n".join(events) + "\n")

        return out_path

    @staticmethod
    def _format_ass_time(seconds: float) -> str:
        """Converts float seconds into ASS timestamp: H:MM:SS.cs"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centisecs = int(round((seconds - int(seconds)) * 100))
        if centisecs >= 100:
            centisecs = 99
        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"
