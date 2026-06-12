import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from digg_transcriber.rss import fetch_episodes_from_rss, fetch_podcast_metadata_from_rss, fetch_podcast_title_from_rss, get_audio_url, parse_duration, parse_published_date


class RSSTests(unittest.TestCase):
    def test_parse_duration_accepts_seconds_and_hms(self):
        self.assertEqual(parse_duration("123"), 123)
        self.assertEqual(parse_duration("01:02:03"), 3723)
        self.assertEqual(parse_duration("bad"), None)
        self.assertEqual(parse_duration(""), None)

    def test_get_audio_url_prefers_audio_enclosures(self):
        entry = {
            "enclosures": [
                {"type": "image/jpeg", "url": "https://example.com/image.jpg"},
                {"type": "audio/mpeg", "href": "https://example.com/audio.mp3"},
            ],
            "links": [{"type": "audio/ogg", "href": "https://example.com/alternate.ogg"}],
            "media_content": [{"type": "audio/mp4", "url": "https://example.com/media.m4a"}],
        }

        self.assertEqual(get_audio_url(entry), "https://example.com/audio.mp3")

    def test_parse_published_date_uses_feedparser_tuple(self):
        entry = {"published_parsed": (2026, 6, 11, 12, 30, 45, 0, 0, 0)}

        self.assertEqual(parse_published_date(entry), datetime(2026, 6, 11, 12, 30, 45))
        self.assertEqual(parse_published_date({}), None)

    def test_fetch_episodes_from_rss_filters_entries_without_audio(self):
        feed = SimpleNamespace(
            bozo=False,
            feed={"title": "Example Podcast"},
            entries=[
                {
                    "id": "guid-1",
                    "title": "Episode One",
                    "summary": "Summary",
                    "enclosures": [{"type": "audio/mpeg", "href": "https://example.com/one.mp3"}],
                    "itunes_duration": "01:02:03",
                    "published_parsed": (2026, 6, 11, 1, 2, 3, 0, 0, 0),
                },
                {"id": "guid-2", "title": "No Audio", "enclosures": []},
            ],
        )

        with (
            patch("digg_transcriber.http_client.get_http_session") as get_session,
            patch("feedparser.parse", return_value=feed),
        ):
            response = SimpleNamespace(content=b"feed", raise_for_status=lambda: None)
            get_session.return_value.get.return_value = response

            episodes = fetch_episodes_from_rss("https://example.com/feed.xml")

        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0]["guid"], "guid-1")
        self.assertEqual(episodes[0]["title"], "Episode One")
        self.assertEqual(episodes[0]["description"], "Summary")
        self.assertEqual(episodes[0]["audio_url"], "https://example.com/one.mp3")
        self.assertEqual(episodes[0]["duration_seconds"], 3723)
        self.assertEqual(episodes[0]["published_at"], datetime(2026, 6, 11, 1, 2, 3))
        get_session.return_value.get.assert_called_once_with("https://example.com/feed.xml", timeout=30)

    def test_fetch_podcast_metadata_includes_feed_title(self):
        feed = SimpleNamespace(bozo=False, feed={"title": "Example Podcast"}, entries=[])

        with (
            patch("digg_transcriber.http_client.get_http_session") as get_session,
            patch("feedparser.parse", return_value=feed),
        ):
            response = SimpleNamespace(content=b"feed", raise_for_status=lambda: None)
            get_session.return_value.get.return_value = response

            metadata = fetch_podcast_metadata_from_rss("https://example.com/feed.xml")
            self.assertEqual(fetch_podcast_title_from_rss("https://example.com/feed.xml"), "Example Podcast")

        self.assertEqual(metadata["title"], "Example Podcast")
        self.assertEqual(metadata["episodes"], [])

    def test_fetch_episodes_from_rss_returns_empty_when_bozo_without_entries(self):
        feed = SimpleNamespace(bozo=True, entries=[])

        with (
            patch("digg_transcriber.http_client.get_http_session") as get_session,
            patch("feedparser.parse", return_value=feed),
        ):
            response = SimpleNamespace(content=b"bad", raise_for_status=lambda: None)
            get_session.return_value.get.return_value = response

            self.assertEqual(fetch_episodes_from_rss("https://example.com/feed.xml"), [])


if __name__ == "__main__":
    unittest.main()
