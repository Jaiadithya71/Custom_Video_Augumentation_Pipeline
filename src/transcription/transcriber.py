"""Transcription Module: Uses faster-whisper to generate word-level timestamps."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """Wrapper around faster-whisper providing word-level timestamps and caching."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "auto",
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model: Optional[WhisperModel] = None

    @property
    def model(self) -> WhisperModel:
        """Lazy load the Whisper model."""
        if self._model is None:
            logger.info(f"Loading faster-whisper model: {self.model_size} ({self.device})...")
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    def transcribe(
        self,
        audio_path: str,
        cache_path: Optional[str] = None,
        language: str = "en",
    ) -> Dict[str, Any]:
        """
        Transcribes audio file with word-level timestamps.
        If cache_path exists, loads directly from cache.
        """
        if cache_path and Path(cache_path).exists():
            logger.info(f"Loading cached transcript from {cache_path}")
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)

        logger.info(f"Transcribing {audio_path} with word-level timestamps...")
        segments, info = self.model.transcribe(
            audio_path,
            language=language,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        transcript_data: Dict[str, Any] = {
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration,
            "segments": [],
            "all_words": [],
        }

        for segment in segments:
            seg_words = []
            if segment.words:
                for w in segment.words:
                    word_entry = {
                        "word": w.word.strip(),
                        "start": round(w.start, 2),
                        "end": round(w.end, 2),
                        "probability": round(w.probability, 2),
                    }
                    seg_words.append(word_entry)
                    transcript_data["all_words"].append(word_entry)

            transcript_data["segments"].append(
                {
                    "id": segment.id,
                    "start": round(segment.start, 2),
                    "end": round(segment.end, 2),
                    "text": segment.text.strip(),
                    "words": seg_words,
                }
            )

        if cache_path:
            Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(transcript_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Transcript saved to {cache_path}")

        return transcript_data

    @staticmethod
    def get_words_in_window(transcript: Dict[str, Any], start_sec: float, end_sec: float) -> List[Dict[str, Any]]:
        """Filters words that fall within [start_sec, end_sec]."""
        return [
            w for w in transcript.get("all_words", [])
            if w["start"] >= start_sec and w["end"] <= end_sec
        ]
