"""Narrative Profiler: Deep channel analysis and video essence extraction before pipeline execution."""

import os
import re
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
import requests

logger = logging.getLogger(__name__)


@dataclass
class VideoNarrativeProfile:
    """Encapsulates the unique essence, narrative arc, and stylistic directives of a video and channel."""
    channel_name: str
    channel_niche: str
    video_format: str               # "interview_podcast", "solo_explainer", "documentary", "educational", etc.
    tone: str                       # "dramatic", "inspirational", "philosophical", "shocking", etc.
    target_audience: str
    core_thesis: str
    speakers: List[Dict[str, str]] = field(default_factory=list)  # e.g. [{"name": "Raj Shamani", "role": "host"}]
    key_narrative_arcs: List[str] = field(default_factory=list)
    editorial_badges: List[str] = field(default_factory=list)
    hook_recommendation: str = ""
    visual_crop_strategy: str = "dynamic_speaker"  # "dynamic_speaker", "center_focus", "cinematic_zoom"
    zoom_factor: float = 1.08        # Default 1.08x to eliminate original burned-in letterbox captions
    banner_duration_sec: float = 4.5 # Display hook headline for 4.5 seconds then fade

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class NarrativeProfiler:
    """
    Analyzes channel identity, video title, metadata, and transcript essence
    BEFORE pipeline execution to tailor clipping, storytelling, and visual styling.
    """

    PROFILER_SYSTEM_PROMPT = """You are an elite executive producer for top-tier short-form media (YouTube Shorts, TikTok, Instagram Reels).
Analyze the provided video metadata and transcript sample to produce a deep narrative profile.

Your goal is to extract:
1. CHANNEL ESSENCE: Who is the creator? What is the channel's signature style, tone, and audience expectations?
2. VIDEO ESSENCE: What is the core narrative of this specific video? Who is speaking (Host vs Guest)?
3. VIRAL ANCHORS: What 3 to 4 specific narrative arcs or emotional moments would make 10/10 viral Shorts?
4. EDITORIAL HOOKS: Create punchy, intriguing hook badges (max 6-8 words) suitable for top banner stickers.

Return strictly valid JSON with this exact schema:
{
  "channel_name": "Raj Shamani",
  "channel_niche": "Long-form candid podcast, high-profile interviews, wisdom & life lessons",
  "video_format": "interview_podcast",
  "tone": "dramatic & inspirational",
  "target_audience": "Curious learners, entrepreneurs, space & science enthusiasts, young strivers",
  "core_thesis": "NASA astronaut Sunita Williams reveals the extreme psychological and physical realities of 286 days in space.",
  "speakers": [
    {"name": "Raj Shamani", "role": "host"},
    {"name": "Sunita Williams", "role": "guest"}
  ],
  "key_narrative_arcs": [
    "Satellite explosion near ISS and emergency safe haven evacuation",
    "Emotional reaction to Kalpana Chawla and the Columbia disaster",
    "Extraterrestrial life in the universe",
    "Physical disorientation and nausea returning to Earth gravity"
  ],
  "editorial_badges": [
    "🚨 SATELLITE EXPLODED IN ORBIT",
    "💔 LOSING KALPANA CHAWLA",
    "👽 IS THERE ALIEN LIFE?",
    "🚀 THE TRUTH ABOUT SPACE SURVIVAL"
  ],
  "hook_recommendation": "Anchor clips on Raj's high-stakes questions or Sunita's direct first-hand crisis accounts.",
  "visual_crop_strategy": "dynamic_speaker",
  "zoom_factor": 1.08,
  "banner_duration_sec": 4.5
}"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model = model

    def analyze(
        self,
        metadata: Dict[str, Any],
        transcript_sample: Optional[str] = None
    ) -> VideoNarrativeProfile:
        """
        Runs comprehensive channel & video analysis.
        Uses Gemini LLM if API key is configured; otherwise uses intelligent heuristic profiling.
        """
        title = metadata.get("title", "")
        channel = metadata.get("channel") or metadata.get("uploader") or "Unknown Channel"
        description = metadata.get("description", "")

        logger.info(f"Profiling video narrative for channel '{channel}' and video '{title}'...")

        if self.api_key:
            try:
                return self._call_llm_profiler(title, channel, description, transcript_sample)
            except Exception as e:
                logger.warning(f"LLM narrative profiling failed ({e}). Falling back to heuristic profiler.")

        return self._heuristic_profiler(title, channel, description, transcript_sample)

    def _call_llm_profiler(
        self,
        title: str,
        channel: str,
        description: str,
        transcript_sample: Optional[str]
    ) -> VideoNarrativeProfile:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}

        prompt = (
            f"{self.PROFILER_SYSTEM_PROMPT}\n\n"
            f"CHANNEL: {channel}\n"
            f"TITLE: {title}\n"
            f"DESCRIPTION: {description[:800]}\n"
        )
        if transcript_sample:
            prompt += f"\nTRANSCRIPT SAMPLE:\n\"\"\"{transcript_sample[:2500]}\"\"\"\n"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text}")

        res_json = resp.json()
        raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(raw_text)

        return VideoNarrativeProfile(
            channel_name=data.get("channel_name", channel),
            channel_niche=data.get("channel_niche", "General Content"),
            video_format=data.get("video_format", "interview_podcast"),
            tone=data.get("tone", "conversational"),
            target_audience=data.get("target_audience", "General Audience"),
            core_thesis=data.get("core_thesis", title),
            speakers=data.get("speakers", []),
            key_narrative_arcs=data.get("key_narrative_arcs", []),
            editorial_badges=data.get("editorial_badges", []),
            hook_recommendation=data.get("hook_recommendation", ""),
            visual_crop_strategy=data.get("visual_crop_strategy", "dynamic_speaker"),
            zoom_factor=float(data.get("zoom_factor", 1.08)),
            banner_duration_sec=float(data.get("banner_duration_sec", 4.5)),
        )

    def _heuristic_profiler(
        self,
        title: str,
        channel: str,
        description: str,
        transcript_sample: Optional[str]
    ) -> VideoNarrativeProfile:
        """
        Sophisticated rule-based profiler that extracts host/guest, channel niche,
        and high-converting editorial hook badges without needing an external API.
        """
        title_lower = title.lower()
        channel_lower = channel.lower()
        combined_text = f"{title} {description}".lower()

        # 1. Format Detection
        is_interview = any(k in title_lower or k in description.lower() for k in [
            "podcast", "interview", "conversation", "| fo", "figuring out", "beerbiceps",
            "joe rogan", "lex fridman", "on 286 days", "talks about", "ft.", "feat."
        ])
        video_format = "interview_podcast" if is_interview else "solo_explainer"

        # 2. Speaker Extraction
        speakers = []
        host_name = channel
        guest_name = "Featured Guest"

        # Special casing for known podcast channels
        if "raj shamani" in channel_lower or "figuring out" in title_lower:
            host_name = "Raj Shamani"
            # Parse guest name from title: e.g. "Sunita Williams On 286 Days in Space | FO461 Raj Shamani"
            m = re.match(r"^([^|:-]+?)(?:\s+(?:on|talks|about|reveals|shares|interview)|\||$)", title, re.IGNORECASE)
            if m:
                guest_name = m.group(1).strip()
            speakers = [
                {"name": host_name, "role": "host"},
                {"name": guest_name, "role": "guest"},
            ]
        elif "beerbiceps" in channel_lower or "ranveer" in channel_lower:
            host_name = "Ranveer Allahbadia"
            speakers = [{"name": host_name, "role": "host"}]
        else:
            speakers = [{"name": channel, "role": "creator"}]

        # 3. Tone & Niche Detection
        niche = "Conversational Podcast & Long-Form Wisdom" if is_interview else "Digital Media & Video"
        tone = "dramatic & insightful"

        if any(w in combined_text for w in ["space", "nasa", "astronaut", "satellite", "columbia"]):
            tone = "intense survival & high-stakes inspiration"
            niche = "Space, Science & Extreme Human Endeavors"
        elif any(w in combined_text for w in ["money", "business", "startup", "crore", "dollar", "wealth"]):
            tone = "ambitious & analytical"
            niche = "Business, Finance & Entrepreneurship"

        # 4. Generate Channel-Tailored Editorial Hook Badges
        editorial_badges = []
        if "sunita williams" in combined_text or "space" in combined_text:
            editorial_badges = [
                "SATELLITE EXPLOSION IN SPACE",
                "THE TRAGEDY OF COLUMBIA",
                "HOW INDIA LOOKS FROM SPACE",
                "IS THERE LIFE IN THE UNIVERSE?",
                "STUCK IN SPACE: 9 MONTHS",
            ]
        elif is_interview:
            editorial_badges = [
                "THE BRUTAL TRUTH NOBODY TELLS YOU",
                "BIGGEST MISTAKE YOU CAN MAKE",
                "A LESSON THAT CHANGED EVERYTHING",
                "THE MOMENT EVERYTHING SHIFTED",
            ]
        else:
            editorial_badges = [
                "MUST WATCH INSIGHT",
                "WATCH BEFORE IT'S TOO LATE",
                "THE HIDDEN TRUTH",
            ]

        key_arcs = [
            f"High-stakes conversation with {guest_name}",
            "Key turning point or crisis moment",
            "Philosophical resolution and future outlook",
        ]

        return VideoNarrativeProfile(
            channel_name=channel,
            channel_niche=niche,
            video_format=video_format,
            tone=tone,
            target_audience="Curious, ambitious viewers seeking authentic, high-value stories",
            core_thesis=f"{channel}: {title}",
            speakers=speakers,
            key_narrative_arcs=key_arcs,
            editorial_badges=editorial_badges,
            hook_recommendation=f"Prioritize moments where {host_name} asks an intense question and {guest_name} delivers a dramatic first-person experience.",
            visual_crop_strategy="dynamic_speaker" if is_interview else "center_focus",
            zoom_factor=1.08,
            banner_duration_sec=4.5,
        )
