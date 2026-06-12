"""RSS feed parsing and episode extraction for podcast sources."""

from __future__ import annotations

import calendar
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Optional


def parse_duration(duration_str: Optional[str]) -> Optional[int]:
    if not duration_str:
        return None
    duration_str = duration_str.strip()
    if ":" in duration_str:
        parts = list(reversed(duration_str.split(":")))
        seconds = 0
        multiplier = 1
        for part in parts:
            seconds += int(part) * multiplier
            multiplier *= 60
        return seconds
    try:
        return int(duration_str)
    except ValueError:
        return None


def parse_published_date(entry: dict) -> Optional[datetime]:
    published = entry.get("published_parsed")
    if published is None:
        return None
    try:
        return datetime(*published[:6])
    except (TypeError, ValueError):
        return None


def get_audio_url(entry: dict) -> Optional[str]:
    for enclosure in entry.get("enclosures", []):
        enc_type = enclosure.get("type", "")
        if enc_type.startswith("audio/") or enc_type == "":
            url = enclosure.get("href") or enclosure.get("url")
            if url:
                return url
    for link in entry.get("links", []):
        if link.get("type", "").startswith("audio/"):
            return link.get("href")
    for content in entry.get("media_content", []):
        if content.get("type", "").startswith("audio/"):
            url = content.get("url") or content.get("href")
            if url:
                return url
    return None


def _fetch_feed(rss_url: str):
    import feedparser  # lazy import
    from digg_transcriber.http_client import get_http_session

    session = get_http_session()
    response = session.get(rss_url, timeout=30)
    response.raise_for_status()
    return feedparser.parse(response.content)


def _episodes_from_feed(feed) -> list[dict]:
    if feed.bozo and not feed.entries:
        return []

    episodes = []
    for entry in feed.entries:
        audio_url = get_audio_url(entry)
        if not audio_url:
            continue

        guid = entry.get("id") or entry.get("guid") or audio_url
        title = entry.get("title", "Unknown")
        description = entry.get("summary") or entry.get("description") or ""
        if hasattr(description, "strip"):
            description = description.strip()

        duration_seconds = parse_duration(
            entry.get("itunes_duration") or entry.get("itunes:duration")
        )

        published_at = parse_published_date(entry)

        episodes.append({
            "guid": guid,
            "title": title,
            "description": description,
            "audio_url": audio_url,
            "published_at": published_at,
            "duration_seconds": duration_seconds,
        })

    return episodes


def fetch_podcast_metadata_from_rss(rss_url: str) -> dict:
    feed = _fetch_feed(rss_url)
    title = getattr(feed, "feed", {}).get("title", "")
    return {
        "title": str(title).strip(),
        "episodes": _episodes_from_feed(feed),
    }


def fetch_podcast_title_from_rss(rss_url: str) -> str:
    return fetch_podcast_metadata_from_rss(rss_url)["title"]


def fetch_episodes_from_rss(rss_url: str) -> list[dict]:
    return fetch_podcast_metadata_from_rss(rss_url)["episodes"]
