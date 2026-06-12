"""CLI for digg-transcriber."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from digg_transcriber.config import AppConfig, config_update_needed, load_config, update_config, write_default_config
from digg_transcriber.database import (
    add_podcast,
    fetch_podcast_episodes,
    get_all_episodes,
    get_all_podcasts,
    get_episodes_without_transcription,
    import_pod_transcriber_transcripts,
)
from digg_transcriber.core import discover_sources, run_job, detect_source_type, run_podcast_job
from digg_transcriber.paths import OutputMode
from digg_transcriber.podcast_index import search_podcasts, get_podcast_by_id, get_episodes_by_feed_id, get_client
from digg_transcriber.watcher import run_watch
from digg_transcriber.whisper import resolve_model_repo, is_model_cached, model_prereq_help

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("digg-transcriber")

CLI_NAME = "digg-transcriber"


def _confirm(prompt: str) -> bool:
    if not sys.stdin.isatty():
        print("Non-interactive mode: leaving config unchanged.")
        return False
    reply = input(prompt).strip().lower()
    return reply in {"y", "yes"}


def cmd_init(args: argparse.Namespace) -> int:
    path, created = write_default_config(force=args.force)
    if created:
        print(f"Created config: {path}")
        print("Edit this file to configure your paths and model.")
        return 0

    print(f"Config exists: {path}")
    missing = config_update_needed(path)
    if not missing:
        print("Config is up to date.")
        return 0

    print("Missing config options:")
    for item in missing:
        print(f"  - {item}")

    if args.update or _confirm("Update config with missing options? [y/N] "):
        update_config(path)
        print("Updated config with missing options.")
        return 0

    print("Config left unchanged.")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    model = args.model
    repo = resolve_model_repo(model)
    cached = is_model_cached(model)

    print(f"Model: {model}")
    print(f"Repo: {repo}")
    print(f"Cached: {'yes' if cached else 'no'}")

    if not cached:
        print("\n" + model_prereq_help(model))
        return 1
    return 0


def cmd_transcribe(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    if args.model:
        cfg.model = args.model
    if args.language:
        cfg.language = args.language
    if args.output_mode:
        cfg.output_mode = OutputMode(args.output_mode)
    if args.output_dir:
        cfg.output_dir = Path(args.output_dir)
    if args.formats:
        cfg.formats = [f.strip() for f in args.formats.split(",")]

    if not args.paths:
        print("No input paths provided")
        return 2

    all_sources = []
    for p in args.paths:
        path = Path(p).expanduser()
        sources = discover_sources(
            path,
            set(cfg.watch_extensions),
            recursive=args.recursive,
        )
        all_sources.extend(sources)

    if not all_sources:
        return 2

    counts = {"ok": 0, "skipped": 0, "failed": 0}
    for _source_type, source in all_sources:
        status = run_job(source, cfg, force=args.force)
        counts[status] += 1

    print(f"Done: {counts['ok']} ok, {counts['skipped']} skipped, {counts['failed']} failed")
    return 1 if counts["failed"] else 0


def cmd_watch(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    return run_watch(cfg, force=args.force)


def cmd_check_prereqs(args: argparse.Namespace) -> int:
    model = args.model or "medium"

    print("Checking prerequisites...")

    repo = resolve_model_repo(model)
    cached = is_model_cached(model)
    print(f"  Model '{model}': {'cached' if cached else 'NOT CACHED'}")

    if args.verbose:
        from digg_transcriber.hub_cache import find_cached_file, hf_hub_cache_dir
        cache_dir = hf_hub_cache_dir()
        print(f"  Cache dir: {cache_dir}")
        for name in ("config.json", "model.safetensors", "weights.npz"):
            path = find_cached_file(repo, name)
            if path is None:
                print(f"    {name}: not found")
            else:
                try:
                    size = path.stat().st_size
                    print(f"    {name}: {size:,} bytes")
                except OSError as e:
                    print(f"    {name}: {path} (stat failed: {e})")

    if not cached:
        print("\n" + model_prereq_help(model))
        return 1
    return 0


def cmd_podcast(args: argparse.Namespace) -> int:
    """Transcribe podcast episode(s) from RSS feed URL."""
    cfg = load_config(args.config)
    if args.model:
        cfg.model = args.model
    if args.language:
        cfg.language = args.language
    if args.output_mode:
        cfg.output_mode = OutputMode(args.output_mode)
    if args.output_dir:
        cfg.output_dir = Path(args.output_dir)
    if args.formats:
        cfg.formats = [f.strip() for f in args.formats.split(",")]

    if not args.rss_url and not args.guid:
        print("Provide --rss-url or --guid")
        return 2

    rss_url = args.rss_url
    if not rss_url:
        print("--guid requires --rss-url to fetch episodes")
        return 2

    counts = {"ok": 0, "skipped": 0, "failed": 0}
    for ep_guid in (args.guid or []):
        status = run_podcast_job(rss_url, cfg, force=args.force, episode_guid=ep_guid)
        counts[status] += 1

    if not args.guid:
        status = run_podcast_job(rss_url, cfg, force=args.force)
        counts[status] += 1

    print(f"Done: {counts['ok']} ok, {counts['skipped']} skipped, {counts['failed']} failed")
    return 1 if counts["failed"] else 0


def cmd_podcasts_add(args: argparse.Namespace) -> int:
    podcast_id = add_podcast(args.name, args.rss_url, podcast_index_id=args.podcast_index_id)
    print(f"Added podcast: {args.name}")
    print(f"ID: {podcast_id}")
    print(f"RSS: {args.rss_url}")
    if args.fetch:
        new_count, total_count = fetch_podcast_episodes(podcast_id, args.rss_url)
        print(f"Fetched {total_count} episodes ({new_count} new)")
    return 0


def cmd_podcasts_fetch(args: argparse.Namespace) -> int:
    podcasts = get_all_podcasts()
    if args.rss_url:
        podcast = next((p for p in podcasts if p["rss_url"] == args.rss_url), None)
        podcasts = [podcast] if podcast else []
        if not podcasts:
            print(f"Podcast not found: {args.rss_url}")
            return 1

    if not podcasts:
        print("No podcasts configured")
        return 0

    total_new = 0
    total_episodes = 0
    for podcast in podcasts:
        new_count, episode_count = fetch_podcast_episodes(podcast["id"], podcast["rss_url"])
        total_new += new_count
        total_episodes += episode_count
        print(f"{podcast['title']}: {new_count} new / {episode_count} total")

    print(f"Done: {total_new} new / {total_episodes} total")
    return 0


def cmd_podcasts_list(args: argparse.Namespace) -> int:
    podcasts = get_all_podcasts()
    if not podcasts:
        print("No podcasts configured")
        return 0
    for podcast in podcasts:
        print(f"{podcast['id']}\t{podcast['title']}\t{podcast['rss_url']}")
    return 0


def cmd_episodes_list(args: argparse.Namespace) -> int:
    if args.untranscribed:
        episodes = get_episodes_without_transcription()
    else:
        episodes = get_all_episodes()
    if args.podcast_id:
        from digg_transcriber.database import get_episodes_by_podcast

        episodes = get_episodes_by_podcast(args.podcast_id)
    if args.limit:
        episodes = episodes[: args.limit]
    if not episodes:
        print("No episodes found")
        return 0
    for episode in episodes:
        status = "transcribed" if episode.get("transcript_path") else "untranscribed"
        print(f"{episode['id']}\t{episode.get('podcast_title', '')}\t{episode['title']}\t{status}")
    return 0


def cmd_episodes_import_pod_transcriber(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    output_dir = Path(args.output_dir).expanduser() if args.output_dir else cfg.output_dir
    result = import_pod_transcriber_transcripts(
        Path(args.source).expanduser(),
        podcast_title=args.podcast_title,
        output_dir=output_dir,
        dry_run=args.dry_run,
    )
    mode = "Would import" if args.dry_run else "Imported"
    print(
        f"{mode} {result['imported']} episodes "
        f"from {result['podcasts']} podcasts "
        f"(missing transcript files: {result['missing']})"
    )
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    """Search Podcast Index for podcasts."""
    cfg = load_config(args.config)
    api_key = cfg.podcast_index_api_key
    api_secret = cfg.podcast_index_api_secret

    if not api_key or not api_secret:
        print("Podcast Index API credentials not configured.")
        print("Set in config file or environment:")
        print("  podcast_index_api_key: YOUR_KEY")
        print("  podcast_index_api_secret: YOUR_SECRET")
        return 2

    auth = get_client(api_key, api_secret)
    results = search_podcasts(args.query, auth, max_results=args.max)

    if not results:
        print("No results found")
        return 1

    for i, podcast in enumerate(results, 1):
        print(f"\n{i}. {podcast['title']}")
        print(f"   Author: {podcast.get('author', 'Unknown')}")
        print(f"   Feed: {podcast.get('rss_url', '')}")
        if podcast.get("description"):
            desc = podcast["description"][:200]
            print(f"   Description: {desc}...")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=CLI_NAME,
        description="Universal transcription tool for video and audio",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # init
    p_init = sub.add_parser("init", help="Create or update default config file")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing")
    p_init.add_argument("--update", action="store_true", help="Add missing config options")
    p_init.set_defaults(func=cmd_init)

    # check
    p_check = sub.add_parser("check", help="Check model cache status")
    p_check.add_argument("--model", "-m", default="medium", help="Model to check")
    p_check.set_defaults(func=cmd_check)

    # transcribe
    p_transcribe = sub.add_parser("transcribe", help="Transcribe files")
    p_transcribe.add_argument("paths", nargs="*", help="Input file(s) or directory")
    p_transcribe.add_argument("--config", "-c", type=Path, help="Config file path")
    p_transcribe.add_argument("--model", "-m", help="Whisper model")
    p_transcribe.add_argument("--language", "-l", help="Language code (or auto)")
    p_transcribe.add_argument("--output-mode", choices=["archive", "beside", "mirror", "flat"])
    p_transcribe.add_argument("--output-dir", "-o", help="Output directory")
    p_transcribe.add_argument("--formats", "-f", help="Comma-separated formats (vtt,txt)")
    p_transcribe.add_argument("--force", action="store_true", help="Overwrite existing")
    p_transcribe.add_argument("--recursive", "-r", action="store_true", default=True)
    p_transcribe.set_defaults(func=cmd_transcribe)

    # podcast
    p_podcast = sub.add_parser("podcast", help="Transcribe podcast episode from RSS")
    p_podcast.add_argument("--rss-url", help="RSS feed URL")
    p_podcast.add_argument("--guid", action="append", help="Episode GUID (repeatable)")
    p_podcast.add_argument("--config", "-c", type=Path, help="Config file path")
    p_podcast.add_argument("--model", "-m", help="Whisper model")
    p_podcast.add_argument("--language", "-l", help="Language code (or auto)")
    p_podcast.add_argument("--output-mode", choices=["archive", "beside", "mirror", "flat"])
    p_podcast.add_argument("--output-dir", "-o", help="Output directory")
    p_podcast.add_argument("--formats", "-f", help="Comma-separated formats (vtt,txt)")
    p_podcast.add_argument("--force", action="store_true", help="Overwrite existing")
    p_podcast.set_defaults(func=cmd_podcast)

    p_podcasts = sub.add_parser("podcasts", help="Manage podcast library")
    p_podcasts_sub = p_podcasts.add_subparsers(dest="podcasts_cmd", required=True)

    p_podcasts_add = p_podcasts_sub.add_parser("add", help="Add a podcast by RSS URL")
    p_podcasts_add.add_argument("--name", required=True, help="Podcast title")
    p_podcasts_add.add_argument("--rss-url", required=True, help="RSS feed URL")
    p_podcasts_add.add_argument("--podcast-index-id", type=int, help="Podcast Index ID")
    p_podcasts_add.add_argument("--fetch", action="store_true", help="Fetch episodes after adding")
    p_podcasts_add.set_defaults(func=cmd_podcasts_add)

    p_podcasts_fetch = p_podcasts_sub.add_parser("fetch", help="Fetch episodes for configured podcasts")
    p_podcasts_fetch.add_argument("--rss-url", help="Fetch only this RSS feed")
    p_podcasts_fetch.set_defaults(func=cmd_podcasts_fetch)

    p_podcasts_list = p_podcasts_sub.add_parser("list", help="List configured podcasts")
    p_podcasts_list.set_defaults(func=cmd_podcasts_list)

    p_episodes = sub.add_parser("episodes", help="Manage podcast episodes")
    p_episodes_sub = p_episodes.add_subparsers(dest="episodes_cmd", required=True)

    p_episodes_list = p_episodes_sub.add_parser("list", help="List episodes")
    p_episodes_list.add_argument("--podcast-id", type=int, help="Filter by podcast ID")
    p_episodes_list.add_argument("--untranscribed", action="store_true", help="Show only untranscribed episodes")
    p_episodes_list.add_argument("--limit", type=int, help="Maximum episodes to show")
    p_episodes_list.set_defaults(func=cmd_episodes_list)

    p_episodes_import = p_episodes_sub.add_parser(
        "import-pod-transcriber",
        help="Import transcribed episodes from pod-transcriber",
    )
    p_episodes_import.add_argument("source", help="pod-transcriber project root or transcripts folder")
    p_episodes_import.add_argument("--podcast-title", help="Only import this podcast title")
    p_episodes_import.add_argument("--output-dir", "-o", help="Destination transcript root")
    p_episodes_import.add_argument("--config", "-c", type=Path, help="Config file path")
    p_episodes_import.add_argument("--dry-run", action="store_true", help="Report without copying files")
    p_episodes_import.set_defaults(func=cmd_episodes_import_pod_transcriber)

    # search
    p_search = sub.add_parser("search", help="Search Podcast Index")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--config", "-c", type=Path, help="Config file path")
    p_search.add_argument("--max", type=int, default=10, help="Max results")
    p_search.set_defaults(func=cmd_search)

    # watch
    p_watch = sub.add_parser("watch", help="Watch folders for new files")
    p_watch.add_argument("--config", "-c", type=Path, help="Config file path")
    p_watch.add_argument("--force", action="store_true", help="Overwrite existing")
    p_watch.set_defaults(func=cmd_watch)

    # prereqs (alias for check)
    p_prereqs = sub.add_parser("prereqs", help="Check prerequisites")
    p_prereqs.add_argument("--model", "-m", help="Model to check")
    p_prereqs.add_argument("--config", "-c", type=Path, help="Config file path")
    p_prereqs.add_argument("--verbose", "-v", action="store_true")
    p_prereqs.set_defaults(func=cmd_check_prereqs)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())