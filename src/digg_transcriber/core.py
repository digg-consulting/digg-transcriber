"""Core pipeline orchestration for digg-transcriber."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Optional

from digg_transcriber.config import AppConfig
from digg_transcriber.database import mark_processed
from digg_transcriber.paths import OutputMode, output_paths_for, should_skip, move_source_to_archive
from digg_transcriber.plugins import SOURCE_PLUGINS
from digg_transcriber.whisper import get_transcriber
from digg_transcriber.writers import write_formats

logger = logging.getLogger(__name__)


def discover_sources(
    path: Path,
    extensions: set[str],
    recursive: bool = True,
    exclude_under: Optional[Path] = None,
) -> list[tuple[str, Path]]:
    ext_set = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in extensions}
    if path.is_file():
        if path.suffix.lower() not in ext_set:
            return []
        return [(detect_source_type(path), path)]

    pattern = "**/*" if recursive else "*"
    results = []
    for p in path.glob(pattern):
        if not p.is_file():
            continue
        if p.suffix.lower() not in ext_set:
            continue
        if exclude_under and _is_under(p, exclude_under):
            continue
        results.append((detect_source_type(p), p))

    return sorted(results, key=lambda x: str(x[1]))


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def detect_source_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}:
        return "video"
    if suffix in {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".opus", ".aac"}:
        return "local_audio"
    return "local_audio"


def run_job(
    source: Path,
    cfg: AppConfig,
    *,
    force: bool = False,
) -> str:
    """Returns: 'ok' | 'skipped' | 'failed'"""
    source_type = detect_source_type(source)
    plugin_cls = SOURCE_PLUGINS.get(source_type)
    if plugin_cls is None:
        logger.error("no plugin for source type: %s", source_type)
        return "failed"

    plugin = plugin_cls()
    source_id = plugin.get_id(source)
    title = plugin.get_title(source)

    out_paths = output_paths_for(
        source,
        output_mode=cfg.output_mode,
        output_dir=cfg.output_dir,
        formats=cfg.formats,
    )

    if should_skip(
        out_paths,
        formats=cfg.formats,
        force=force,
        source_path=source,
        output_mode=cfg.output_mode,
    ):
        logger.info("skip %s (outputs exist)", source)
        return "skipped"

    audio_path: Optional[Path] = None
    try:
        logger.info("prepare audio: %s", source)
        audio_path = plugin.prepare_audio(source)

        logger.info("transcribe: %s", source)
        transcriber = get_transcriber(cfg.model, cfg.language if cfg.language != "auto" else None)
        result = transcriber(audio_path)

        write_formats(result.text, result.segments, out_paths, formats=cfg.formats)

        if cfg.output_mode == OutputMode.ARCHIVE:
            dest = move_source_to_archive(source, out_paths)
            logger.info("archived source: %s", dest)
        elif cfg.output_mode != OutputMode.BESIDE and audio_path != source:
            plugin.cleanup_source(source)
            logger.info("deleted source: %s", source)

        logger.info(
            "wrote %s",
            ", ".join(str(out_paths[f]) for f in cfg.formats),
        )

        mark_processed(source_id, source_type, title, out_paths[cfg.formats[0]])
        return "ok"

    except Exception:
        logger.exception("failed: %s", source)
        return "failed"
    finally:
        if audio_path is not None:
            plugin.cleanup(audio_path)


def _safe_path_component(value: Optional[str], default: str) -> str:
    safe = (value or default).replace("/", "_").replace("\\", "_").strip()
    safe = safe or default
    return safe[:100]


def run_podcast_job(
    rss_url: str,
    cfg: AppConfig,
    *,
    force: bool = False,
    episode_guid: Optional[str] = None,
) -> str:
    """Transcribe a podcast episode from RSS feed URL.
    
    Returns: 'ok' | 'skipped' | 'failed'
    """
    from digg_transcriber.plugins.podcast import PodcastSource

    plugin = PodcastSource(rss_url, episode_guid=episode_guid)
    source_id = plugin.get_id()
    title = plugin.get_title()
    podcast_title = _safe_path_component(plugin.get_podcast_title(), "untitled-podcast")
    episode_stem = _safe_path_component(title, "untitled-episode")
    audio_url = plugin.get_audio_url()

    if not audio_url:
        logger.error("no audio URL found for podcast episode")
        return "failed"

    paths: dict[str, Path] = {}
    folder = cfg.output_dir / podcast_title / episode_stem
    for fmt in cfg.formats:
        paths[fmt] = folder / f"{episode_stem}.{fmt}"

    if not force and all(p.exists() for p in paths.values()):
        logger.info("skip podcast episode (outputs exist)")
        return "skipped"

    audio_path: Optional[Path] = None
    try:
        logger.info("download audio: %s", audio_url)
        audio_path = _download_audio(audio_url)

        logger.info("transcribe podcast: %s", title)
        transcriber = get_transcriber(cfg.model, cfg.language if cfg.language != "auto" else None)
        result = transcriber(audio_path)

        write_formats(result.text, result.segments, paths, formats=cfg.formats)

        logger.info(
            "wrote %s",
            ", ".join(str(paths[f]) for f in cfg.formats),
        )

        mark_processed(source_id, "podcast", title, paths[cfg.formats[0]])
        return "ok"

    except Exception:
        logger.exception("failed: podcast episode")
        return "failed"
    finally:
        if audio_path is not None and audio_path.exists():
            audio_path.unlink(missing_ok=True)


def _download_audio(url: str) -> Path:
    from digg_transcriber.http_client import get_http_session
    
    session = get_http_session()
    response = session.get(url, stream=True, timeout=60)
    response.raise_for_status()

    suffix = ".mp3"
    if "." in url.split("/")[-1].split("?")[0]:
        suffix = "." + url.split("/")[-1].split("?")[0].split(".")[-1]

    fd, tmp_name = tempfile.mkstemp(suffix=suffix)
    import os
    os.close(fd)
    tmp = Path(tmp_name)

    with open(tmp, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    return tmp


__all__ = [
    "discover_sources",
    "detect_source_type",
    "run_job",
    "run_podcast_job",
]