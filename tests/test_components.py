"""Unit tests and smoke tests for Content Agent components."""

import unittest
from pathlib import Path
from src.video_engine.subtitle_gen import SubtitleGenerator
from src.ingestion.heatmap import YouTubeHeatmapExtractor
from src.hype_detector.llm_scorer import LLMSemanticScorer


class TestContentAgent(unittest.TestCase):

    def test_subtitle_generator(self):
        """Tests that .ass subtitles are generated with correct styling and timing."""
        sub_gen = SubtitleGenerator()
        words = [
            {"word": "The", "start": 10.0, "end": 10.3},
            {"word": "biggest", "start": 10.3, "end": 10.8},
            {"word": "mistake", "start": 10.8, "end": 11.2},
            {"word": "people", "start": 11.2, "end": 11.5},
            {"word": "make", "start": 11.5, "end": 11.8},
        ]
        out_path = Path("./temp/test_subtitles.ass")
        created = sub_gen.generate_ass_file(words, clip_start=10.0, output_ass_path=str(out_path))
        self.assertTrue(created.exists())

        with open(created, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("[Script Info]", content)
            self.assertIn("Dialogue:", content)
            self.assertIn("MISTAKE", content)

        if out_path.exists():
            out_path.unlink()

    def test_heatmap_interpolation(self):
        """Tests linear interpolation of YouTube engagement curves."""
        heatmap = [(10.0, 0.2), (20.0, 0.8), (30.0, 0.4)]
        self.assertAlmostEqual(YouTubeHeatmapExtractor.get_heat_at_time(heatmap, 10.0), 0.2)
        self.assertAlmostEqual(YouTubeHeatmapExtractor.get_heat_at_time(heatmap, 15.0), 0.5)
        self.assertAlmostEqual(YouTubeHeatmapExtractor.get_heat_at_time(heatmap, 20.0), 0.8)
        self.assertAlmostEqual(YouTubeHeatmapExtractor.get_heat_at_time(heatmap, 5.0), 0.2)

    def test_heuristic_scorer(self):
        """Tests that heuristic fallback calculates scores and hook banners properly."""
        scorer = LLMSemanticScorer(api_key=None)
        text = "The biggest secret to making money is never giving up. You must stay focused."
        result = scorer.score_segment(text, duration_sec=35.0)
        self.assertIn("hook_score", result)
        self.assertIn("semantic_score", result)
        self.assertIn("viral_title", result)
        self.assertGreater(result["hook_score"], 5.0)


if __name__ == "__main__":
    unittest.main()
