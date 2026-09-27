"""
Hook Discovery Engine: Discovers high-retention viral moments by analyzing
the high-voltage hook zone of videos where peak soundbites and visual hooks concentrate.
"""

import logging
from typing import Dict, List, Any, Tuple, Optional
from src.ingestion.heatmap import YouTubeHeatmapExtractor
from src.hype_detector.audio_energy import AudioEnergyAnalyzer
from src.hype_detector.llm_scorer import LLMSemanticScorer

logger = logging.getLogger(__name__)


class HookDiscoveryEngine:
    """
    Identifies and extracts the most compelling, self-contained story hooks
    from the high-impact teaser zone of videos.
    """

    TRANSITION_MARKERS = [
        "before starting today",
        "before we get started",
        "before we start",
        "before starting this",
        "welcome to",
        "welcome back to",
        "in today's episode",
        "today's episode",
        "today's guest",
        "my guest today",
        "our guest today",
        "without further ado",
        "join me in welcoming",
        "let's dive into",
        "brought to you by",
        "sponsored by",
        "sponsor of today",
        "welcome back everyone",
        "welcome everyone",
    ]

    QUESTION_WORDS = {
        "how", "what", "why", "was", "did", "do", "have", "before",
        "tell", "is", "can", "are", "could", "would", "where", "who", "when"
    }

    BAD_STARTERS = {
        "for", "and", "cuz", "because", "so", "but", "or", "um",
        "uh", "like", "that", "this", "then", "which", "well", "a", "an", "the"
    }

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        min_clip_duration: float = 16.0,
        max_clip_duration: float = 45.0,
    ):
        self.weights = weights or {
            "crowd_heatmap": 0.20,
            "semantic_hook": 0.40,
            "acoustic_rms": 0.20,
            "pitch_variance": 0.10,
            "wpm_velocity": 0.10,
        }
        self.min_clip_duration = min_clip_duration
        self.max_clip_duration = max_clip_duration

    def detect_hook_boundary(
        self,
        segments: List[Dict[str, Any]],
        words: List[Dict[str, Any]],
        total_duration: float,
    ) -> float:
        """
        Detects where the high-energy teaser / hook sequence concludes
        and the regular conversation begins.
        """
        # Look for verbal transition cues between 35s and 270s
        for seg in segments:
            if 35.0 <= seg.get("start", 0.0) <= 270.0:
                txt = seg.get("text", "").lower()
                for marker in self.TRANSITION_MARKERS:
                    if marker in txt:
                        logger.info(
                            f"Detected episode start transition '{marker}' at {seg['start']:.2f}s"
                        )
                        return float(seg["start"])

        # Fallback for long videos (> 10 mins): hook zone is the first ~3.5 minutes
        if total_duration > 600.0:
            return min(210.0, total_duration)

        return total_duration

    def extract_candidate_hooks(
        self,
        words: List[Dict[str, Any]],
        boundary: float,
    ) -> List[Dict[str, Any]]:
        """
        Extracts self-contained dialogue hook clusters within the hook boundary.
        """
        hook_words = [w for w in words if w["end"] <= boundary + 0.5]
        if not hook_words:
            return []

        # Find entry points (speaker questions or major topic openers)
        entry_indices = []
        for i, w in enumerate(hook_words):
            raw = w["word"].strip()
            clean = raw.replace(">>", "").strip().lower()

            is_start = (i == 0)
            is_turn = raw.startswith(">>")
            is_question = clean in self.QUESTION_WORDS

            if is_start or (is_turn and is_question) or (is_turn and i > 5):
                entry_indices.append(i)

        if not entry_indices:
            entry_indices = [0]

        candidates = []
        for start_idx in entry_indices:
            c_words = hook_words[start_idx:]
            if not c_words:
                continue

            # Try different natural target durations
            for target_dur in [18.0, 24.0, 32.0, 42.0]:
                sub = [w for w in c_words if (w["end"] - c_words[0]["start"]) <= target_dur + 4.0]
                if not sub:
                    continue

                dur = sub[-1]["end"] - sub[0]["start"]
                if dur < self.min_clip_duration:
                    continue

                # Snap start to clean starter word
                cleaned_sub = list(sub)
                while len(cleaned_sub) > 6:
                    first_tok = cleaned_sub[0]["word"].lower().strip(".,?!\"'>-")
                    if first_tok in self.BAD_STARTERS:
                        cleaned_sub = cleaned_sub[1:]
                    else:
                        break

                # Snap end to sentence end punctuation (. ! ?)
                if len(cleaned_sub) > 6:
                    for back in range(len(cleaned_sub) - 1, max(0, len(cleaned_sub) - 10), -1):
                        rw = cleaned_sub[back]["word"].strip()
                        if any(rw.endswith(p) for p in [".", "!", "?"]):
                            cleaned_sub = cleaned_sub[: back + 1]
                            break

                final_dur = cleaned_sub[-1]["end"] - cleaned_sub[0]["start"]
                if final_dur < self.min_clip_duration or final_dur > self.max_clip_duration:
                    continue

                cand_text = " ".join(w["word"] for w in cleaned_sub)
                candidates.append({
                    "start": round(cleaned_sub[0]["start"], 2),
                    "end": round(cleaned_sub[-1]["end"], 2),
                    "duration": round(final_dur, 2),
                    "words": cleaned_sub,
                    "text": cand_text,
                })

        return candidates

    def discover_top_hooks(
        self,
        transcript_data: Dict[str, Any],
        audio_features: Dict[str, Any],
        heatmap: List[Tuple[float, float]],
        llm_scorer: LLMSemanticScorer,
        top_k: int = 3,
        narrative_profile: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Discovers and ranks the top viral story moments.
        """
        total_duration = audio_features.get("duration", 0.0)
        all_words = transcript_data.get("all_words", [])
        segments = transcript_data.get("segments", [])

        if not all_words:
            return []

        # 1. Detect hook boundary
        boundary = self.detect_hook_boundary(segments, all_words, total_duration)
        logger.info(f"Targeting viral hook zone: 0.0s -> {boundary:.2f}s")

        # 2. Extract candidate hooks
        candidates = self.extract_candidate_hooks(all_words, boundary)

        # Fallback if no candidate met duration criteria in the boundary
        if len(candidates) < top_k and total_duration > boundary:
            logger.info("Insufficient candidates in primary hook zone; expanding candidate search.")
            from src.hype_detector.fusion import HypeFusionEngine
            fallback_engine = HypeFusionEngine(min_clip_duration=self.min_clip_duration)
            return fallback_engine.find_top_clips(
                transcript_data=transcript_data,
                audio_features=audio_features,
                heatmap=heatmap,
                llm_scorer=llm_scorer,
                top_k=top_k,
                narrative_profile=narrative_profile,
                use_hook_discovery=False,
            )

        if not candidates:
            return []

        # 3. Score candidate hooks
        energy_analyzer = AudioEnergyAnalyzer()
        active_weights = dict(self.weights)
        if not heatmap:
            active_weights["crowd_heatmap"] = 0.0
            active_weights["semantic_hook"] = 0.50
            active_weights["acoustic_rms"] = 0.25
            active_weights["pitch_variance"] = 0.15
            active_weights["wpm_velocity"] = 0.10

        scored = []
        for cand in candidates:
            if heatmap:
                heat_vals = [
                    YouTubeHeatmapExtractor.get_heat_at_time(heatmap, t)
                    for t in [cand["start"], (cand["start"] + cand["end"]) / 2.0, cand["end"]]
                ]
                heat_score = float(sum(heat_vals) / len(heat_vals))
            else:
                heat_score = 0.0

            acoustic = energy_analyzer.score_window(
                audio_features, cand["start"], cand["end"], cand["words"]
            )

            pre_score = (
                (active_weights["crowd_heatmap"] * heat_score)
                + (active_weights["acoustic_rms"] * acoustic["rms_score"])
                + (active_weights["pitch_variance"] * acoustic["pitch_score"])
                + (active_weights["wpm_velocity"] * acoustic["wpm_score"])
            )
            cand["heatmap_score"] = heat_score
            cand["acoustic"] = acoustic
            cand["pre_score"] = pre_score
            scored.append(cand)

        # Deduplicate overlapping candidates before LLM scoring
        scored.sort(key=lambda c: c["pre_score"], reverse=True)
        pruned_for_llm = []
        for c in scored:
            if any(
                max(0.0, min(c["end"], p["end"]) - max(c["start"], p["start"])) > 2.0
                for p in pruned_for_llm
            ):
                continue
            pruned_for_llm.append(c)
            if len(pruned_for_llm) >= 10:
                break

        # 4. LLM Semantic Evaluation
        final_clips = []
        for cand in pruned_for_llm:
            llm_eval = llm_scorer.score_segment(
                cand["text"], cand["duration"], narrative_profile=narrative_profile
            )
            sem_score = llm_eval.get("semantic_score", 0.6)
            final_score = (
                (active_weights["crowd_heatmap"] * cand["heatmap_score"])
                + (active_weights["semantic_hook"] * sem_score)
                + (active_weights["acoustic_rms"] * cand["acoustic"]["rms_score"])
                + (active_weights["pitch_variance"] * cand["acoustic"]["pitch_score"])
                + (active_weights["wpm_velocity"] * cand["acoustic"]["wpm_score"])
            )
            cand["final_hype_score"] = round(final_score, 4)
            cand["llm_evaluation"] = llm_eval
            cand["viral_title"] = llm_eval.get("viral_title", "")
            cand["hook_banner_text"] = llm_eval.get("hook_banner_text", "")
            final_clips.append(cand)

        final_clips.sort(key=lambda c: c["final_hype_score"], reverse=True)

        # 5. Non-Maximum Suppression (zero overlap guarantee)
        selected = []
        for cand in final_clips:
            if len(selected) >= top_k:
                break
            overlap = False
            for s in selected:
                inter = max(0.0, min(cand["end"], s["end"]) - max(cand["start"], s["start"]))
                if inter > 1.0:
                    overlap = True
                    break
            if not overlap:
                selected.append(cand)

        return selected
