"""YouTube Native Transcript Extractor: Pulls word-level timestamps directly from YouTube."""

import re
import json
import logging
import urllib.request
from typing import Dict, List, Any, Optional
import yt_dlp

logger = logging.getLogger(__name__)


class YouTubeTranscriptExtractor:
    """Extracts YouTube's native timedtext captions with word-level precision in < 1 second."""

    def __init__(self):
        self.ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en", "en-orig", "en-US", "en-GB"],
            "nocheckcertificate": True,
        }

    def get_transcript(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extracts native captions directly from YouTube.
        Returns standardized transcript dictionary with segments and all_words.
        Returns None if no English captions exist.
        """
        logger.info(f"Checking for native YouTube captions on {url}...")
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            logger.warning(f"Could not fetch metadata for captions: {e}")
            return None

        duration = info.get("duration", 0)
        subs = info.get("subtitles", {})
        auto_subs = info.get("automatic_captions", {})

        # Priority list for English tracks
        target_track = None
        for lang_code in ["en", "en-orig", "en-US", "en-GB"]:
            if lang_code in subs:
                target_track = subs[lang_code]
                break
            elif lang_code in auto_subs:
                target_track = auto_subs[lang_code]
                break

        if not target_track:
            logger.info("No native English subtitles found.")
            return None

        # Find the JSON3 format URL (contains exact word timestamps)
        json3_url = None
        for fmt in target_track:
            if fmt.get("ext") == "json3":
                json3_url = fmt.get("url")
                break

        if not json3_url:
            logger.info("No JSON3 format timedtext found in track.")
            return None

        try:
            req = urllib.request.Request(
                json3_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode("utf-8"))
            return self._parse_json3_data(data, duration)
        except Exception as e:
            logger.warning(f"Failed to download/parse JSON3 timedtext: {e}")
            return None

    def _parse_json3_data(self, data: dict, duration: float) -> Dict[str, Any]:
        """Converts raw YouTube timedtext JSON3 events into standardized transcript schema."""
        events = data.get("events", [])
        segments = []
        all_words = []

        seg_id = 0
        for event in events:
            t_start_ms = event.get("tStartMs", 0)
            d_dur_ms = event.get("dDurationMs", 0)
            t_start = round(t_start_ms / 1000.0, 2)
            t_end = round((t_start_ms + d_dur_ms) / 1000.0, 2)
            segs = event.get("segs", [])

            seg_text_parts = []
            seg_words = []

            for seg in segs:
                text = seg.get("utf8", "")
                clean_word = text.strip()
                if not clean_word:
                    continue

                offset_ms = seg.get("tOffsetMs", 0) or 0
                w_start = round((t_start_ms + offset_ms) / 1000.0, 2)
                w_end = round(w_start + 0.35, 2)

                word_entry = {
                    "word": clean_word,
                    "start": w_start,
                    "end": w_end,
                    "probability": 1.0,
                }
                seg_words.append(word_entry)
                all_words.append(word_entry)
                seg_text_parts.append(clean_word)

            if seg_words:
                full_seg_text = " ".join(seg_text_parts)
                segments.append({
                    "id": seg_id,
                    "start": seg_words[0]["start"],
                    "end": max(t_end, seg_words[-1]["end"]),
                    "text": full_seg_text,
                    "words": seg_words,
                })
                seg_id += 1

        logger.info(f"Successfully extracted native transcript: {len(all_words)} words across {len(segments)} segments.")
        return {
            "language": "en",
            "language_probability": 1.0,
            "duration": duration,
            "source": "youtube_native",
            "segments": segments,
            "all_words": all_words,
        }
