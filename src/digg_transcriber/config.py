"""Configuration management for digg-transcriber."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from digg_transcriber.paths import OutputMode
from digg_transcriber.xdg import (
    config_example_path,
    default_config_path,
    dt_config_dir,
    migrate_legacy_config,
    resolve_config_path,
)


def bundled_config_example_text() -> str:
    pkg_dir = Path(__file__).resolve().parent
    return (pkg_dir / "config.yaml.example").read_text(encoding="utf-8")


def default_config_dict() -> dict:
    return {
        "model": "medium",
        "language": "auto",
        "output_mode": "archive",
        "output_dir": str(Path.home() / "Transcripts"),
        "formats": ["vtt", "txt"],
        "watch": {
            "paths": [],
            "debounce_seconds": 2,
            "extensions": [".mp4", ".mov", ".avi", ".mkv", ".mp3", ".m4a", ".wav", ".flac"],
        },
        "podcast": {
            "podcast_index_api_key": "",
            "podcast_index_api_secret": "",
        },
    }


@dataclass
class AppConfig:
    model: str = "medium"
    language: str = "auto"
    output_mode: OutputMode = OutputMode.ARCHIVE
    output_dir: Path = field(default_factory=lambda: Path.home() / "Transcripts")
    formats: list[str] = field(default_factory=lambda: ["vtt", "txt"])
    watch_paths: list[Path] = field(default_factory=list)
    watch_debounce_seconds: float = 2.0
    watch_extensions: list[str] = field(
        default_factory=lambda: [".mp4", ".mov", ".avi", ".mkv", ".mp3", ".m4a", ".wav", ".flac"]
    )
    podcast_index_api_key: str = ""
    podcast_index_api_secret: str = ""


def load_config(path: Optional[Path] = None) -> AppConfig:
    cfg_path = resolve_config_path(path)
    data = default_config_dict()
    if cfg_path.exists():
        loaded = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        data.update(loaded)
    watch = data.get("watch") or {}
    return AppConfig(
        model=data["model"],
        language=data["language"],
        output_mode=OutputMode(data["output_mode"]),
        output_dir=Path(data["output_dir"]).expanduser(),
        formats=list(data["formats"]),
        watch_paths=[Path(p).expanduser() for p in watch.get("paths", [])],
        watch_debounce_seconds=float(watch.get("debounce_seconds", 2)),
        watch_extensions=list(
            watch.get("extensions", [".mp4", ".mov", ".avi", ".mkv", ".mp3", ".m4a", ".wav", ".flac"])
        ),
    )


def write_default_config(path: Optional[Path] = None, *, force: bool = False) -> tuple[Path, bool]:
    cfg_path = resolve_config_path(path)
    existed_before = cfg_path.is_file()
    migrated = migrate_legacy_config(cfg_path)
    dt_config_dir().mkdir(parents=True, exist_ok=True)
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    if cfg_path.exists() and not force and (existed_before or migrated is None):
        return cfg_path, False
    cfg_path.write_text(bundled_config_example_text(), encoding="utf-8")
    return cfg_path, True


__all__ = ["AppConfig", "load_config", "write_default_config", "default_config_dict"]