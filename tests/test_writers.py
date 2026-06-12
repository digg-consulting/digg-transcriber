import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from digg_transcriber.models import Segment
from digg_transcriber.writers import format_full_text, format_srt, format_vtt, write_formats


class WriterTests(unittest.TestCase):
    def test_format_full_text_includes_speakers(self):
        segments = [
            Segment(0.0, 1.0, "  Hello  ", "Host"),
            Segment(1.0, 2.0, "World", None),
            Segment(2.0, 3.0, "   ", "Host"),
        ]

        self.assertEqual(format_full_text(segments), "Host: Hello\n\nWorld\n")

    def test_format_srt_numbers_and_formats_times(self):
        segments = [Segment(1.5, 2.75, "One", "Host")]

        self.assertEqual(
            format_srt(segments),
            "1\n00:00:01,500 --> 00:00:02,750\nHost: One\n",
        )

    def test_format_vtt_uses_dot_time_separator(self):
        segments = [Segment(1.5, 2.75, "One", "Host")]

        self.assertEqual(
            format_vtt(segments),
            "WEBVTT\n\n00:00:01.500 --> 00:00:02.750\nHost: One\n",
        )

    def test_write_formats_creates_all_requested_outputs(self):
        with TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            segments = [Segment(0.0, 1.0, "Hello", "Host")]
            paths = {fmt: output_dir / f"episode.{fmt}" for fmt in ["txt", "srt", "vtt", "json"]}

            write_formats("ignored", segments, paths, formats=list(paths))

            self.assertEqual((output_dir / "episode.txt").read_text(encoding="utf-8"), "Host: Hello\n")
            self.assertIn("00:00:00,000 --> 00:00:01,000", (output_dir / "episode.srt").read_text(encoding="utf-8"))
            self.assertIn("WEBVTT", (output_dir / "episode.vtt").read_text(encoding="utf-8"))
            payload = json.loads((output_dir / "episode.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["text"], "Host: Hello")
            self.assertEqual(payload["segments"][0]["speaker"], "Host")

    def test_write_formats_rejects_unknown_format(self):
        with self.assertRaises(ValueError):
            write_formats("", [], { "bad": Path("episode.bad") }, formats=["bad"])


if __name__ == "__main__":
    unittest.main()
