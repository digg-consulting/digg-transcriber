"""Detect models in the Hugging Face hub cache."""

from __future__ import annotations

from typing import Optional
from pathlib import Path


def repo_id_to_cache_folder(repo_id: str) -> str:
    return "models--" + repo_id.replace("/", "--")


def hub_repo_dir(repo_id: str) -> Optional[Path]:
    from digg_transcriber.xdg import hf_hub_cache_dir
    path = hf_hub_cache_dir() / repo_id_to_cache_folder(repo_id)
    return path if path.is_dir() else None


def iter_snapshot_dirs(repo_id: str):
    root = hub_repo_dir(repo_id)
    if root is None:
        return
    snaps = root / "snapshots"
    if not snaps.is_dir():
        return
    dirs = [p for p in snaps.iterdir() if p.is_dir()]
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    yield from dirs


def find_cached_snapshot_path(repo_id: str, filename: str) -> Optional[Path]:
    for snap in iter_snapshot_dirs(repo_id):
        path = snap / filename
        if path.is_file():
            return path
    return None


def find_cached_file(repo_id: str, filename: str) -> Optional[Path]:
    path = find_cached_snapshot_path(repo_id, filename)
    if path is None:
        return None
    try:
        return path.resolve()
    except OSError:
        return path


def find_cached_file_with_min_size(
    repo_id: str, filename: str, min_bytes: int
) -> Optional[Path]:
    path = find_cached_file(repo_id, filename)
    if path is None:
        return None
    try:
        if path.stat().st_size >= min_bytes:
            return path
    except OSError:
        pass
    return None


def hub_repo_has_weight_files(repo_id: str, min_bytes: int = 100_000) -> bool:
    patterns = ("*.bin", "*.safetensors", "*.pt", "*.npz", "*.ckpt")
    for snap in iter_snapshot_dirs(repo_id):
        for pattern in patterns:
            for path in snap.rglob(pattern):
                if path.is_file():
                    try:
                        if path.stat().st_size >= min_bytes:
                            return True
                    except OSError:
                        continue
    return False


__all__ = [
    "repo_id_to_cache_folder",
    "find_cached_file",
    "find_cached_file_with_min_size",
    "hub_repo_has_weight_files",
]