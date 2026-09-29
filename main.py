"""Main Orchestrator CLI for Content Agent."""

import os
import sys
import argparse
import logging
import json
from pathlib import Path
import yaml

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from src.ingestion.downloader import YouTubeDownloader
from src.ingestion.heatmap import YouTubeHeatmapExtractor
from src.transcription.youtube_transcript import YouTubeTranscriptExtractor
from src.transcription.transcriber import WhisperTranscriber
from src.hype_detector.audio_energy import AudioEnergyAnalyzer
from src.hype_detector.llm_scorer import LLMSemanticScorer
from src.hype_detector.fusion import HypeFusionEngine
from src.video_engine.tracker import FaceTracker
from src.video_engine.subtitle_gen import SubtitleGenerator
from src.video_engine.composer import VideoComposer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ContentAgent")


def load_config(config_path: str = "config/settings.yaml") -> dict:
    if Path(config_path).exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


def process_video(url: str, top_k: int = 3, output_dir: str = "./output"):
    config = load_config()
    out_dir = Path(output_dir)
    temp_dir = Path(config.get("app", {}).get("temp_dir", "./temp"))
    out_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 60)
    print("🎬 CONTENT AGENT: AUTONOMOUS VIRAL CLIPPER PIPELINE")
    print("=" * 60 + "\n")

    # 1. Ingestion
    logger.info("Step 1/5: Ingestion & Metadata Fetching...")
    downloader = YouTubeDownloader(temp_dir=str(temp_dir))
    info = downloader.get_video_info(url)
    video_id = info["id"]
    logger.info(f"Video: '{info['title']}' by {info['channel']} ({info['duration']}s)")

    logger.info("Downloading 16kHz audio stream...")
    audio_path = downloader.download_audio(url, video_id=video_id)

    # 2. Crowd Heatmap
    logger.info("Step 2/5: Extracting YouTube Engagement Heatmap...")
    heatmap_extractor = YouTubeHeatmapExtractor()
    heatmap = heatmap_extractor.extract_heatmap(url)
    logger.info(f"Heatmap points extracted: {len(heatmap)}")

    # 3. Speech-to-Text Transcription (Native first, Whisper fallback)
    cache_path = temp_dir / f"{video_id}_transcript.json"
    transcript = None

    if cache_path.exists():
        logger.info(f"Loading cached transcript from {cache_path}")
        with open(cache_path, "r", encoding="utf-8") as f:
            transcript = json.load(f)
    else:
        logger.info("Step 3/5: Checking for native YouTube word-level captions...")
        yt_extractor = YouTubeTranscriptExtractor()
        transcript = yt_extractor.get_transcript(url)

        if transcript:
            logger.info(f"Extracted native transcript ({len(transcript['all_words'])} words) in < 1 second!")
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(transcript, f, indent=2, ensure_ascii=False)
        else:
            logger.info("Native captions not found. Running faster-whisper Speech-to-Text...")
            t_config = config.get("transcription", {})
            transcriber = WhisperTranscriber(
                model_size=t_config.get("model_size", "base"),
                device=t_config.get("device", "auto"),
            )
            transcript = transcriber.transcribe(str(audio_path), cache_path=str(cache_path))
            logger.info(f"Transcribed {len(transcript['all_words'])} words across {len(transcript['segments'])} segments.")

    # 4. Acoustic & Hype Fusion Analysis
    logger.info("Step 4/5: Running Multi-Signal Hype Detection Engine...")
    energy_analyzer = AudioEnergyAnalyzer()
    audio_features = energy_analyzer.analyze_audio(str(audio_path))

    llm_scorer = LLMSemanticScorer()
    h_config = config.get("hype_detection", {})
    fusion_engine = HypeFusionEngine(
        weights=h_config.get("weights"),
        min_clip_duration=h_config.get("min_clip_duration", 30),
        max_clip_duration=h_config.get("max_clip_duration", 55),
        sliding_step=h_config.get("sliding_step", 5),
    )

    top_clips = fusion_engine.find_top_clips(
        transcript_data=transcript,
        audio_features=audio_features,
        heatmap=heatmap,
        llm_scorer=llm_scorer,
        top_k=top_k,
    )

    if not top_clips:
        logger.error("No suitable viral clips detected meeting duration criteria.")
        return

    print("\n" + "-" * 60)
    print(f"🔥 TOP {len(top_clips)} VIRAL MOMENTS DETECTED:")
    for idx, clip in enumerate(top_clips, 1):
        print(f"  [{idx}] Time: {clip['start']}s -> {clip['end']}s ({clip['duration']}s)")
        print(f"      Hype Score: {clip['final_hype_score']}")
        print(f"      Hook Title: {clip['viral_title']}")
        print(f"      Preview: \"{clip['text'][:70]}...\"\n")
    print("-" * 60 + "\n")

    # 5. Video Engine Processing & Rendering
    logger.info("Downloading video stream for rendering...")
    video_path = downloader.download_video(url, video_id=video_id)

    logger.info("Step 5/5: Rendering 9:16 Shorts with Face Tracking & Kinetic Subtitles...")
    tracker = FaceTracker()
    sub_gen = SubtitleGenerator()
    composer = VideoComposer()

    rendered_files = []
    for idx, clip in enumerate(top_clips, 1):
        clip_name = f"{video_id}_short_{idx}"
        ass_path = temp_dir / f"{clip_name}.ass"
        out_short = out_dir / f"{clip_name}.mp4"

        # Generate bouncing ASS subtitles
        sub_gen.generate_ass_file(
            words=clip["words"],
            clip_start=clip["start"],
            output_ass_path=str(ass_path),
        )

        # Detect active speaker crop window
        crop_box = tracker.calculate_crop_window(
            video_path=str(video_path),
            start_sec=clip["start"],
            end_sec=clip["end"],
        )

        # Compose and render final Short
        final_mp4 = composer.render_short(
            input_video_path=str(video_path),
            start_sec=clip["start"],
            end_sec=clip["end"],
            crop_box=crop_box,
            ass_subtitle_path=str(ass_path),
            output_path=str(out_short),
            hook_banner_text=clip["hook_banner_text"],
        )
        rendered_files.append(final_mp4)

    print("\n" + "=" * 60)
    print("✅ COMPLETED! GENERATED SHORTS:")
    for f in rendered_files:
        print(f"  👉 {f}")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Content Agent: Autonomous Viral Video Clipper")
    parser.add_argument("--url", type=str, required=True, help="YouTube video URL to process")
    parser.add_argument("--top-k", type=int, default=3, help="Number of viral clips to extract (default: 3)")
    parser.add_argument("--output-dir", type=str, default="./output", help="Directory to save final Shorts")

    args = parser.parse_args()
    process_video(url=args.url, top_k=args.top_k, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
