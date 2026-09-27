"""
Video Composer: Executes FFmpeg pipeline for single or split-screen stacked cropping, subtitles, and rendering.
Adapted from OpenShorts architecture.
"""

import os
import re
import subprocess
import logging
from pathlib import Path
from typing import Tuple, Optional, Any

logger = logging.getLogger(__name__)


class VideoComposer:
    """Executes single-pass hardware or CPU accelerated FFmpeg rendering."""

    def __init__(self, output_width: int = 1080, output_height: int = 1920):
        self.output_width = output_width
        self.output_height = output_height

    def _has_audio_stream(self, video_path: str) -> bool:
        """Checks if input file contains an audio stream."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "a",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0",
            str(video_path),
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            return "audio" in res.stdout
        except Exception:
            return False

    def render_short(
        self,
        input_video_path: str,
        start_sec: float,
        end_sec: float,
        crop_box: Optional[Tuple[int, int, int, int]] = None,
        ass_subtitle_path: str = "",
        output_path: str = "",
        hook_banner_text: Optional[str] = None,
        zoom_factor: float = 1.08,
        banner_duration: float = 4.5,
        layout_plan: Optional[Any] = None,
    ) -> Path:
        """
        Renders a studio-grade vertical YouTube Short with:
        - OpenShorts-style Single or Dual-Speaker Split-Screen Stack layout
        - Dynamic framing & zoom crop to eliminate original letterbox captions
        - High-resolution scaling to 1080x1920
        - Kinetic burned-in ASS karaoke subtitles (monotonic non-stacking)
        - Timed 4.5s safe-zone hook banner pill card
        - YouTube standard audio loudness normalization (-14 LUFS) with micro-fades
        """
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        duration = end_sec - start_sec

        # Determine if we should render Split-Screen Stack or Single Crop
        is_split = (
            layout_plan is not None
            and getattr(layout_plan, "layout_type", "single") == "split_screen_stack"
            and getattr(layout_plan, "top_crop", None) is not None
            and getattr(layout_plan, "bottom_crop", None) is not None
        )

        clean_ass_path = str(ass_subtitle_path).replace("\\", "/").replace(":", "\\:")

        # Prepare banner text filter helper
        banner_filters = []
        if hook_banner_text:
            clean_banner = re.sub(r"^[>\-\s]+", "", hook_banner_text).strip()
            clean_banner = re.sub(r"\[.*?\]", "", clean_banner).strip()
            safe_text = (
                clean_banner.replace("'", "")
                .replace(":", "\\:")
                .replace("%", "\\%")
                .strip()
            )

            words = safe_text.split()
            lines = []
            cur_line = []
            cur_len = 0
            for w in words:
                if cur_len + len(w) + 1 > 28 and cur_line:
                    lines.append(" ".join(cur_line))
                    cur_line = [w]
                    cur_len = len(w)
                else:
                    cur_line.append(w)
                    cur_len += len(w) + 1
            if cur_line:
                lines.append(" ".join(cur_line))

            lines = lines[:2]
            dur_filter = f"between(t,0,{banner_duration})"

            banner_y = 160 if is_split else 220
            if len(lines) == 1:
                banner_filters.extend([
                    f"drawbox=x=(w-880)/2:y={banner_y}:w=880:h=90:color=black@0.85:t=fill:enable='{dur_filter}'",
                    f"drawtext=text='{lines[0]}':fontcolor=white:fontsize=38:x=(w-text_w)/2:y={banner_y + 26}:borderw=2:bordercolor=black:enable='{dur_filter}'",
                ])
            elif len(lines) >= 2:
                banner_filters.extend([
                    f"drawbox=x=(w-920)/2:y={banner_y}:w=920:h=140:color=black@0.85:t=fill:enable='{dur_filter}'",
                    f"drawtext=text='{lines[0]}':fontcolor=white:fontsize=34:x=(w-text_w)/2:y={banner_y + 20}:borderw=2:bordercolor=black:enable='{dur_filter}'",
                    f"drawtext=text='{lines[1]}':fontcolor=white:fontsize=34:x=(w-text_w)/2:y={banner_y + 68}:borderw=2:bordercolor=black:enable='{dur_filter}'",
                ])

        cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(round(start_sec, 2)),
            "-i", str(input_video_path),
            "-t", str(round(duration, 2)),
        ]

        if is_split:
            logger.info(f"Rendering in OpenShorts DUAL-SPEAKER SPLIT-SCREEN STACK layout...")
            half_h = self.output_height // 2
            tx, ty, tw, th = layout_plan.top_crop
            bx, by, bw, bh = layout_plan.bottom_crop
            div_th = getattr(layout_plan, "divider_thickness", 4)
            div_y = half_h - (div_th // 2)

            filter_complex_parts = [
                f"[0:v]crop={tw}:{th}:{tx}:{ty},scale={self.output_width}:{half_h}:flags=bicubic[top]",
                f"[0:v]crop={bw}:{bh}:{bx}:{by},scale={self.output_width}:{half_h}:flags=bicubic[bot]",
                f"[top][bot]vstack[stacked]",
                f"[stacked]drawbox=y={div_y}:h={div_th}:color={layout_plan.divider_color}:t=fill[with_div]",
            ]

            last_link = "with_div"
            if banner_filters:
                banner_str = ",".join(banner_filters)
                filter_complex_parts.append(f"[{last_link}]{banner_str}[with_banner]")
                last_link = "with_banner"

            if clean_ass_path:
                filter_complex_parts.append(f"[{last_link}]ass='{clean_ass_path}'[outv]")
                last_link = "outv"

            fc_str = ";".join(filter_complex_parts)
            cmd.extend(["-filter_complex", fc_str, "-map", f"[{last_link}]", "-map", "0:a?"])
        else:
            # Single Speaker layout
            eff_crop = crop_box
            if eff_crop is None and layout_plan is not None:
                eff_crop = (layout_plan.crop_x, layout_plan.crop_y, layout_plan.crop_w, layout_plan.crop_h)
            if eff_crop is None:
                eff_crop = (0, 0, self.output_width, self.output_height)

            cx, cy, cw, ch = eff_crop

            if zoom_factor > 1.0:
                zw = max(100, int(cw / zoom_factor))
                zh = max(100, int(ch / zoom_factor))
                zx = cx + int((cw - zw) / 2)
                zy = cy + int((ch - zh) / 2)
                zw -= (zw % 2)
                zh -= (zh % 2)
                cx, cy, cw, ch = zx, zy, zw, zh

            v_filters = [
                f"crop={cw}:{ch}:{cx}:{cy}",
                f"scale={self.output_width}:{self.output_height}:flags=bicubic",
            ]
            v_filters.extend(banner_filters)
            if clean_ass_path:
                v_filters.append(f"ass='{clean_ass_path}'")

            cmd.extend(["-vf", ",".join(v_filters)])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "20",
        ])

        # Handle audio normalization with micro-fades
        if self._has_audio_stream(str(input_video_path)):
            out_fade_start = max(0.0, round(duration - 0.25, 2))
            audio_filter = (
                f"loudnorm=I=-14:LRA=7:tp=-1.0,"
                f"afade=t=in:ss=0:d=0.15,"
                f"afade=t=out:st={out_fade_start}:d=0.25"
            )
            cmd.extend([
                "-af", audio_filter,
                "-c:a", "aac",
                "-b:a", "192k",
            ])
        else:
            cmd.extend(["-an"])

        cmd.append(str(out_file))

        logger.info(f"Rendering Short ({duration:.1f}s) to {out_file}...")
        res = subprocess.run(cmd, capture_output=True, text=True)

        if res.returncode != 0:
            logger.error(f"FFmpeg error: {res.stderr}")
            raise RuntimeError(f"FFmpeg render failed with exit code {res.returncode}:\n{res.stderr}")

        logger.info(f"Successfully rendered: {out_file}")
        return out_file
