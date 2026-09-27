"""
Face Tracker Module: OpenShorts-adapted multi-speaker computer vision tracker.
Tracks active speaker coordinates using Google MediaPipe Face Detection,
detects letterbox bars, and generates intelligent Single or Dual-Speaker Split-Screen layouts.
"""

import os
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Tuple, List, Optional, Dict, Any
import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class LayoutPlan:
    """Represents the optimal video cropping and composition strategy."""
    layout_type: str  # "single" or "split_screen_stack"
    # Primary 9:16 crop window (used directly in "single" mode)
    crop_x: int
    crop_y: int
    crop_w: int
    crop_h: int
    # Split-screen stacked crops (each 9:8 aspect ratio)
    top_crop: Optional[Tuple[int, int, int, int]] = None     # (x, y, w, h)
    bottom_crop: Optional[Tuple[int, int, int, int]] = None  # (x, y, w, h)
    divider_color: str = "white@0.25"
    divider_thickness: int = 4


class FaceTracker:
    """Tracks speaker face coordinates across a video clip to generate vertical short layouts."""

    def __init__(self, smoothing_alpha: float = 0.15):
        self.smoothing_alpha = smoothing_alpha
        self.mp_detector = self._load_mediapipe_detector()
        self.face_cascade = self._load_fallback_cascade()

    def _load_mediapipe_detector(self):
        """Loads MediaPipe Tasks FaceDetector using local TFLite model."""
        try:
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision

            project_root = Path(__file__).resolve().parent.parent.parent
            model_path = project_root / "assets" / "models" / "blaze_face_short_range.tflite"

            if model_path.exists():
                base_options = python.BaseOptions(model_asset_path=str(model_path))
                options = vision.FaceDetectorOptions(base_options=base_options, min_detection_confidence=0.35)
                return vision.FaceDetector.create_from_options(options)
            else:
                logger.warning(f"MediaPipe model not found at {model_path}. Using Haar fallback.")
        except Exception as e:
            logger.warning(f"Could not initialize MediaPipe FaceDetector: {e}. Using Haar fallback.")
        return None

    def _load_fallback_cascade(self) -> Optional[cv2.CascadeClassifier]:
        """Loads Haar Cascade as a fallback if MediaPipe is unavailable."""
        project_root = Path(__file__).resolve().parent.parent.parent
        local_model = project_root / "assets" / "models" / "haarcascade_frontalface_default.xml"
        if local_model.exists():
            cascade = cv2.CascadeClassifier(str(local_model))
            if not cascade.empty():
                return cascade

        if hasattr(cv2, "data") and hasattr(cv2.data, "haarcascades"):
            cv_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
            if cv_path.exists():
                cascade = cv2.CascadeClassifier(str(cv_path))
                if not cascade.empty():
                    return cascade

        return None

    def detect_letterbox_bars(self, video_path: str, sample_time_sec: float = 60.0) -> Tuple[int, int]:
        """
        Detects top and bottom black letterbox bars in widescreen content.
        Uses symmetric boundary calculation to eliminate black bars and any captions burned into them.
        Returns (top_bar_height, bottom_bar_start_y).
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return 0, 1080

        cap.set(cv2.CAP_PROP_POS_MSEC, sample_time_sec * 1000)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            return 0, 1080

        h, w, _ = frame.shape
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        row_means = np.mean(gray, axis=1)

        # Detect top black bar by scanning downward from top edge
        top_bar = 0
        while top_bar < h // 4 and row_means[top_bar] < 14:
            top_bar += 1

        if top_bar >= 24:
            bottom_bar = h - top_bar
        else:
            bottom_bar = h

        # Ensure even coordinates
        top_bar = top_bar + (top_bar % 2)
        bottom_bar = bottom_bar - (bottom_bar % 2)

        return top_bar, bottom_bar

    def calculate_layout_plan(
        self,
        video_path: str,
        start_sec: float,
        end_sec: float,
        target_aspect_ratio: float = 9.0 / 16.0,
    ) -> LayoutPlan:
        """
        OpenShorts-inspired layout detection:
        Samples frames across [start_sec, end_sec], detects speaker faces with MediaPipe,
        determines if content is Single Speaker or Multi-Speaker Dialogue, and computes
        either a Single 9:16 Crop or a Dual-Cam 9:8 Split-Screen Stacked Plan.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Cannot open video: {video_path}")
            return LayoutPlan("single", 0, 0, 1080, 1920)

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        # 1. Letterbox bar elimination
        top_bar, bottom_bar = self.detect_letterbox_bars(video_path, (start_sec + end_sec) / 2.0)
        active_h = bottom_bar - top_bar

        if top_bar >= 24 and active_h < orig_h - 40:
            crop_h = active_h
            crop_y = top_bar
        else:
            crop_h = orig_h
            crop_y = 0

        crop_w = int(crop_h * target_aspect_ratio)
        if crop_w > orig_w:
            crop_w = orig_w
            crop_h = int(crop_w / target_aspect_ratio)

        # Ensure even dimensions
        crop_w = crop_w - (crop_w % 2)
        crop_h = crop_h - (crop_h % 2)
        crop_y = crop_y - (crop_y % 2)

        # 2. Multi-face sampling across clip
        detected_frames: List[List[Dict[str, float]]] = []
        cap = cv2.VideoCapture(video_path)
        start_frame = int(start_sec * fps)
        end_frame = int(end_sec * fps)
        sample_step = max(1, int(fps / 2))  # Sample every 0.5s

        cap.set(cv2.CAP_PROP_POS_MSEC, start_sec * 1000)
        current_frame = start_frame

        import mediapipe as mp
        while current_frame <= end_frame:
            ret, frame = cap.read()
            if not ret:
                break

            if (current_frame - start_frame) % sample_step == 0:
                frame_faces = []
                if self.mp_detector is not None:
                    # MediaPipe detection
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                    res = self.mp_detector.detect(mp_img)
                    for d in res.detections:
                        bb = d.bounding_box
                        score = d.categories[0].score if d.categories else 0.5
                        frame_faces.append({
                            "cx": bb.origin_x + bb.width / 2.0,
                            "cy": bb.origin_y + bb.height / 2.0,
                            "w": bb.width,
                            "h": bb.height,
                            "score": score
                        })
                elif self.face_cascade is not None:
                    # Haar fallback
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    active_gray = gray[crop_y : crop_y + crop_h, :]
                    faces = self.face_cascade.detectMultiScale(
                        active_gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60)
                    )
                    for fx, fy, fw, fh in faces:
                        frame_faces.append({
                            "cx": fx + fw / 2.0,
                            "cy": crop_y + fy + fh / 2.0,
                            "w": fw,
                            "h": fh,
                            "score": 0.8
                        })

                if frame_faces:
                    detected_frames.append(frame_faces)

            current_frame += 1

        cap.release()

        # 3. Analyze spatial clustering across frames
        all_centers = [f["cx"] for frame in detected_frames for f in frame]
        two_faces_count = sum(1 for frame in detected_frames if len(frame) >= 2)

        # Detect if there are two distinct spatial speakers (e.g. Host on Left, Guest on Right)
        is_dual_speaker = False
        left_speaker_x = None
        right_speaker_x = None

        if len(all_centers) >= 4:
            centers_arr = np.array(all_centers)
            p25 = float(np.percentile(centers_arr, 25))
            p75 = float(np.percentile(centers_arr, 75))
            spread = p75 - p25

            # If two faces frequently co-occur in the same frame, or spatial spread > 320px
            if two_faces_count >= max(2, len(detected_frames) * 0.25) or (spread > 320 and len(detected_frames) >= 4):
                left_faces = [x for x in all_centers if x < orig_w * 0.5]
                right_faces = [x for x in all_centers if x >= orig_w * 0.5]
                if left_faces and right_faces:
                    is_dual_speaker = True
                    left_speaker_x = float(np.median(left_faces))
                    right_speaker_x = float(np.median(right_faces))
                    logger.info(
                        f"[OpenShorts Layout] Dual-speaker podcast dialogue detected! "
                        f"Left speaker at x={left_speaker_x:.1f}, Right speaker at x={right_speaker_x:.1f}."
                    )

        # 4. Construct Layout Plan
        if is_dual_speaker and left_speaker_x is not None and right_speaker_x is not None:
            # Dual-speaker Split-Screen Stack (9:8 aspect ratio each, stacking to 9:16)
            stack_target_ar = 9.0 / 8.0
            stack_h = crop_h
            stack_w = int(stack_h * stack_target_ar)
            if stack_w > orig_w:
                stack_w = orig_w
                stack_h = int(stack_w / stack_target_ar)

            stack_w -= (stack_w % 2)
            stack_h -= (stack_h % 2)

            # Left speaker (placed in Top half - typically Guest)
            top_x = max(0, min(int(left_speaker_x - stack_w / 2.0), orig_w - stack_w))
            top_x -= (top_x % 2)
            top_crop = (top_x, crop_y, stack_w, stack_h)

            # Right speaker (placed in Bottom half - typically Host)
            bot_x = max(0, min(int(right_speaker_x - stack_w / 2.0), orig_w - stack_w))
            bot_x -= (bot_x % 2)
            bottom_crop = (bot_x, crop_y, stack_w, stack_h)

            return LayoutPlan(
                layout_type="split_screen_stack",
                crop_x=top_x,
                crop_y=crop_y,
                crop_w=stack_w,
                crop_h=stack_h,
                top_crop=top_crop,
                bottom_crop=bottom_crop,
                divider_color="white@0.25",
                divider_thickness=4,
            )

        # Single Speaker Mode (Default full-bleed 9:16)
        if all_centers:
            speaker_x = float(np.median(all_centers))
        else:
            speaker_x = orig_w / 2.0

        single_x = max(0, min(int(speaker_x - (crop_w / 2.0)), orig_w - crop_w))
        single_x -= (single_x % 2)

        return LayoutPlan(
            layout_type="single",
            crop_x=single_x,
            crop_y=crop_y,
            crop_w=crop_w,
            crop_h=crop_h,
        )

    def calculate_crop_window(
        self,
        video_path: str,
        start_sec: float,
        end_sec: float,
        target_aspect_ratio: float = 9.0 / 16.0,
    ) -> Tuple[int, int, int, int]:
        """Backward-compatible crop calculation returning (x, y, w, h)."""
        plan = self.calculate_layout_plan(video_path, start_sec, end_sec, target_aspect_ratio)
        return plan.crop_x, plan.crop_y, plan.crop_w, plan.crop_h
