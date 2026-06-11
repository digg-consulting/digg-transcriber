"""Video source plugin for digg-transcriber."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from digg_transcriber.extract import extract_audio_wav


class VideoSource:
    extensions = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}

    def get_id(self, source: Path) -> str:
        return str(source.resolve())

    def get_title(self, source: Path) -> Optional[str]:
        return source.stem

    def prepare_audio(self, source: Path) -> Path:
        return extract_audio_wav(source)

    def cleanup(self, audio_path: Path) -> None:
        audio_path.unlink(missing_ok=True)

    def cleanup_source(self, source: Path) -> None:
        source.unlink(missing_ok=True)