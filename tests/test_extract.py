import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
import wave

from digg_transcriber.extract import wav_duration_seconds


class ExtractTests(unittest.TestCase):
    def test_wav_duration_seconds_reads_valid_wav(self):
        with TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "one_second.wav"
            with wave.open(str(wav_path), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                wav.writeframes(b"\x00\x00" * 16000)

            self.assertEqual(wav_duration_seconds(wav_path), 1.0)

    def test_wav_duration_seconds_returns_none_for_invalid_file(self):
        with TemporaryDirectory() as tmp:
            self.assertIsNone(wav_duration_seconds(Path(tmp) / "missing.wav"))


if __name__ == "__main__":
    unittest.main()
