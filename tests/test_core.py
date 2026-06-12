import logging
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from digg_transcriber.config import AppConfig
from digg_transcriber.core import detect_source_type, discover_sources, run_job, run_podcast_job
from digg_transcriber.models import Segment, TranscriptResult
from digg_transcriber.paths import OutputMode


class FakePlugin:
    instances = []

    def __init__(self):
        self.prepared = []
        self.cleaned = []
        self.source_deleted = []
        FakePlugin.instances.append(self)

    def get_id(self, source):
        return f"id:{source.name}"

    def get_title(self, source):
        return source.stem

    def prepare_audio(self, source):
        self.prepared.append(source)
        return source

    def cleanup(self, audio_path):
        self.cleaned.append(audio_path)

    def cleanup_source(self, source):
        self.source_deleted.append(source)


class CoreTests(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.plugin = FakePlugin()

    def tearDown(self):
        logging.disable(logging.NOTSET)
        self.tmp.cleanup()

    def test_detect_source_type_and_discover_sources(self):
        source_dir = self.root / "media"
        nested = source_dir / "nested"
        nested.mkdir(parents=True)
        video = source_dir / "clip.mp4"
        audio = nested / "clip.wav"
        text = source_dir / "notes.txt"
        video.touch()
        audio.touch()
        text.touch()

        self.assertEqual(detect_source_type(video), "video")
        self.assertEqual(detect_source_type(audio), "local_audio")
        self.assertEqual(discover_sources(source_dir, {".mp4", ".wav"}, recursive=True), [("video", video), ("local_audio", audio)])
        self.assertEqual(discover_sources(source_dir, {".mp4", ".wav"}, recursive=False), [("video", video)])
        self.assertEqual(discover_sources(video, {".mp4"}, recursive=True), [("video", video)])
        self.assertEqual(discover_sources(text, {".mp4"}, recursive=True), [])

    def test_run_job_writes_outputs_and_records_processing(self):
        source = self.root / "episode.wav"
        source.touch()
        cfg = AppConfig(output_dir=self.root / "out", output_mode=OutputMode.FLAT, formats=["txt"], model="tiny", language="en")
        output_path = self.root / "out" / "episode.txt"

        with (
            patch("digg_transcriber.core.SOURCE_PLUGINS", {"local_audio": FakePlugin}),
            patch("digg_transcriber.core.get_transcriber", return_value=lambda _: TranscriptResult("Hello", [Segment(0.0, 1.0, "Hello")])),
            patch("digg_transcriber.core.mark_processed") as mark_processed,
        ):
            status = run_job(source, cfg)

        plugin = FakePlugin.instances[-1]
        self.assertEqual(status, "ok")
        self.assertEqual(output_path.read_text(encoding="utf-8"), "Hello\n")
        self.assertEqual(plugin.prepared, [source])
        self.assertEqual(plugin.cleaned, [source])
        mark_processed.assert_called_once_with("id:episode.wav", "local_audio", "episode", output_path)

    def test_run_job_returns_failed_when_transcription_raises(self):
        source = self.root / "episode.wav"
        source.touch()
        cfg = AppConfig(output_dir=self.root / "out", output_mode=OutputMode.FLAT, formats=["txt"])

        with (
            patch("digg_transcriber.core.SOURCE_PLUGINS", {"local_audio": FakePlugin}),
            patch("digg_transcriber.core.get_transcriber", side_effect=RuntimeError("boom")),
            patch("digg_transcriber.core.mark_processed") as mark_processed,
            patch("digg_transcriber.core.logger.exception") as logger_exception,
        ):
            status = run_job(source, cfg)

        logger_exception.assert_called_once()

        self.assertEqual(status, "failed")
        self.assertFalse((self.root / "out").exists())
        mark_processed.assert_not_called()

    def test_run_job_skips_when_outputs_already_exist(self):
        source = self.root / "episode.wav"
        source.touch()
        cfg = AppConfig(output_dir=self.root / "out", output_mode=OutputMode.FLAT, formats=["txt"])
        (self.root / "out").mkdir()
        (self.root / "out" / "episode.txt").write_text("already", encoding="utf-8")

        with (
            patch("digg_transcriber.core.SOURCE_PLUGINS", {"local_audio": FakePlugin}),
            patch("digg_transcriber.core.get_transcriber") as get_transcriber,
        ):
            status = run_job(source, cfg)

        plugin = FakePlugin.instances[-1]
        self.assertEqual(status, "skipped")
        get_transcriber.assert_not_called()
        self.assertEqual(plugin.prepared, [])

    def test_run_podcast_job_downloads_transcribes_and_cleans_temp_audio(self):
        cfg = AppConfig(output_dir=self.root / "out", output_mode=OutputMode.FLAT, formats=["txt"])

        with (
            patch("digg_transcriber.core._download_audio", return_value=self.root / "episode.mp3"),
            patch("digg_transcriber.core.get_transcriber", return_value=lambda _: TranscriptResult("Podcast", [Segment(0.0, 1.0, "Podcast")])),
            patch("digg_transcriber.core.mark_processed") as mark_processed,
            patch("digg_transcriber.core.mark_transcription") as mark_transcription,
            patch("digg_transcriber.plugins.podcast.PodcastSource") as podcast_source_cls,
        ):
            podcast_source_cls.return_value.get_id.return_value = "podcast-id"
            podcast_source_cls.return_value.get_podcast_title.return_value = "Example / Podcast"
            podcast_source_cls.return_value.get_title.return_value = "Episode / Title"
            podcast_source_cls.return_value.get_audio_url.return_value = "https://example.com/episode.mp3"

            status = run_podcast_job("https://example.com/feed.xml", cfg)

        self.assertEqual(status, "ok")
        self.assertFalse((self.root / "episode.mp3").exists())
        transcript_path = self.root / "out" / "Example _ Podcast" / "Episode _ Title" / "Episode _ Title.txt"
        self.assertEqual(transcript_path.read_text(encoding="utf-8"), "Podcast\n")
        mark_transcription.assert_called_once()
        self.assertEqual(mark_transcription.call_args.args[1], transcript_path)
        mark_processed.assert_called_once_with("podcast-id", "podcast", "Episode / Title", transcript_path)


if __name__ == "__main__":
    unittest.main()
