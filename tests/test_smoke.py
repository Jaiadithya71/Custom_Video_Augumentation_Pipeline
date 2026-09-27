"""Comprehensive Smoke Tests for Content Agent.
Tests all pipeline stages end-to-end with synthetic media and live API smoke checks.
"""

import os
import shutil
import unittest
import numpy as np
import cv2
import soundfile as sf
from pathlib import Path

import src
from src.ingestion.downloader import YouTubeDownloader
from src.ingestion.heatmap import YouTubeHeatmapExtractor
from src.transcription.transcriber import WhisperTranscriber
from src.hype_detector.audio_energy import AudioEnergyAnalyzer
from src.hype_detector.llm_scorer import LLMSemanticScorer
from src.hype_detector.fusion import HypeFusionEngine
from src.video_engine.tracker import FaceTracker
from src.video_engine.subtitle_gen import SubtitleGenerator
from src.video_engine.composer import VideoComposer


class TestContentAgentSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = Path("./temp/smoke_tests")
        cls.temp_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if cls.temp_dir.exists():
            shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_01_ffmpeg_available(self):
        """Smoke Test 1: Verify FFmpeg is found and executable."""
        ffmpeg_bin = shutil.which("ffmpeg")
        self.assertIsNotNone(ffmpeg_bin, "FFmpeg executable not found in PATH")
        print(f"\n[SMOKE 1] FFmpeg confirmed at: {ffmpeg_bin}")

    def test_02_synthetic_audio_analysis(self):
        """Smoke Test 2: Generate synthetic audio and test acoustic feature extraction."""
        sr = 16000
        duration = 10.0  # 10 seconds
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        
        # Segment 1 (0-5s): Low volume sine wave (440 Hz)
        audio_part1 = 0.1 * np.sin(2 * np.pi * 440 * t[:int(sr * 5)])
        # Segment 2 (5-10s): High volume excited chirp (880 Hz to 1200 Hz)
        audio_part2 = 0.8 * np.sin(2 * np.pi * 900 * t[int(sr * 5):])
        audio_data = np.concatenate([audio_part1, audio_part2]).astype(np.float32)

        wav_path = self.temp_dir / "synthetic_test.wav"
        sf.write(str(wav_path), audio_data, sr)
        self.assertTrue(wav_path.exists())

        analyzer = AudioEnergyAnalyzer(sample_rate=sr)
        features = analyzer.analyze_audio(str(wav_path))

        self.assertIn("norm_rms", features)
        self.assertIn("norm_pitch", features)
        self.assertGreater(len(features["times"]), 0)

        # Window score: Segment 2 should have higher RMS than Segment 1
        mock_words = [
            {"word": "excited", "start": 6.0, "end": 6.4},
            {"word": "moment", "start": 6.5, "end": 7.0},
        ]
        score_quiet = analyzer.score_window(features, 0.0, 4.0, [])
        score_loud = analyzer.score_window(features, 5.0, 9.0, mock_words)

        self.assertGreater(score_loud["rms_score"], score_quiet["rms_score"])
        print(f"[SMOKE 2] Audio Acoustics: Quiet RMS={score_quiet['rms_score']:.2f}, Loud RMS={score_loud['rms_score']:.2f}")

    def test_03_hype_fusion_and_nms(self):
        """Smoke Test 3: Test multi-signal fusion and NMS candidate selection."""
        mock_transcript = {
            "all_words": [
                {"word": "This", "start": 1.0, "end": 1.3},
                {"word": "is", "start": 1.3, "end": 1.5},
                {"word": "the", "start": 1.5, "end": 1.7},
                {"word": "most", "start": 1.7, "end": 2.0},
                {"word": "insane", "start": 2.0, "end": 2.5},
                {"word": "secret", "start": 2.5, "end": 3.0},
                {"word": "ever.", "start": 3.0, "end": 3.5},
            ]
        }
        mock_audio_features = {
            "duration": 40.0,
            "times": [float(i) for i in range(40)],
            "norm_rms": [0.3] * 20 + [0.9] * 20,
            "norm_pitch": [0.4] * 20 + [0.8] * 20,
        }
        mock_heatmap = [(5.0, 0.2), (25.0, 0.9), (35.0, 0.5)]

        engine = HypeFusionEngine(
            min_clip_duration=2.0,
            max_clip_duration=10.0,
            sliding_step=2.0,
        )
        llm_scorer = LLMSemanticScorer(api_key=None)  # Uses heuristic fallback

        clips = engine.find_top_clips(
            transcript_data=mock_transcript,
            audio_features=mock_audio_features,
            heatmap=mock_heatmap,
            llm_scorer=llm_scorer,
            top_k=2,
        )

        self.assertGreater(len(clips), 0, "No clips extracted by Hype Fusion Engine")
        self.assertIn("final_hype_score", clips[0])
        print(f"[SMOKE 3] Hype Fusion selected top clip: '{clips[0]['viral_title']}' with score {clips[0]['final_hype_score']}")

    def test_04_end_to_end_video_render(self):
        """Smoke Test 4: Generate synthetic 16:9 video, track crop, burn subtitles, render 9:16 Short."""
        test_video_path = self.temp_dir / "synthetic_16x9.mp4"
        width, height, fps, duration = 1280, 720, 24, 3

        # Create synthetic 16:9 video with a moving colored box simulating speaker
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(test_video_path), fourcc, fps, (width, height))

        total_frames = fps * duration
        for f in range(total_frames):
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            # Background dark blue
            frame[:] = (30, 20, 20)
            # Simulated moving face box
            box_x = int(400 + 200 * np.sin(2 * np.pi * f / total_frames))
            box_y = int(250)
            cv2.rectangle(frame, (box_x, box_y), (box_x + 150, box_y + 150), (200, 200, 255), -1)
            cv2.putText(frame, "SPEAKER", (box_x + 10, box_y + 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
            writer.write(frame)
        writer.release()
        self.assertTrue(test_video_path.exists())

        # 1. Track Face / Crop
        tracker = FaceTracker()
        crop_box = tracker.calculate_crop_window(str(test_video_path), 0.0, 3.0)
        crop_x, crop_y, crop_w, crop_h = crop_box
        self.assertGreater(crop_w, 0)
        self.assertGreater(crop_h, 0)

        # 2. Generate Subtitles
        sub_gen = SubtitleGenerator()
        ass_path = self.temp_dir / "test_sub.ass"
        words = [
            {"word": "Testing", "start": 0.2, "end": 0.8},
            {"word": "the", "start": 0.8, "end": 1.1},
            {"word": "pipeline", "start": 1.1, "end": 1.7},
            {"word": "success!", "start": 1.7, "end": 2.5},
        ]
        sub_gen.generate_ass_file(words, clip_start=0.0, output_ass_path=str(ass_path))
        self.assertTrue(ass_path.exists())

        # 3. Render 9:16 Short with VideoComposer
        composer = VideoComposer(output_width=720, output_height=1280)  # fast 720p vertical for test
        out_short = self.temp_dir / "final_test_short.mp4"
        rendered = composer.render_short(
            input_video_path=str(test_video_path),
            start_sec=0.0,
            end_sec=2.5,
            crop_box=crop_box,
            ass_subtitle_path=str(ass_path),
            output_path=str(out_short),
            hook_banner_text="Smoke Test Hook Banner",
        )

        self.assertTrue(rendered.exists(), "Rendered short mp4 file was not created")
        file_size = rendered.stat().st_size
        self.assertGreater(file_size, 1000, f"Rendered short file is suspiciously small ({file_size} bytes)")

        # Verify output video properties
        cap = cv2.VideoCapture(str(rendered))
        out_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        out_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        self.assertEqual(out_w, 720)
        self.assertEqual(out_h, 1280)
        print(f"[SMOKE 4] Video Engine rendered 9:16 Short successfully: {out_w}x{out_h} ({file_size / 1024:.1f} KB)")

    def test_05_live_youtube_metadata_fetch(self):
        """Smoke Test 5: Verify yt-dlp metadata extraction on a public video."""
        test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
        downloader = YouTubeDownloader(temp_dir=str(self.temp_dir))
        info = downloader.get_video_info(test_url)

        self.assertEqual(info["id"], "jNQXAC9IVRw")
        self.assertIn("title", info)
        self.assertGreater(info["duration"], 0)
        print(f"[SMOKE 5] YouTube Metadata Verified: '{info['title']}' ({info['duration']}s)")


if __name__ == "__main__":
    unittest.main()
