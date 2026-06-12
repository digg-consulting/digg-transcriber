import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from digg_transcriber.config import AppConfig, default_config_dict, load_config, write_default_config
from digg_transcriber.paths import OutputMode


class ConfigTests(unittest.TestCase):
    def test_default_config_has_expected_defaults(self):
        cfg = default_config_dict()

        self.assertEqual(cfg["model"], "medium")
        self.assertEqual(cfg["language"], "auto")
        self.assertEqual(cfg["output_mode"], "archive")
        self.assertEqual(cfg["formats"], ["vtt", "txt"])
        self.assertEqual(cfg["watch"]["debounce_seconds"], 2)
        self.assertEqual(cfg["watch"]["extensions"][0], ".mp4")

    def test_load_config_explicit_path_merges_values(self):
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            config_path.write_text(
                yaml.safe_dump({
                    "model": "tiny",
                    "language": "en",
                    "output_mode": "flat",
                    "output_dir": "~/Transcripts",
                    "formats": ["txt", "json"],
                    "watch": {
                        "paths": ["~/Media"],
                        "debounce_seconds": 4,
                        "extensions": ["mp4", ".wav"],
                    },
                }),
                encoding="utf-8",
            )

            cfg = load_config(config_path)

            self.assertEqual(cfg.model, "tiny")
            self.assertEqual(cfg.language, "en")
            self.assertEqual(cfg.output_mode, OutputMode.FLAT)
            self.assertEqual(cfg.output_dir, Path.home() / "Transcripts")
            self.assertEqual(cfg.formats, ["txt", "json"])
            self.assertEqual(cfg.watch_paths, [Path.home() / "Media"])
            self.assertEqual(cfg.watch_debounce_seconds, 4.0)
            self.assertEqual(cfg.watch_extensions, [".mp4", ".wav"])

    def test_load_config_handles_empty_file(self):
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            config_path.write_text("", encoding="utf-8")

            cfg = load_config(config_path)

            self.assertEqual(cfg, AppConfig())

    def test_write_default_config_creates_and_overwrites_with_force(self):
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"

            returned_path, created = write_default_config(config_path)
            again_path, created_again = write_default_config(config_path)
            forced_path, forced = write_default_config(config_path, force=True)

            self.assertEqual(returned_path, config_path)
            self.assertTrue(created)
            self.assertEqual(again_path, config_path)
            self.assertFalse(created_again)
            self.assertEqual(forced_path, config_path)
            self.assertTrue(forced)
            self.assertIn("model:", config_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
