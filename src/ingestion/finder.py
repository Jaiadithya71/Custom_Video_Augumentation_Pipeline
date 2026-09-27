"""Viral Video Finder: Discovers and analyzes high-performing long-form YouTube videos."""

import logging
from typing import List, Dict, Any, Optional
import yt_dlp

logger = logging.getLogger(__name__)

NICHE_PRESETS = {
    "podcasts": "trending podcast interview full episode",
    "tech_ai": "artificial intelligence technology interview podcast",
    "business": "business wealth investing finance interview",
    "self_improvement": "psychology discipline mindset habits podcast",
    "science": "science philosophy physics deep dive discussion",
}


class ViralVideoFinder:
    """Discovers high-engagement long-form YouTube videos and scores their viral potential."""

    def __init__(self):
        self.ydl_opts = {
            "quiet": True,
            "extract_flat": True,
            "nocheckcertificate": True,
            "no_warnings": True,
        }

    def find_viral_videos(
        self,
        query_or_niche: str = "podcasts",
        limit: int = 10,
        min_duration_sec: int = 600,   # At least 10 minutes
        max_duration_sec: int = 10800,  # Max 3 hours
    ) -> List[Dict[str, Any]]:
        """
        Searches YouTube for trending long-form videos in a niche,
        filters for suitable duration, and ranks them by engagement.
        """
        search_query = NICHE_PRESETS.get(query_or_niche, query_or_niche)
        search_term = f"ytsearch{limit * 2}:{search_query}"

        logger.info(f"Searching YouTube for viral candidates: '{search_term}'...")

        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                res = ydl.extract_info(search_term, download=False)
                raw_entries = res.get("entries", [])
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

        candidates = []
        for entry in raw_entries:
            if not entry:
                continue

            duration = entry.get("duration") or 0
            if duration < min_duration_sec or duration > max_duration_sec:
                continue

            views = entry.get("view_count") or 0
            video_id = entry.get("id")
            if not video_id:
                continue

            # Calculate Virality Potential Score (0.0 to 10.0)
            # High view count in a long-form video indicates rich clip density
            if views > 10_000_000:
                virality_score = 9.8
            elif views > 5_000_000:
                virality_score = 9.2
            elif views > 1_000_000:
                virality_score = 8.5
            elif views > 500_000:
                virality_score = 7.8
            elif views > 100_000:
                virality_score = 7.0
            else:
                virality_score = 6.0

            candidates.append({
                "id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "title": entry.get("title", "Untitled"),
                "channel": entry.get("uploader") or entry.get("channel") or "Unknown Channel",
                "views": views,
                "views_formatted": self._format_views(views),
                "duration": duration,
                "duration_formatted": self._format_duration(duration),
                "thumbnail": entry.get("thumbnail") or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                "virality_score": virality_score,
            })

            if len(candidates) >= limit:
                break

        # Sort by virality potential
        candidates.sort(key=lambda c: (c["virality_score"], c["views"]), reverse=True)
        return candidates

    @staticmethod
    def _format_views(views: int) -> str:
        if views >= 1_000_000:
            return f"{views / 1_000_000:.1f}M views"
        elif views >= 1_000:
            return f"{views / 1_000:.0f}K views"
        return f"{views} views"

    @staticmethod
    def _format_duration(seconds: int) -> str:
        hrs = seconds // 3600
        mins = (seconds % 3600) // 60
        secs = seconds % 60
        if hrs > 0:
            return f"{hrs}:{mins:02d}:{secs:02d}"
        return f"{mins}:{secs:02d}"
