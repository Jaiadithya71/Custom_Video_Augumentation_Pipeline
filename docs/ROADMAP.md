# Project Roadmap & Implementation Milestones

## Phase 1: Environment Setup & Core Foundations
*Goal: Establish workspace, dependencies, configuration schemas, and ingestion pipeline.*

- [ ] **1.1 Dependency Specification:** Create `requirements.txt` with verified library versions (`yt-dlp`, `faster-whisper`, `librosa`, `opencv-python`, `mediapipe`, `ffmpeg-python`, `pyyaml`, `pydantic`).
- [ ] **1.2 Configuration Layer:** Create `config/settings.yaml` for customizable thresholds (minimum duration, hype weightings, output paths).
- [ ] **1.3 Ingestion Module (`src/ingestion/`):**
  - Implement `downloader.py` using `yt-dlp` to selectively extract audio (`.wav`) and 1080p video (`.mp4`).
  - Implement `heatmap.py` to extract and parse YouTube's "Most Replayed" curve.
- [ ] **1.4 Transcription Module (`src/transcription/`):**
  - Implement `transcriber.py` using `faster-whisper` with word-level timestamp extraction.
  - Export structured transcript JSON with sentence boundaries.

---

## Phase 2: The Multi-Signal Hype Detection Engine
*Goal: Build the algorithmic scorer that accurately finds the top 3-5 viral moments in a long-form video.*

- [ ] **2.1 Acoustic Analyzer (`src/hype_detector/audio_energy.py`):**
  - RMS energy windowing and Z-score standardization.
  - Fundamental frequency ($F_0$) pitch standard deviation via `librosa`.
  - Words Per Minute (WPM) acceleration calculator from Whisper timestamps.
- [ ] **2.2 Event Classifier (`src/hype_detector/event_detector.py`):**
  - Lightweight audio event classifier for laughter, applause, and gasps using YAMNet.
- [ ] **2.3 LLM Semantic Scorer (`src/hype_detector/llm_scorer.py`):**
  - Sliding window transcript chunking.
  - Structured prompt for curiosity gap, story arc completeness, and payoff.
  - JSON response parser with validation.
- [ ] **2.4 Fusion Scorer & NMS (`src/hype_detector/fusion.py`):**
  - Weighted composite scoring equation combining all signals.
  - Word-boundary alignment to snap start/end times to natural sentence pauses.
  - Non-Maximum Suppression (NMS) to eliminate overlapping clip candidates.

---

## Phase 3: Video Engine & Smart Reframing (9:16)
*Goal: Dynamically convert horizontal clips to vertical Shorts with centered speaker tracking.*

- [ ] **3.1 Face Tracking (`src/video_engine/tracker.py`):**
  - MediaPipe / YOLOv8 face detector on keyframes.
  - Exponential Moving Average (EMA) smoothing algorithm for fluid camera movement.
- [ ] **3.2 Layout Engine (`src/video_engine/layout.py`):**
  - Single speaker centering crop.
  - Split-screen stacked layout (top/bottom) when two continuous speakers are detected.
  - Blur-padded fallback if no faces are detected.

---

## Phase 4: Transformative Styling & Kinetic Captions
*Goal: Make the content visually engaging and comply with YouTube's Fair Use / Transformative policies.*

- [ ] **4.1 Subtitle Engine (`src/video_engine/subtitle_gen.py`):**
  - Generate `.ass` (Advanced SubStation Alpha) subtitle files.
  - Word-by-word karaoke highlighting (active word in bright color with scale bounce).
  - Configurable font sizing, drop shadow, and vertical positioning.
- [ ] **4.2 Transformative Composer (`src/video_engine/composer.py`):**
  - Dynamic top title/hook banner with contextual question.
  - Audio normalization (`loudnorm` filter in FFmpeg).
  - Background music ducking (auto-lowers music when speech is present).
  - FFmpeg hardware-accelerated rendering (`h264_nvenc` or standard `libx264`).

---

## Phase 5: Publishing & Orchestration CLI
*Goal: Provide a one-command CLI pipeline and automated YouTube distribution.*

- [ ] **5.1 Metadata Generator (`src/publisher/metadata_gen.py`):**
  - Generates viral titles, SEO description, and hashtags for each extracted clip.
- [ ] **5.2 YouTube Uploader (`src/publisher/yt_uploader.py`):**
  - YouTube Data API v3 OAuth integration.
  - Scheduled or unlisted upload capability.
- [ ] **5.3 Master CLI (`main.py`):**
  - CLI commands:
    ```bash
    python main.py process --url "https://youtube.com/watch?v=..." --num-clips 3
    ```
