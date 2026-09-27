"""Audio Energy Module: Extracts RMS loudness, pitch variance, and speech velocity."""

import logging
from typing import Dict, List, Any, Tuple
import numpy as np
import soundfile as sf
import librosa

logger = logging.getLogger(__name__)


class AudioEnergyAnalyzer:
    """Analyzes audio to detect volume peaks, pitch inflections, and speech velocity."""

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate

    def analyze_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Loads audio and calculates frame-level RMS energy and pitch statistics.
        Returns normalized continuous energy curves.
        """
        logger.info(f"Analyzing audio acoustics from {audio_path}...")
        y, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True)
        duration = librosa.get_duration(y=y, sr=sr)

        # 1. Compute RMS Energy (Loudness)
        hop_length = int(sr * 0.5)  # 0.5-second windows
        frame_length = int(sr * 1.0)
        rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
        rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)

        # Normalize RMS with Z-Score
        rms_mean = np.mean(rms)
        rms_std = np.std(rms) if np.std(rms) > 0 else 1.0
        z_rms = (rms - rms_mean) / rms_std
        # Clamp to 0.0 - 1.0 range via sigmoid
        norm_rms = 1.0 / (1.0 + np.exp(-z_rms))

        # 2. Compute Pitch (F0) Inflection (using fast spectral centroid as proxy for vocal pitch brightness)
        spec_cent = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
        cent_mean = np.mean(spec_cent)
        cent_std = np.std(spec_cent) if np.std(spec_cent) > 0 else 1.0
        z_cent = (spec_cent - cent_mean) / cent_std
        norm_pitch = 1.0 / (1.0 + np.exp(-z_cent))

        return {
            "duration": duration,
            "times": rms_times.tolist(),
            "norm_rms": norm_rms.tolist(),
            "norm_pitch": norm_pitch.tolist(),
        }

    def score_window(
        self,
        audio_features: Dict[str, Any],
        start_sec: float,
        end_sec: float,
        words_in_window: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """
        Computes the acoustic score for a specific [start_sec, end_sec] candidate window.
        Includes loudness (RMS), pitch variance, and speech velocity (WPM).
        """
        times = np.array(audio_features["times"])
        mask = (times >= start_sec) & (times <= end_sec)

        if not np.any(mask):
            return {"rms_score": 0.5, "pitch_score": 0.5, "wpm_score": 0.5}

        window_rms = np.mean(np.array(audio_features["norm_rms"])[mask])
        window_pitch_std = np.std(np.array(audio_features["norm_pitch"])[mask])

        # Pitch dynamism: higher variance = less monotone speech
        pitch_score = float(np.clip(window_pitch_std * 2.0, 0.0, 1.0))

        # Words Per Minute (WPM)
        duration_min = (end_sec - start_sec) / 60.0
        word_count = len(words_in_window)
        wpm = (word_count / duration_min) if duration_min > 0 else 0

        # Normal conversational speech is 130-160 WPM. Excited/fast speech is 170-220 WPM.
        # Score accelerates between 140 and 200 WPM
        wpm_score = float(np.clip((wpm - 120.0) / 80.0, 0.0, 1.0))

        return {
            "rms_score": float(np.clip(window_rms, 0.0, 1.0)),
            "pitch_score": pitch_score,
            "wpm_score": wpm_score,
            "wpm": round(wpm, 1),
        }
