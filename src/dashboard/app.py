"""Local Web Dashboard for Content Agent.
Provides real-time pipeline monitoring and an interactive media inspector for finished shorts & intermediates.
"""

import os
import sys
import json
import uuid
import time
import logging
import threading
from pathlib import Path
from typing import Dict, Any, List

from flask import Flask, render_template, request, jsonify, send_file, send_from_directory

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import src
from src.ingestion.downloader import YouTubeDownloader
from src.ingestion.heatmap import YouTubeHeatmapExtractor
from src.ingestion.finder import ViralVideoFinder
from src.transcription.youtube_transcript import YouTubeTranscriptExtractor
from src.transcription.transcriber import WhisperTranscriber
from src.hype_detector.audio_energy import AudioEnergyAnalyzer
from src.hype_detector.llm_scorer import LLMSemanticScorer
from src.hype_detector.fusion import HypeFusionEngine
from src.video_engine.tracker import FaceTracker
from src.video_engine.subtitle_gen import SubtitleGenerator
from src.video_engine.composer import VideoComposer
from src.publisher.metadata_gen import ShortsMetadataGenerator
from src.publisher.yt_uploader import YouTubeUploader, YouTubeAuthError

app = Flask(__name__, template_folder="templates")
app.config["TEMPLATES_AUTO_RELOAD"] = True
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Dashboard")

JOBS_FILE = PROJECT_ROOT / "temp" / "jobs.json"
JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)

# In-memory jobs cache (RLock allows re-entrant calls from save_jobs)
JOBS: Dict[str, Dict[str, Any]] = {}
JOBS_LOCK = threading.RLock()
JOB_PERMISSIONS: Dict[str, Dict[str, Any]] = {}


def load_saved_jobs():
    global JOBS
    if JOBS_FILE.exists():
        try:
            with open(JOBS_FILE, "r", encoding="utf-8") as f:
                JOBS = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load saved jobs: {e}")
            JOBS = {}


def save_jobs():
    try:
        with JOBS_LOCK:
            with open(JOBS_FILE, "w", encoding="utf-8") as f:
                json.dump(JOBS, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Could not persist jobs: {e}")


load_saved_jobs()


def run_pipeline_job(job_id: str, url: str, top_k: int):
    """Executes the pipeline in a background worker thread with progress tracking."""
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return

    def log(msg: str, status: str = None):
        with JOBS_LOCK:
            if status:
                job["status"] = status
            timestamp = time.strftime("%H:%M:%S")
            entry = f"[{timestamp}] {msg}"
            job["logs"].append(entry)
            logger.info(f"Job {job_id}: {entry}")
            save_jobs()

    try:
        temp_dir = PROJECT_ROOT / "temp"
        out_dir = PROJECT_ROOT / "output"
        temp_dir.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)

        # 1. Ingestion
        log(f"Fetching video metadata for: {url}", "downloading")
        downloader = YouTubeDownloader(temp_dir=str(temp_dir))
        info = downloader.get_video_info(url)
        video_id = info["id"]
        job["video_info"] = info
        log(f"Found: '{info['title']}' ({info['duration']}s) by {info['channel']}")

        # 1.5 Channel & Video Narrative Profiling (Pre-Pipeline Analysis)
        log(f"Profiling channel '{info.get('channel')}' essence & video narrative arc...", "profiling")
        from src.intelligence.narrative_profiler import NarrativeProfiler
        narrative_profiler = NarrativeProfiler()
        narrative_profile = narrative_profiler.analyze(info)
        job["narrative_profile"] = narrative_profile.to_dict()
        log(f"Channel: {narrative_profile.channel_name} | Format: {narrative_profile.video_format} | Tone: {narrative_profile.tone}")
        if narrative_profile.editorial_badges:
            log(f"Editorial Badges: {' | '.join(narrative_profile.editorial_badges[:3])}")

        log("Downloading audio stream (16kHz mono)...")
        audio_path = downloader.download_audio(url, video_id=video_id)
        job["intermediates"]["audio_file"] = str(audio_path.relative_to(PROJECT_ROOT)).replace("\\", "/")

        # 2. Crowd Heatmap
        log("Extracting YouTube Engagement Heatmap...", "analyzing")
        heatmap_extractor = YouTubeHeatmapExtractor()
        heatmap = heatmap_extractor.extract_heatmap(url)
        job["intermediates"]["heatmap_points"] = len(heatmap)
        job["intermediates"]["heatmap"] = heatmap[:50]  # Store sample points

        # 3. Transcription (Fast Native Extractor first, fallback to Whisper)
        cache_path = temp_dir / f"{video_id}_transcript.json"
        transcript = None

        if cache_path.exists():
            log("Loading cached transcript from disk...", "transcribing")
            with open(cache_path, "r", encoding="utf-8") as f:
                transcript = json.load(f)
        else:
            log("Extracting native YouTube word-level transcript (instant)...", "transcribing")
            yt_extractor = YouTubeTranscriptExtractor()
            transcript = yt_extractor.get_transcript(url)

            if transcript:
                log(f"Extracted {len(transcript['all_words'])} words in 0.5s from YouTube captions.")
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(transcript, f, indent=2, ensure_ascii=False)
            else:
                # No native captions: Ask permission before running heavy local Whisper
                dur = info.get("duration", 0)
                dur_str = f"{dur // 60} mins" if dur else "unknown duration"
                job["permission_required"] = {
                    "type": "whisper_transcription",
                    "duration_str": dur_str,
                    "message": f"This video has no native YouTube captions. Running local Whisper on the initial 5-minute hook zone will take ~30 seconds.",
                }
                log(f"⚠️ No native captions. Awaiting user permission to run local Whisper on initial 5-min hook zone...", "awaiting_permission")

                event = threading.Event()
                JOB_PERMISSIONS[job_id] = {"event": event, "decision": None}

                # Wait for user response (up to 10 minutes)
                event.wait(timeout=600)
                decision = JOB_PERMISSIONS.get(job_id, {}).get("decision")

                if decision != "allow":
                    log("Job cancelled: User opted out of local Whisper transcription.", "cancelled")
                    job["permission_required"] = None
                    save_jobs()
                    return

                job["permission_required"] = None
                log("User approved Whisper transcription. Running faster-whisper speech-to-text...", "transcribing")
                transcriber = WhisperTranscriber(model_size="base")
                transcript = transcriber.transcribe(str(audio_path), cache_path=str(cache_path))

        job["intermediates"]["transcript_file"] = str(cache_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        job["intermediates"]["total_words"] = len(transcript["all_words"])

        # 4. Hype Analysis
        log("Analyzing acoustic features (RMS energy, pitch variance)...", "analyzing")
        energy_analyzer = AudioEnergyAnalyzer()
        audio_features = energy_analyzer.analyze_audio(str(audio_path))

        log("Discovering viral story hooks with Hook Discovery Engine...")
        llm_scorer = LLMSemanticScorer()
        fusion_engine = HypeFusionEngine(min_clip_duration=16.0, max_clip_duration=45.0, sliding_step=4.0)
        top_clips = fusion_engine.find_top_clips(
            transcript_data=transcript,
            audio_features=audio_features,
            heatmap=heatmap,
            llm_scorer=llm_scorer,
            top_k=top_k,
            narrative_profile=narrative_profile,
        )

        if not top_clips:
            log("No clips found meeting viral criteria.", "failed")
            return

        job["candidates"] = top_clips
        log(f"Selected {len(top_clips)} high-hype moments!")

        # 5. Video Engine Rendering
        log("Downloading 1080p video stream (initial 5-min hook zone)...", "rendering")
        video_path = downloader.download_video(url, video_id=video_id)
        job["intermediates"]["video_file"] = str(video_path.relative_to(PROJECT_ROOT)).replace("\\", "/")

        tracker = FaceTracker()
        sub_gen = SubtitleGenerator()
        composer = VideoComposer()

        for idx, clip in enumerate(top_clips, 1):
            clip_name = f"{video_id}_short_{idx}"
            ass_path = temp_dir / f"{clip_name}.ass"
            out_short = out_dir / f"{clip_name}.mp4"

            log(f"Rendering Short [{idx}/{len(top_clips)}]: {clip['viral_title']} ({clip['start']}s -> {clip['end']}s)")

            # OpenShorts Face Tracking & Layout Detection
            layout_plan = tracker.calculate_layout_plan(
                video_path=str(video_path),
                start_sec=clip["start"],
                end_sec=clip["end"],
            )

            if layout_plan.layout_type == "split_screen_stack":
                log(f"Detected 2 distinct speakers in dialogue -> OpenShorts Dual-Cam Split-Screen Stack layout enabled")
            else:
                log(f"Framing dominant speaker at x={layout_plan.crop_x} (9:16 full-bleed)")

            # Generate kinetic karaoke subtitles with pop scaling & emojis
            sub_margin = 320 if layout_plan.layout_type == "split_screen_stack" else 380
            sub_gen.generate_ass_file(
                words=clip["words"],
                clip_start=clip["start"],
                output_ass_path=str(ass_path),
                margin_bottom=sub_margin,
            )

            # FFmpeg studio-grade render with layout plan
            composer.render_short(
                input_video_path=str(video_path),
                start_sec=clip["start"],
                end_sec=clip["end"],
                crop_box=(layout_plan.crop_x, layout_plan.crop_y, layout_plan.crop_w, layout_plan.crop_h),
                layout_plan=layout_plan,
                ass_subtitle_path=str(ass_path),
                output_path=str(out_short),
                hook_banner_text=clip["hook_banner_text"],
                zoom_factor=getattr(narrative_profile, "zoom_factor", 1.08),
                banner_duration=getattr(narrative_profile, "banner_duration_sec", 4.5),
            )

            rel_short_path = str(out_short.relative_to(PROJECT_ROOT)).replace("\\", "/")
            rel_ass_path = str(ass_path.relative_to(PROJECT_ROOT)).replace("\\", "/")

            with JOBS_LOCK:
                JOBS[job_id]["finished_shorts"].append({
                    "id": clip_name,
                    "video_path": rel_short_path,
                    "ass_path": rel_ass_path,
                    "title": clip["viral_title"],
                    "banner_text": clip["hook_banner_text"],
                    "layout_type": layout_plan.layout_type,
                    "score": clip["final_hype_score"],
                    "start": clip["start"],
                    "end": clip["end"],
                    "duration": clip["duration"],
                    "text": clip["text"],
                })
                save_jobs()

        log("Pipeline completed successfully!", "completed")

    except Exception as e:
        logger.exception(f"Job failed: {e}")
        log(f"Error: {str(e)}", "failed")


@app.after_request
def add_header(response):
    if "text/html" in response.headers.get("Content-Type", ""):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    with JOBS_LOCK:
        job_list = list(JOBS.values())
        job_list.sort(key=lambda j: j.get("created_at", 0), reverse=True)
        return jsonify(job_list)


@app.route("/api/jobs", methods=["POST"])
def create_job():
    data = request.json or {}
    url = data.get("url", "").strip()
    top_k = int(data.get("top_k", 3))

    if not url:
        return jsonify({"error": "YouTube URL is required"}), 400

    job_id = str(uuid.uuid4())[:8]
    job_data = {
        "id": job_id,
        "url": url,
        "top_k": top_k,
        "status": "queued",
        "created_at": time.time(),
        "video_info": {},
        "logs": [],
        "intermediates": {},
        "candidates": [],
        "finished_shorts": [],
    }

    with JOBS_LOCK:
        JOBS[job_id] = job_data
        save_jobs()

    # Launch background processing thread
    thread = threading.Thread(target=run_pipeline_job, args=(job_id, url, top_k), daemon=True)
    thread.start()

    return jsonify({"success": True, "job_id": job_id})


@app.route("/api/jobs/<job_id>", methods=["GET"])
def get_job_detail(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        return jsonify(job)


@app.route("/api/jobs/<job_id>", methods=["DELETE"])
def delete_job(job_id: str):
    with JOBS_LOCK:
        if job_id in JOBS:
            del JOBS[job_id]
            save_jobs()
            return jsonify({"success": True, "deleted": job_id})
        return jsonify({"error": "Job not found"}), 404


@app.route("/media/<path:filename>")
def serve_media(filename: str):
    """Safely serves media files with byte-range support for video seeking."""
    file_path = PROJECT_ROOT / filename
    if not file_path.exists():
        return "File not found", 404
    return send_file(str(file_path), conditional=True)


@app.route("/api/discover", methods=["GET"])
def discover_popular():
    """Returns trending/viral long-form videos in a niche or search query."""
    niche = request.args.get("niche", "podcasts")
    limit = int(request.args.get("limit", 8))
    finder = ViralVideoFinder()
    videos = finder.find_viral_videos(query_or_niche=niche, limit=limit)
    return jsonify(videos)


@app.route("/api/jobs/<job_id>/permission", methods=["POST"])
def respond_permission(job_id: str):
    """Handles user approval or cancellation when Whisper transcription is needed."""
    data = request.json or {}
    action = data.get("action", "cancel")  # "allow" or "cancel"
    if job_id in JOB_PERMISSIONS:
        JOB_PERMISSIONS[job_id]["decision"] = action
        JOB_PERMISSIONS[job_id]["event"].set()
        return jsonify({"success": True, "action": action})
@app.route("/api/shorts/<job_id>/<short_id>/metadata", methods=["GET"])
def get_short_metadata(job_id: str, short_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404

        target_short = None
        for s in job.get("finished_shorts", []):
            if s.get("id") == short_id:
                target_short = s
                break

        if not target_short:
            return jsonify({"error": "Short not found"}), 404

        generator = ShortsMetadataGenerator()
        metadata = generator.generate_metadata(
            short_info=target_short,
            video_info=job.get("video_info"),
            narrative_profile=job.get("narrative_profile")
        )
        return jsonify(metadata)


@app.route("/api/publish", methods=["POST"])
def publish_short():
    data = request.json or {}
    job_id = data.get("job_id")
    short_id = data.get("short_id")
    title = data.get("title")
    description = data.get("description", "")
    tags = data.get("tags", [])
    privacy_status = data.get("privacy_status", "unlisted")

    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404

        target_short = None
        for s in job.get("finished_shorts", []):
            if s.get("id") == short_id:
                target_short = s
                break

        if not target_short:
            return jsonify({"error": "Short not found"}), 404

    video_path = PROJECT_ROOT / target_short["video_path"]
    if not video_path.exists():
        return jsonify({"error": f"Video file not found at {video_path}"}), 404

    try:
        uploader = YouTubeUploader()
        result = uploader.upload_video(
            video_path=str(video_path),
            title=title or target_short.get("title", "Short"),
            description=description,
            tags=tags,
            privacy_status=privacy_status,
        )
        with JOBS_LOCK:
            target_short["published"] = {
                "platform": "youtube",
                "video_id": result["video_id"],
                "url": result["url"],
                "status": privacy_status,
            }
            save_jobs()
        return jsonify({"success": True, "result": result})

    except YouTubeAuthError as e:
        return jsonify({
            "success": False,
            "auth_required": True,
            "error": str(e),
            "help_url": "https://console.cloud.google.com/apis/credentials"
        }), 401
    except Exception as e:
        logger.exception(f"Upload failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)

