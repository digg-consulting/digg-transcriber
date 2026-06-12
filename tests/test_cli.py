import contextlib
import io
import unittest
from pathlib import Path
from unittest.mock import patch

from digg_transcriber.cli import main


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


if __name__ == "__main__":
    unittest.main()
