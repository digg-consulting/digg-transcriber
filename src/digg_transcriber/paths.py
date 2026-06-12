"""Output path resolution for digg-transcriber."""

from __future__ import annotations

import shutil
from enum import Enum
from pathlib import Path
from typing import Optional


class OutputMode(str, Enum):
    BESIDE = "beside"
    MIRROR = "mirror"
    FLAT = "flat"
    ARCHIVE = "archive"


def archive_dir_for(source: Path, output_dir: Path) -> Path:
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    base = output_dir / source.stem
    if source.parent.resolve() == base.resolve():
        return base
    if not base.exists():
        return base
    n = 2
    while True:
        candidate = output_dir / f"{source.stem}-{n}"
        if not candidate.exists():
            return candidate
        n += 1


def output_paths_for(
    source_path: Path,
    *,
    output_mode: OutputMode,
    output_dir: Path,
    formats: list[str],
    mirror_root: Optional[Path] = None,
) -> dict[str, Path]:
    stem = source_path.stem
    paths: dict[str, Path] = {}
    for fmt in formats:
        if output_mode == OutputMode.BESIDE:
            paths[fmt] = source_path.parent / f"{stem}.{fmt}"
        elif output_mode == OutputMode.FLAT:
            paths[fmt] = output_dir / f"{stem}.{fmt}"
        elif output_mode == OutputMode.MIRROR:
            if mirror_root is None:
                raise ValueError("mirror_root required for mirror mode")
            rel = source_path.relative_to(mirror_root)
            paths[fmt] = output_dir / rel.with_suffix(f".{fmt}")
        elif output_mode == OutputMode.ARCHIVE:
            folder = archive_dir_for(source_path, output_dir)
            paths[fmt] = folder / f"{stem}.{fmt}"
        else:
            raise ValueError(f"unknown output mode: {output_mode}")
    return paths


def archived_source_path(source_path: Path, output_paths: dict[str, Path]) -> Path:
    if not output_paths:
        raise ValueError("output_paths required")
    return next(iter(output_paths.values())).parent / source_path.name


def should_skip(
    paths: dict[str, Path],
    *,
    formats: list[str],
    force: bool = False,
    source_path: Optional[Path] = None,
    output_mode: Optional[OutputMode] = None,
) -> bool:
    if force:
        return False
    if not all(paths[fmt].parent.exists() and paths[fmt].exists() for fmt in formats):
        return False
    if output_mode == OutputMode.ARCHIVE and source_path is not None:
        return archived_source_path(source_path, paths).exists()
    return True


def move_source_to_archive(source_path: Path, output_paths: dict[str, Path]) -> Path:
    dest = archived_source_path(source_path, output_paths)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if source_path.resolve() == dest.resolve():
        return dest
    shutil.move(str(source_path), str(dest))
    return dest


__all__ = [
    "OutputMode",
    "archive_dir_for",
    "output_paths_for",
    "should_skip",
    "move_source_to_archive",
]