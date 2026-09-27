"""Hype Fusion Engine: Combines heatmap, acoustic dynamics, and semantic LLM scores."""

import logging
from typing import Dict, List, Any, Tuple, Optional
from src.ingestion.heatmap import YouTubeHeatmapExtractor
from src.hype_detector.audio_energy import AudioEnergyAnalyzer
from src.hype_detector.llm_scorer import LLMSemanticScorer

logger = logging.getLogger(__name__)


class HypeFusionEngine:
    """Fuses multi-modal signals to detect and rank the most viral video moments."""

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        min_clip_duration: float = 18.0,
        max_clip_duration: float = 55.0,
        sliding_step: float = 5.0,
        nms_overlap_threshold: float = 0.30,
    ):
        self.weights = weights or {
            "crowd_heatmap": 0.35,
            "semantic_hook": 0.30,
            "acoustic_rms": 0.15,
            "pitch_variance": 0.10,
            "wpm_velocity": 0.10,
        }
        self.min_clip_duration = min_clip_duration
        self.max_clip_duration = max_clip_duration
        self.sliding_step = sliding_step
        self.nms_overlap_threshold = nms_overlap_threshold

    def find_top_clips(
        self,
        transcript_data: Dict[str, Any],
        audio_features: Dict[str, Any],
        heatmap: List[Tuple[float, float]],
        llm_scorer: LLMSemanticScorer,
        top_k: int = 3,
        narrative_profile: Optional[Any] = None,
        use_hook_discovery: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Generates candidate segments, prioritizing the high-retention hook zone,
        scores them with multi-signal fusion, applies Non-Maximum Suppression (NMS),
        and returns the top K viral clips.
        """
        if use_hook_discovery:
            from src.hype_detector.hook_discovery import HookDiscoveryEngine
            hook_engine = HookDiscoveryEngine(
                weights=self.weights,
                min_clip_duration=self.min_clip_duration,
                max_clip_duration=self.max_clip_duration,
            )
            discovered_hooks = hook_engine.discover_top_hooks(
                transcript_data=transcript_data,
                audio_features=audio_features,
                heatmap=heatmap,
                llm_scorer=llm_scorer,
                top_k=top_k,
                narrative_profile=narrative_profile,
            )
            if discovered_hooks:
                return discovered_hooks

        duration = audio_features.get("duration", 0.0)
        if duration < self.min_clip_duration:
            logger.warning("Video is shorter than minimum clip duration.")
            return []

        all_words = transcript_data.get("all_words", [])
        if not all_words:
            logger.warning("No words found in transcript.")
            return []

        # Adjust weights if heatmap is unavailable
        active_weights = dict(self.weights)
        if not heatmap:
            active_weights["crowd_heatmap"] = 0.0
            active_weights["semantic_hook"] = 0.45
            active_weights["acoustic_rms"] = 0.25
            active_weights["pitch_variance"] = 0.15
            active_weights["wpm_velocity"] = 0.15

        candidates: List[Dict[str, Any]] = []

        # Generate candidate windows across duration
        t_start = 0.0
        while t_start + self.min_clip_duration <= duration:
            for target_len in [22.0, 30.0, 42.0, 52.0]:
                raw_end = t_start + target_len
                if raw_end > duration:
                    continue

                # Snap start and end to actual Whisper word boundaries
                snapped_start, snapped_end, words = self._snap_to_word_boundaries(
                    all_words, t_start, raw_end
                )

                clip_dur = snapped_end - snapped_start
                if clip_dur < self.min_clip_duration or clip_dur > self.max_clip_duration:
                    continue

                # 1. Crowd Heatmap Score
                if heatmap:
                    heat_scores = [
                        YouTubeHeatmapExtractor.get_heat_at_time(heatmap, t)
                        for t in [snapped_start, (snapped_start + snapped_end) / 2.0, snapped_end]
                    ]
                    heatmap_score = float(sum(heat_scores) / len(heat_scores))
                else:
                    heatmap_score = 0.0

                # 2. Acoustic Score (RMS, Pitch, WPM)
                acoustic = AudioEnergyAnalyzer().score_window(
                    audio_features, snapped_start, snapped_end, words
                )

                # Segment text
                segment_text = " ".join([w["word"] for w in words])

                # 3. Fast Heuristic Pre-Score to filter before expensive LLM calls
                pre_score = (
                    (active_weights["crowd_heatmap"] * heatmap_score)
                    + (active_weights["acoustic_rms"] * acoustic["rms_score"])
                    + (active_weights["pitch_variance"] * acoustic["pitch_score"])
                    + (active_weights["wpm_velocity"] * acoustic["wpm_score"])
                )

                candidates.append({
                    "start": snapped_start,
                    "end": snapped_end,
                    "duration": round(clip_dur, 2),
                    "text": segment_text,
                    "words": words,
                    "heatmap_score": heatmap_score,
                    "acoustic": acoustic,
                    "pre_score": pre_score,
                })

            t_start += self.sliding_step

        if not candidates:
            return []

        # Sort candidates by pre-score and pick top 15 for full LLM semantic evaluation
        candidates.sort(key=lambda c: c["pre_score"], reverse=True)
        top_candidates = candidates[:15]

        # 4. LLM Semantic Evaluation on top candidates
        scored_candidates = []
        for cand in top_candidates:
            llm_eval = llm_scorer.score_segment(
                cand["text"], cand["duration"], narrative_profile=narrative_profile
            )
            semantic_score = llm_eval.get("semantic_score", 0.5)

            final_hype_score = (
                (active_weights["crowd_heatmap"] * cand["heatmap_score"])
                + (active_weights["semantic_hook"] * semantic_score)
                + (active_weights["acoustic_rms"] * cand["acoustic"]["rms_score"])
                + (active_weights["pitch_variance"] * cand["acoustic"]["pitch_score"])
                + (active_weights["wpm_velocity"] * cand["acoustic"]["wpm_score"])
            )

            cand["final_hype_score"] = round(final_hype_score, 4)
            cand["llm_evaluation"] = llm_eval
            cand["viral_title"] = llm_eval.get("viral_title", "")
            cand["hook_banner_text"] = llm_eval.get("hook_banner_text", "")
            scored_candidates.append(cand)

        # Sort by final hype score
        scored_candidates.sort(key=lambda c: c["final_hype_score"], reverse=True)

        # 5. Non-Maximum Suppression (NMS) to eliminate overlapping clips
        selected_clips = self._apply_nms(scored_candidates, top_k)
        return selected_clips

    def _snap_to_word_boundaries(
        self, words: List[Dict[str, Any]], start_sec: float, end_sec: float
    ) -> Tuple[float, float, List[Dict[str, Any]]]:
        """Finds closest words and returns exact boundaries aligned to complete thoughts and sentences."""
        sub_words = [w for w in words if w["end"] >= start_sec and w["start"] <= end_sec]
        if not sub_words:
            return start_sec, end_sec, []

        # 1. Dialogue Hook Snapping: If a question or speaker turn appears in the first 12-15s,
        # snap forward so the short opens immediately on the punchy question!
        for i in range(1, min(len(sub_words) - 5, 25)):
            raw = sub_words[i]["word"].strip()
            # If word starts with ">>" (speaker turn marker)
            if raw.startswith(">>") and (sub_words[-1]["end"] - sub_words[i]["start"]) >= self.min_clip_duration:
                sub_words = sub_words[i:]
                break

        # 2. Clean Starter: Avoid starting on dangling prepositions or conjunctions
        bad_starters = {
            "for", "and", "cuz", "because", "so", "but", "or", "um", "uh", "like", "that", "this", "then", "which", "well", "a", "an", "the"
        }
        while len(sub_words) > 6:
            w_token = sub_words[0]["word"].lower().strip(".,?!\"'>-")
            if w_token in bad_starters:
                sub_words = sub_words[1:]
            else:
                break

        # 3. Clean Payoff Ending: Snap to the nearest sentence boundary within the last 8 words
        if len(sub_words) > 8:
            for back in range(len(sub_words) - 1, max(0, len(sub_words) - 8), -1):
                raw_w = sub_words[back]["word"].strip()
                if any(raw_w.endswith(p) for p in [".", "!", "?"]):
                    sub_words = sub_words[: back + 1]
                    break

        snapped_start = sub_words[0]["start"]
        snapped_end = sub_words[-1]["end"]
        return snapped_start, snapped_end, sub_words

    def _apply_nms(self, candidates: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        """Removes clips that overlap with higher-scoring clips to ensure each short is completely unique."""
        selected = []
        for cand in candidates:
            if len(selected) >= top_k:
                break

            overlap = False
            for s in selected:
                # Calculate temporal intersection in seconds
                intersection_start = max(cand["start"], s["start"])
                intersection_end = min(cand["end"], s["end"])
                intersection = max(0.0, intersection_end - intersection_start)

                # Strict non-overlap: reject if clips overlap by more than 1 second
                # to guarantee every selected Short covers a distinct story/topic.
                if intersection > 1.0:
                    overlap = True
                    break

            if not overlap:
                selected.append(cand)

        return selected
