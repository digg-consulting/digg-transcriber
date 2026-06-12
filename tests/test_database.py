import os
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from digg_transcriber.database import (
    get_episode_by_guid,
    get_podcast_by_rss_url,
    get_transcription_by_guid,
    import_pod_transcriber_transcripts,
)


class DatabasePodcastTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.env = {
            "XDG_CACHE_HOME": str(Path(self.tmp.name) / "cache"),
            "HOME": str(Path(self.tmp.name) / "home"),
        }
        self._cm = None

    def tearDown(self):
        if self._cm:
            self._cm.__exit__(None, None, None)
        self.tmp.cleanup()

    def _patch_env(self):
        self._cm = patch.dict(os.environ, self.env)
        self._cm.__enter__()

    def test_import_pod_transcriber_transcripts_copies_and_marks_transcripts(self):
        self._patch_env()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            pod_root = root / "pod-transcriber"
            (pod_root / "data").mkdir(parents=True)
            (pod_root / "transcripts" / "Example_Podcast").mkdir(parents=True)
            db_path = pod_root / "data" / "podcasts.db"
            source_txt = pod_root / "transcripts" / "Example_Podcast" / "2026-06-01_Episode_One.txt"
            source_txt.write_text("Transcript text\n", encoding="utf-8")

            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE podcasts (id INTEGER PRIMARY KEY, title TEXT, rss_url TEXT)")
            conn.execute(
                "CREATE TABLE episodes (id INTEGER PRIMARY KEY, podcast_id INTEGER, guid TEXT, title TEXT, "
                "description TEXT, audio_url TEXT, published_at TEXT, duration_seconds INTEGER)"
            )
            conn.execute("CREATE TABLE transcriptions (id INTEGER PRIMARY KEY, episode_id INTEGER, transcript_file TEXT)")
            conn.execute(
                "INSERT INTO podcasts (id, title, rss_url) VALUES (1, 'Example Podcast', 'https://example.com/feed.xml')"
            )
            conn.execute(
                "INSERT INTO episodes (id, podcast_id, guid, title, description, audio_url, published_at, duration_seconds) "
                "VALUES (1, 1, 'guid-1', 'Episode One', 'Description', 'https://example.com/audio.mp3', '2026-06-01', 300)"
            )
            conn.execute(
                "INSERT INTO transcriptions (id, episode_id, transcript_file) "
                "VALUES (1, 1, 'Example_Podcast/2026-06-01_Episode_One.txt')"
            )
            conn.commit()
            conn.close()

            output_dir = Path(self.tmp.name) / "Transcripts"
            result = import_pod_transcriber_transcripts(
                pod_root,
                output_dir=output_dir,
            )

            self.assertEqual(result["imported"], 1)
            self.assertEqual(result["missing"], 0)
            self.assertEqual(result["podcasts"], 1)
            podcast = get_podcast_by_rss_url("https://example.com/feed.xml")
            self.assertIsNotNone(podcast)
            episode = get_episode_by_guid("guid-1")
            self.assertIsNotNone(episode)
            self.assertEqual(episode["title"], "Episode One")
            transcript = get_transcription_by_guid("guid-1")
            self.assertIsNotNone(transcript)
            destination = Path(transcript["transcript_path"])
            self.assertEqual(destination, output_dir / "Example Podcast" / "Episode One" / "Episode One.txt")
            self.assertEqual(destination.read_text(encoding="utf-8"), "Transcript text\n")


if __name__ == "__main__":
    unittest.main()
