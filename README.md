# Content Agent: Autonomous Viral Video Clipper & Repurposing Pipeline

An open-source, fully self-hosted engine designed to find high-performing long-form YouTube videos, extract high-hype viral moments using multi-modal AI analysis, apply transformative editing (9:16 re-framing, kinetic captions, B-roll), and publish YouTube Shorts without expensive third-party SaaS subscriptions.

---

## 📁 Project Architecture & Documentation

All technical specifications, algorithmic designs, and roadmaps are organized under [`docs/`](docs/):

*   [**Architecture Overview (`docs/ARCHITECTURE.md`)**](docs/ARCHITECTURE.md): End-to-end system design, data flow, component breakdown, and open-source toolchain.
*   [**Hype Detection Engine (`docs/HYPE_DETECTION_ENGINE.md`)**](docs/HYPE_DETECTION_ENGINE.md): Deep-dive into the multi-signal algorithm for identifying viral moments (crowd heatmaps, acoustic dynamics, semantic hooks, facial emotion, and optical flow).
*   [**Implementation Roadmap (`docs/ROADMAP.md`)**](docs/ROADMAP.md): Step-by-step phased development plan, milestones, and testing strategies.

---

## 🛠 Tech Stack (100% Free & Open-Source)

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Ingestion** | `yt-dlp` | Video/audio extraction & stream filtering |
| **Transcription** | `faster-whisper` | Fast GPU/CPU speech-to-text with word-level timestamps |
| **Audio Intelligence** | `librosa`, `scipy`, `YAMNet` | RMS energy, pitch inflection, laughter/gasp detection |
| **Video Intelligence** | `mediapipe`, `ultralytics (YOLOv8)`, `OpenCV` | Active speaker tracking, facial expression, motion flow |
| **Semantic Intelligence** | LLM APIs (Gemini / Claude / local Llama 3) | Hook scoring, narrative arc verification, metadata generation |
| **Video Engine** | `ffmpeg` + `.ass` subtitle engine | 9:16 smart cropping, kinetic karaoke subtitles, audio normalization |
| **Publishing** | `google-api-python-client` | YouTube Data API v3 OAuth & auto-upload |

---

## 🚀 Quick Setup & Status

Project is currently in **Phase 1: Architecture & Foundation**. See [docs/ROADMAP.md](docs/ROADMAP.md) for current sprint items.
