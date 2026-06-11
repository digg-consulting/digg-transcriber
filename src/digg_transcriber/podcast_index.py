"""Podcast Index API client for podcast discovery."""

from __future__ import annotations

from typing import Any

from digg_transcriber.http_client import get_http_session, retry_call

_BASE_URL = "https://api.podcastindex.org/api/1.0"


def get_client(api_key: str, api_secret: str) -> dict[str, str]:
    return {"api_key": api_key, "api_secret": api_secret}


def _request(
    endpoint: str,
    auth: dict[str, str],
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    session = get_http_session()
    headers = {
        "X-Auth-Key": auth["api_key"],
        "X-Auth-Date": str(int(__import__("time").time())),
    }

    def _do():
        resp = session.get(
            f"{_BASE_URL}{endpoint}",
            headers=headers,
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    return retry_call(_do, attempts=3)


def search_podcasts(
    query: str,
    auth: dict[str, str],
    max_results: int = 10,
) -> list[dict]:
    result = _request("/search/byterm", auth, params={"q": query, "max": max_results})
    if result.get("status") != "true":
        return []
    feeds = result.get("feeds", [])
    return [
        {
            "id": feed.get("id"),
            "title": feed.get("title", "Unknown"),
            "description": feed.get("description", ""),
            "rss_url": feed.get("url", ""),
            "web_url": feed.get("link", ""),
            "image_url": feed.get("image", ""),
            "author": feed.get("author", ""),
            "categories": feed.get("categories", {}),
        }
        for feed in feeds
    ]


def get_podcast_by_id(
    feed_id: int,
    auth: dict[str, str],
) -> dict | None:
    result = _request("/podcasts/byfeedid", auth, params={"id": feed_id})
    if result.get("status") != "true":
        return None
    feed = result.get("feed", {})
    return {
        "id": feed.get("id"),
        "title": feed.get("title", "Unknown"),
        "description": feed.get("description", ""),
        "rss_url": feed.get("url", ""),
        "web_url": feed.get("link", ""),
        "image_url": feed.get("image", ""),
        "author": feed.get("author", ""),
    }


def get_episodes_by_feed_id(
    feed_id: int,
    auth: dict[str, str],
    max_results: int = 100,
) -> list[dict]:
    result = _request(
        "/episodes/byfeedid",
        auth,
        params={"id": feed_id, "max": max_results},
    )
    if result.get("status") != "true":
        return []
    items = result.get("items", [])
    return [
        {
            "guid": item.get("guid") or str(item.get("id", "")),
            "title": item.get("title", "Unknown"),
            "description": item.get("description", ""),
            "audio_url": item.get("enclosureUrl", ""),
            "published_at": _unix_to_datetime(item.get("datePublished")),
            "duration_seconds": item.get("duration"),
        }
        for item in items
        if item.get("enclosureUrl")
    ]


def _unix_to_datetime(timestamp: int | None) -> datetime | None:
    if timestamp is None:
        return None
    try:
        return datetime.utcfromtimestamp(timestamp)
    except (ValueError, OSError):
        return None