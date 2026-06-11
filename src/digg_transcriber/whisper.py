"""Whisper model backend for digg-transcriber.

Uses mlx-whisper on macOS (Apple Silicon), faster-whisper elsewhere.
"""

from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Optional

from digg_transcriber.hub_cache import (
    iter_snapshot_dirs,
)
from digg_transcriber.models import Segment, TranscriptResult


MLX_MODEL_REPOS = {
    "large-v3": "mlx-community/whisper-large-v3-mlx",
    "medium": "mlx-community/whisper-medium-mlx",
    "medium-8bit": "mlx-community/whisper-medium-mlx-8bit",
    "small": "mlx-community/whisper-small-mlx",
}

FASTER_MODEL_REPOS = {
    "large-v3": "large-v3",
    "medium": "medium",
    "small": "small",
    "base": "base",
    "tiny": "tiny",
}

_WEIGHT_FILES = ("*.bin", "*.safetensors", "*.pt", "*.npz", "*.ckpt")
_MIN_WEIGHT_BYTES = 1_000_000  # 1MB to distinguish real weights from LFS pointers


def _is_macos() -> bool:
    return platform.system() == "Darwin"


def resolve_model_repo(model: str) -> str:
    if model in MLX_MODEL_REPOS:
        return MLX_MODEL_REPOS[model]
    if "/" in model:
        return model
    raise ValueError(f"unknown model: {model}. Choose from {list(MLX_MODEL_REPOS)}")


def _weight_in_snapshot(snap_dir: Path) -> bool:
    for pattern in _WEIGHT_FILES:
        for path in snap_dir.rglob(pattern):
            if path.is_file():
                try:
                    if path.stat().st_size >= _MIN_WEIGHT_BYTES:
                        return True
                except OSError:
                    continue
    return False


def _whisper_snapshot_dir(repo_id: str) -> Optional[Path]:
    from digg_transcriber.hub_cache import hub_repo_dir
    root = hub_repo_dir(repo_id)
    if root is None:
        return None
    snaps = root / "snapshots"
    if not snaps.is_dir():
        return None
    for snap in iter_snapshot_dirs(repo_id):
        if (snap / "config.json").is_file() and _weight_in_snapshot(snap):
            return snap
    return None


def is_model_cached(model: str) -> bool:
    repo = resolve_model_repo(model)
    snap_dir = _whisper_snapshot_dir(repo)
    return snap_dir is not None


def model_prereq_help(model: str) -> str:
    repo = resolve_model_repo(model)
    return f"""Whisper model '{model}' is not in your local Hugging Face cache.

Prepare with the Hugging Face CLI:

  hf auth login
  hf download {repo} --include "config.json"
  digg-transcriber check --model {model}
"""


def get_transcriber(model: str = "medium", language: Optional[str] = None):
    """Get a transcriber function that processes audio files.

    Returns a callable that takes a path and returns TranscriptResult.
    """
    if _is_macos():
        repo = resolve_model_repo(model)
        snapshot = _whisper_snapshot_dir(repo)
        if snapshot is None:
            raise RuntimeError(model_prereq_help(model))

        import mlx_whisper

        def transcribe_path(audio_path: Path | str):
            result = mlx_whisper.transcribe(str(audio_path), path_or_hf_repo=str(snapshot))
            segments = [
                Segment(
                    start=float(s["start"]),
                    end=float(s["end"]),
                    text=str(s["text"]).strip(),
                )
                for s in result.get("segments", [])
            ]
            return TranscriptResult(
                text=str(result.get("text", "")).strip(),
                segments=segments,
                language=result.get("language"),
            )
        return transcribe_path
    else:
        from faster_whisper import WhisperModel

        device = "cuda" if os.environ.get("CUDA_VISIBLE_DEVICES") else "cpu"
        compute_type = "int8"

        model_obj = WhisperModel(
            model,
            device=device,
            compute_type=compute_type,
        )

        def transcribe_path(audio_path: Path | str):
            segs, info = model_obj.transcribe(
                str(audio_path),
                language=language if language and language != "auto" else None,
                vad_filter=True,
            )
            result_segs = [
                Segment(
                    start=float(s.start),
                    end=float(s.end),
                    text=s.text.strip(),
                )
                for s in segs
            ]
            return TranscriptResult(
                text=" ".join(s.text for s in result_segs),
                segments=result_segs,
                language=info.language if language and language != "auto" else None,
            )
        return transcribe_path


__all__ = [
    "resolve_model_repo",
    "is_model_cached",
    "model_prereq_help",
    "get_transcriber",
]