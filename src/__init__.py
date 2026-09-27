"""Content Agent Root Package: Configures system PATH for FFmpeg and core environments."""

import os
import shutil
import sys
from pathlib import Path

__version__ = "0.1.0"

# Inject Windows native truststore to prevent network SSL verification errors
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass


def _ensure_ffmpeg_in_path():
    """Ensures FFmpeg and FFprobe are discoverable in PATH on Windows."""
    if shutil.which("ffmpeg"):
        return

    # Check common Windows winget / local link paths
    candidate_paths = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links",
        Path(os.environ.get("PROGRAMFILES", "")) / "ffmpeg" / "bin",
        Path("C:/ffmpeg/bin"),
    ]

    for p in candidate_paths:
        if p.exists() and (p / "ffmpeg.exe").exists():
            os.environ["PATH"] = str(p) + os.pathsep + os.environ.get("PATH", "")
            return


_ensure_ffmpeg_in_path()
