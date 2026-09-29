"""Downloader Module: Uses yt-dlp to download metadata and stream files."""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
import yt_dlp


class YouTubeDownloader:
    """Handles downloading YouTube video metadata, audio streams, and video streams."""

    def __init__(
        self,
        temp_dir: str = "./temp",
        max_resolution: int = 1080,
        max_duration_sec: Optional[float] = 300.0,
    ):
        self.temp_dir = Path(temp_dir)
        self.max_resolution = max_resolution
        self.max_duration_sec = max_duration_sec
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def get_video_info(self, url: str) -> Dict[str, Any]:
        """Fetches metadata without downloading the video."""
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "id": info.get("id"),
                "title": info.get("title"),
                "duration": info.get("duration"),
                "channel": info.get("uploader"),
                "view_count": info.get("view_count"),
                "heatmap": info.get("heatmap"),  # Available on some versions/videos
                "thumbnail": info.get("thumbnail"),
                "original_url": url,
            }

    def download_audio(
        self,
        url: str,
        video_id: Optional[str] = None,
        max_duration_sec: Optional[float] = None,
    ) -> Path:
        """Downloads and extracts 16kHz mono WAV audio (capped to 5-min hook zone by default)."""
        if not video_id:
            info = self.get_video_info(url)
            video_id = info["id"]

        output_path = self.temp_dir / f"{video_id}_audio.wav"
        if output_path.exists():
            return output_path

        max_sec = max_duration_sec if max_duration_sec is not None else self.max_duration_sec

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": str(self.temp_dir / f"{video_id}_raw_audio.%(ext)s"),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                }
            ],
            "postprocessor_args": [
                "-ar", "16000",
                "-ac", "1",
            ],
            "quiet": False,
        }

        if max_sec:
            ydl_opts["download_ranges"] = yt_dlp.utils.download_range_func(None, [(0, max_sec)])
            ydl_opts["force_keyframes_at_cuts"] = True

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        raw_wav = self.temp_dir / f"{video_id}_raw_audio.wav"
        if raw_wav.exists():
            raw_wav.rename(output_path)

        return output_path

    def download_video(
        self,
        url: str,
        video_id: Optional[str] = None,
        max_duration_sec: Optional[float] = None,
    ) -> Path:
        """Downloads the video stream (max 1080p, capped to 5-min hook zone by default)."""
        if not video_id:
            info = self.get_video_info(url)
            video_id = info["id"]

        output_path = self.temp_dir / f"{video_id}_video.mp4"
        if output_path.exists():
            return output_path

        max_sec = max_duration_sec if max_duration_sec is not None else self.max_duration_sec

        ydl_opts = {
            "format": f"bestvideo[height<={self.max_resolution}][ext=mp4]+bestaudio[ext=m4a]/best[height<={self.max_resolution}][ext=mp4]/best",
            "outtmpl": str(output_path),
            "merge_output_format": "mp4",
            "quiet": False,
        }

        if max_sec:
            ydl_opts["download_ranges"] = yt_dlp.utils.download_range_func(None, [(0, max_sec)])
            ydl_opts["force_keyframes_at_cuts"] = True

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return output_path

    def download_clip_section(self, url: str, start_sec: float, end_sec: float, output_path: str) -> Path:
        """Downloads only a specific segment directly using yt-dlp section download."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        ydl_opts = {
            "format": f"bestvideo[height<={self.max_resolution}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": str(out),
            "download_ranges": yt_dlp.utils.download_range_func(None, [(start_sec, end_sec)]),
            "force_keyframes_at_cuts": True,
            "quiet": False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return out
