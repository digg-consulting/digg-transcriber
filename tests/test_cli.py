import contextlib
import io
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import yaml

from digg_transcriber.cli import main
from digg_transcriber.config import load_config


class CliTests(unittest.TestCase):
    def test_init_accepts_force_argument(self):
        with (
            patch("digg_transcriber.cli.write_default_config", return_value=(Path("config.yaml"), True)) as write_config,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            exit_code = main(["init", "--force"])

        self.assertEqual(exit_code, 0)
        write_config.assert_called_once()
        self.assertTrue(write_config.call_args.kwargs["force"])

    def test_init_prompts_to_update_existing_config(self):
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            config_path.write_text(yaml.safe_dump({"model": "tiny"}), encoding="utf-8")
            output = io.StringIO()

            with (
                patch.dict(os.environ, {"DIGG_TRANSCRIBER_CONFIG": str(config_path)}),
                patch("digg_transcriber.cli._confirm", return_value=True),
                contextlib.redirect_stdout(output),
            ):
                exit_code = main(["init"])

            self.assertEqual(exit_code, 0)
            self.assertIn("Missing config options:", output.getvalue())
            self.assertIn("podcast.podcast_index_api_key", output.getvalue())
            self.assertEqual(load_config(config_path).model, "tiny")
            self.assertEqual(load_config(config_path).podcast_index_api_key, "")


if __name__ == "__main__":
    unittest.main()
