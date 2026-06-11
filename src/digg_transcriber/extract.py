"""Audio extraction via ffmpeg for digg-transcriber."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Optional


class FfmpegNotFoundError(RuntimeError):
    pass


def require_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise FfmpegNotFoundError(
            "ffmpeg not found. Install with: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)"
        )
    return path


def extract_audio_wav(source_path: Path) -> Path:
    require_ffmpeg()
    fd, tmp_name = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    tmp = Path(tmp_name)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(tmp),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg failed: {proc.stderr.strip()}")
    return tmp


def wav_duration_seconds(wav_path: Path) -> Optional[float]:
    try:
        with wave.open(str(wav_path), "rb") as w:
            rate = w.getframerate()
            if rate <= 0:
                return None
            return w.getnframes() / float(rate)
    except (wave.Error, OSError):
        return None


__all__ = [
    "FfmpegNotFoundError",
    "require_ffmpeg",
    "extract_audio_wav",
    "wav_duration_seconds",
]