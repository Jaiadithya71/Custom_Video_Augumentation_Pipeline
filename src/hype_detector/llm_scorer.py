"""LLM Semantic Scorer: Evaluates curiosity gap, story arc completeness, and viral hooks."""

import os
import json
import logging
import re
from typing import Dict, List, Any, Optional
import requests

logger = logging.getLogger(__name__)


class LLMSemanticScorer:
    """
    Evaluates transcript chunks for short-form virality (hooks, story arc, standalone clarity).
    Supports Gemini API, local Ollama (OpenAI-compatible), and heuristic fallback.
    """

    SYSTEM_PROMPT = """You are an elite short-form content producer (TikTok / YouTube Shorts).
Your job is to evaluate a segment of a conversation transcript and determine if it can become a viral Short.

Criteria:
1. HOOK STRENGTH (0-10): Does the first 3-5 seconds grab intense curiosity, make a bold claim, or ask a burning question?
2. STANDALONE CLARITY (0-10): Can someone watching with zero prior context understand what is being talked about?
3. NARRATIVE PAYOFF (0-10): Is there a satisfying climax, punchline, solution, or mind-blowing insight?
4. RETENTION RISK (0-10): Are there boring tangents, awkward stutters, or incomplete cutoff sentences?

Respond ONLY with valid JSON in this format:
{
  "hook_score": 8.5,
  "clarity_score": 9.0,
  "payoff_score": 8.0,
  "retention_risk": 1.5,
  "viral_title": "Why 99% Of People Fail At This",
  "hook_banner_text": "The Brutal Truth Nobody Tells You",
  "summary": "Short explanation of why this moment is engaging."
}"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model = model

    def score_segment(
        self,
        segment_text: str,
        duration_sec: float,
        narrative_profile: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Scores a candidate segment using LLM or narrative-guided heuristic fallback."""
        if not self.api_key:
            return self._heuristic_fallback(segment_text, duration_sec, narrative_profile)

        try:
            return self._call_gemini_api(segment_text, narrative_profile)
        except Exception as e:
            logger.warning(f"LLM API call failed ({e}). Using narrative-guided heuristic fallback.")
            return self._heuristic_fallback(segment_text, duration_sec, narrative_profile)

    def _call_gemini_api(
        self,
        text: str,
        narrative_profile: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Calls Google Gemini API for fast structured evaluation."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        
        context_str = ""
        if narrative_profile:
            context_str = (
                f"\nCHANNEL CONTEXT: {narrative_profile.channel_name} ({narrative_profile.channel_niche})\n"
                f"VIDEO FORMAT: {narrative_profile.video_format} | TONE: {narrative_profile.tone}\n"
                f"CORE THESIS: {narrative_profile.core_thesis}\n"
            )

        prompt = f"{self.SYSTEM_PROMPT}{context_str}\n\nTRANSCRIPT SEGMENT:\n\"\"\"{text}\"\"\""
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text}")

        res_json = resp.json()
        raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(raw_text)

        # Calculate composite semantic score [0.0 - 1.0]
        hook = float(data.get("hook_score", 5.0))
        clarity = float(data.get("clarity_score", 5.0))
        payoff = float(data.get("payoff_score", 5.0))
        risk = float(data.get("retention_risk", 3.0))

        composite_score = (
            (hook * 0.40) + (payoff * 0.35) + (clarity * 0.25) - (risk * 0.20)
        ) / 10.0
        data["semantic_score"] = float(min(max(composite_score, 0.0), 1.0))
        return data

    def _heuristic_fallback(
        self,
        text: str,
        duration_sec: float,
        narrative_profile: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Narrative-aware rule-based scoring when no API key is provided.
        Matches segments to channel essence, narrative arcs, and editorial badges.
        """
        # Sanitize text
        clean_text = re.sub(r"^[>\-\s]+", "", text).strip()
        clean_text = re.sub(r"\[.*?\]", "", clean_text).strip()
        lower = clean_text.lower()
        
        # High-curiosity trigger words
        curiosity_triggers = [
            "the truth", "secret", "never", "always", "mistake", "crazy", 
            "insane", "how to", "why do", "the biggest", "nobody tells you",
            "warning", "money", "failed", "shocking", "million", "billion",
            "scared", "fear", "death", "exploded", "disaster", "survived"
        ]
        hook_hits = sum(1 for word in curiosity_triggers if word in lower[:120])
        hook_score = min(4.0 + (hook_hits * 1.8), 10.0)

        # Questions in opening create very strong hooks
        if "?" in clean_text[:120]:
            hook_score = min(hook_score + 2.0, 10.0)

        # Penalize clips starting with dangling conjunctions or prepositions
        first_word = clean_text.split()[0].lower() if clean_text.split() else ""
        if first_word in {"for", "and", "because", "so", "cuz", "but", "or", "um", "uh", "when"}:
            hook_score = max(1.5, hook_score - 2.5)

        # Clean sentence ending creates high payoff/completeness
        has_clean_end = bool(re.search(r"[.!?]['\"]?\s*$", clean_text.strip()))
        payoff_score = 8.5 if has_clean_end else 4.0

        clarity_score = 7.5
        retention_risk = 1.5 if has_clean_end else 4.5

        # Check narrative alignment with channel profile
        editorial_badge = "MUST WATCH INSIGHT"
        if narrative_profile and getattr(narrative_profile, "editorial_badges", None):
            badges = narrative_profile.editorial_badges
            editorial_badge = badges[0]
            # Context-match badge
            if any(k in lower for k in ["india", "himalayas", "daytime", "rivers", "lights"]):
                for b in badges:
                    if "INDIA" in b:
                        editorial_badge = b
                        hook_score = min(hook_score + 1.8, 10.0)
                        break
            elif any(k in lower for k in ["debris", "satellite", "orbit", "safe haven", "explode"]):
                for b in badges:
                    if "SATELLITE" in b or "EXPLOSION" in b:
                        editorial_badge = b
                        hook_score = min(hook_score + 1.5, 10.0)
                        break
            elif any(k in lower for k in ["kalpn", "chawla", "columbia", "death", "tragedy", "survivor"]):
                for b in badges:
                    if "COLUMBIA" in b or "KALPANA" in b or "TRAGEDY" in b:
                        editorial_badge = b
                        hook_score = min(hook_score + 1.5, 10.0)
                        break
            elif any(k in lower for k in ["stuck", "starliner", "boeing", "flight"]):
                for b in badges:
                    if "STUCK" in b:
                        editorial_badge = b
                        hook_score = min(hook_score + 1.5, 10.0)
                        break
            elif any(k in lower for k in ["alien", "life", "stars", "universe", "believe"]):
                for b in badges:
                    if "LIFE" in b or "UNIVERSE" in b or "ALIEN" in b:
                        editorial_badge = b
                        hook_score = min(hook_score + 1.5, 10.0)
                        break
            elif any(k in lower for k in ["nauseous", "nausea", "gravity", "earth", "neuro"]):
                for b in badges:
                    if "ORBIT" in b or "SURVIVAL" in b:
                        editorial_badge = b
                        hook_score = min(hook_score + 1.0, 10.0)
                        break

        composite = ((hook_score * 0.4) + (payoff_score * 0.35) + (clarity_score * 0.25) - (retention_risk * 0.2)) / 10.0
        semantic_score = float(min(max(composite, 0.0), 1.0))

        # Editorial Title Generation
        first_sentence = re.split(r"[.!?]", clean_text)[0].strip()
        first_sentence = re.sub(r"^[>\-\s]+", "", first_sentence).strip()
        viral_title = editorial_badge.title() if editorial_badge else (first_sentence[:45] or "Must Watch Insight")

        return {
            "hook_score": hook_score,
            "clarity_score": clarity_score,
            "payoff_score": payoff_score,
            "retention_risk": retention_risk,
            "semantic_score": semantic_score,
            "viral_title": viral_title,
            "hook_banner_text": editorial_badge,
            "summary": f"Narrative-aligned segment for {getattr(narrative_profile, 'channel_name', 'channel')}: {editorial_badge}",
        }
