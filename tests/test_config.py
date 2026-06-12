import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from digg_transcriber.config import AppConfig, config_update_needed, default_config_dict, load_config, update_config, write_default_config
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

    def test_config_update_needed_finds_missing_nested_options(self):
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            config_path.write_text(
                yaml.safe_dump({
                    "model": "tiny",
                    "watch": {
                        "paths": ["~/Media"],
                    },
                }),
                encoding="utf-8",
            )

            self.assertEqual(
                config_update_needed(config_path),
                [
                    "language",
                    "output_mode",
                    "output_dir",
                    "formats",
                    "watch.debounce_seconds",
                    "watch.extensions",
                    "podcast.podcast_index_api_key",
                    "podcast.podcast_index_api_secret",
                ],
            )

    def test_update_config_appends_only_missing_options(self):
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            config_path.write_text(
                yaml.safe_dump({
                    "model": "tiny",
                    "watch": {
                        "paths": ["~/Media"],
                    },
                }),
                encoding="utf-8",
            )

            self.assertTrue(update_config(config_path))
            cfg = load_config(config_path)

            self.assertEqual(cfg.model, "tiny")
            self.assertEqual(cfg.watch_paths, [Path.home() / "Media"])
            self.assertEqual(cfg.language, "auto")
            self.assertEqual(cfg.podcast_index_api_key, "")
            self.assertEqual(cfg.podcast_index_api_secret, "")
            self.assertEqual(config_update_needed(config_path), [])

    def test_update_config_is_idempotent(self):
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            config_path.write_text(yaml.safe_dump(default_config_dict()), encoding="utf-8")

            self.assertFalse(update_config(config_path))
            self.assertEqual(config_update_needed(config_path), [])


if __name__ == "__main__":
    unittest.main()
