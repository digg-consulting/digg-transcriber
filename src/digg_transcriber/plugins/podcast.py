"""Podcast RSS source plugin for digg-transcriber."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from digg_transcriber.rss import fetch_episodes_from_rss


class PodcastSource:
    def __init__(self, rss_url: str, episode_guid: Optional[str] = None):
        self.rss_url = rss_url
        self.episode_guid = episode_guid
        self._episodes: list[dict] | None = None
        self._episode: dict | None = None

    def get_id(self) -> str:
        if self._episode is None:
            self._load_episodes()
        if self._episode:
            return self._episode["guid"]
        return f"podcast:{self.rss_url}"

    def get_title(self) -> Optional[str]:
        if self._episode is None:
            self._load_episodes()
        if self._episode:
            return self._episode["title"]
        return None

    def get_audio_url(self) -> Optional[str]:
        if self._episode is None:
            self._load_episodes()
        if self._episode:
            return self._episode["audio_url"]
        return None

    def get_description(self) -> Optional[str]:
        if self._episode is None:
            self._load_episodes()
        if self._episode:
            return self._episode.get("description")
        return None

    def _load_episodes(self) -> None:
        if self._episodes is None:
            self._episodes = fetch_episodes_from_rss(self.rss_url)
        if self.episode_guid:
            for ep in self._episodes:
                if ep["guid"] == self.episode_guid:
                    self._episode = ep
                    return
        if self._episodes:
            self._episode = self._episodes[-1]

    def get_episodes(self) -> list[dict]:
        if self._episodes is None:
            self._episodes = fetch_episodes_from_rss(self.rss_url)
        return self._episodes