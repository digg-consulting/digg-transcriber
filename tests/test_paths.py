import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from digg_transcriber.paths import OutputMode, archive_dir_for, move_source_to_archive, output_paths_for, should_skip


class OutputPathTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_output_paths_for_supported_modes(self):
        source = self.root / "shows" / "episode.mp4"
        source.parent.mkdir()
        source.touch()
        output_dir = self.root / "transcripts"

        beside = output_paths_for(source, output_mode=OutputMode.BESIDE, output_dir=output_dir, formats=["vtt", "txt"])
        self.assertEqual(beside["vtt"], source.parent / "episode.vtt")
        self.assertEqual(beside["txt"], source.parent / "episode.txt")

        flat = output_paths_for(source, output_mode=OutputMode.FLAT, output_dir=output_dir, formats=["vtt"])
        self.assertEqual(flat["vtt"], output_dir / "episode.vtt")

        mirror = output_paths_for(
            source,
            output_mode=OutputMode.MIRROR,
            output_dir=output_dir,
            formats=["vtt"],
            mirror_root=self.root,
        )
        self.assertEqual(mirror["vtt"], output_dir / "shows" / "episode.vtt")

        archive = output_paths_for(source, output_mode=OutputMode.ARCHIVE, output_dir=output_dir, formats=["vtt"])
        self.assertEqual(archive["vtt"].resolve(), (output_dir / "episode" / "episode.vtt").resolve())

    def test_archive_dir_avoids_existing_folder(self):
        source = self.root / "episode.mp4"
        source.touch()
        output_dir = self.root / "transcripts"
        (output_dir / "episode").mkdir(parents=True)

        self.assertEqual(archive_dir_for(source, output_dir).resolve(), (output_dir / "episode-2").resolve())

    def test_mirror_requires_mirror_root(self):
        source = self.root / "episode.mp4"
        source.touch()
        with self.assertRaises(ValueError):
            output_paths_for(
                source,
                output_mode=OutputMode.MIRROR,
                output_dir=self.root / "transcripts",
                formats=["vtt"],
            )

    def test_should_skip_archive_requires_archived_source(self):
        source = self.root / "episode.mp4"
        source.touch()
        output_dir = self.root / "transcripts"
        paths = output_paths_for(source, output_mode=OutputMode.ARCHIVE, output_dir=output_dir, formats=["vtt", "txt"])

        self.assertFalse(should_skip(paths, formats=["vtt", "txt"], source_path=source, output_mode=OutputMode.ARCHIVE))

        paths["vtt"].parent.mkdir(parents=True, exist_ok=True)
        paths["vtt"].write_text("captions", encoding="utf-8")
        paths["txt"].write_text("text", encoding="utf-8")
        self.assertFalse(should_skip(paths, formats=["vtt", "txt"], source_path=source, output_mode=OutputMode.ARCHIVE))

        (paths["vtt"].parent / source.name).touch()
        self.assertTrue(should_skip(paths, formats=["vtt", "txt"], source_path=source, output_mode=OutputMode.ARCHIVE))
        self.assertFalse(should_skip(paths, formats=["vtt", "txt"], force=True, source_path=source, output_mode=OutputMode.ARCHIVE))

    def test_move_source_to_archive_moves_input_next_to_outputs(self):
        source = self.root / "episode.mp4"
        source.write_text("media", encoding="utf-8")
        output_dir = self.root / "transcripts"
        paths = output_paths_for(source, output_mode=OutputMode.ARCHIVE, output_dir=output_dir, formats=["txt"])

        dest = move_source_to_archive(source, paths)

        self.assertFalse(source.exists())
        self.assertEqual(dest.resolve(), (output_dir / "episode" / "episode.mp4").resolve())
        self.assertTrue(dest.exists())


if __name__ == "__main__":
    unittest.main()
