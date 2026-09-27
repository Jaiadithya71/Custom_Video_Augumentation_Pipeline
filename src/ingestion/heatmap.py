"""Heatmap Parser Module: Extracts YouTube's 'Most Replayed' engagement graph."""

import re
import json
import logging
from typing import List, Tuple, Optional
import requests

logger = logging.getLogger(__name__)


class YouTubeHeatmapExtractor:
    """Scrapes and extracts normalized heat/replay density from YouTube watch pages."""

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.USER_AGENT})

    def extract_heatmap(self, video_url_or_id: str) -> List[Tuple[float, float]]:
        """
        Extracts the (timestamp_in_seconds, normalized_intensity) list.
        Returns empty list if video does not have enough views for heatmap.
        """
        video_id = self._extract_video_id(video_url_or_id)
        watch_url = f"https://www.youtube.com/watch?v={video_id}"

        try:
            response = self.session.get(watch_url, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch watch page. HTTP {response.status_code}")
                return []

            html = response.text
            return self._parse_heatmap_from_html(html)
        except Exception as e:
            logger.warning(f"Error extracting heatmap for {video_id}: {e}")
            return []

    def _extract_video_id(self, url_or_id: str) -> str:
        match = re.search(r"(?:v=|\/|youtu\.be\/)([0-9A-Za-z_-]{11})", url_or_id)
        if match:
            return match.group(1)
        return url_or_id

    def _parse_heatmap_from_html(self, html: str) -> List[Tuple[float, float]]:
        """Finds ytInitialData and traverses markers to find heat markers."""
        # Find ytInitialData JSON in HTML
        match = re.search(r"var ytInitialData\s*=\s*({.+?});</script>", html)
        if not match:
            match = re.search(r"ytInitialData\s*=\s*({.+?});", html)

        if not match:
            return []

        try:
            data = json.loads(match.group(1))
            return self._find_markers_in_json(data)
        except json.JSONDecodeError:
            return []

    def _find_markers_in_json(self, data: dict) -> List[Tuple[float, float]]:
        """Recursively search for timedMarkerDecorationsRenderer or heatMarkerIntensityScoreNormalized."""
        results = []

        def search_dict(d):
            if isinstance(d, dict):
                # Check for timedMarkerDecorationsRenderer
                if "timedMarkerDecorationsRenderer" in d:
                    renderer = d["timedMarkerDecorationsRenderer"]
                    decorations = renderer.get("decorations", [])
                    for dec in decorations:
                        timed_marker = dec.get("timedMarkerDecorationRenderer", {})
                        norm_score = timed_marker.get("intensityScoreNormalized")
                        start_ms = timed_marker.get("visibleTimeRangeStartMillis")
                        if norm_score is not None and start_ms is not None:
                            results.append((float(start_ms) / 1000.0, float(norm_score)))

                # Check for direct keyMoments / heatMarkers
                if "heatMarkerIntensityScoreNormalized" in d:
                    norm_score = d.get("heatMarkerIntensityScoreNormalized")
                    start_ms = d.get("timeRangeStartMillis", 0)
                    results.append((float(start_ms) / 1000.0, float(norm_score)))

                for v in d.values():
                    search_dict(v)
            elif isinstance(d, list):
                for item in d:
                    search_dict(item)

        search_dict(data)
        results.sort(key=lambda x: x[0])
        return results

    @staticmethod
    def get_heat_at_time(heatmap: List[Tuple[float, float]], time_sec: float) -> float:
        """Returns interpolated heat score [0.0 - 1.0] for a given timestamp."""
        if not heatmap:
            return 0.0

        if time_sec <= heatmap[0][0]:
            return heatmap[0][1]
        if time_sec >= heatmap[-1][0]:
            return heatmap[-1][1]

        for i in range(len(heatmap) - 1):
            t1, score1 = heatmap[i]
            t2, score2 = heatmap[i + 1]
            if t1 <= time_sec <= t2:
                # Linear interpolation
                factor = (time_sec - t1) / (t2 - t1) if (t2 - t1) > 0 else 0
                return score1 + factor * (score2 - score1)

        return 0.0
