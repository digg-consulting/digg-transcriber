"""Local audio source plugin for digg-transcriber."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class LocalAudioSource:
    extensions = {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".opus", ".aac"}

    def get_id(self, source: Path) -> str:
        return str(source.resolve())

    def get_title(self, source: Path) -> Optional[str]:
        return source.stem

    def prepare_audio(self, source: Path) -> Path:
        return source

    def cleanup(self, audio_path: Path) -> None:
        pass

    def cleanup_source(self, source: Path) -> None:
        source.unlink(missing_ok=True)