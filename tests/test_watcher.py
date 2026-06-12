import time
import unittest
from pathlib import Path
from queue import Queue
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from digg_transcriber.watcher import StableFileHandler


class WatcherTests(unittest.TestCase):
    def test_handler_queues_ready_files_after_debounce(self):
        with TemporaryDirectory() as tmp:
            media = Path(tmp) / "media.mp4"
            notes = Path(tmp) / "notes.txt"
            queue = Queue()
            handler = StableFileHandler(queue, {".mp4"}, debounce_seconds=0.1)

            handler.on_created(SimpleNamespace(is_directory=False, src_path=str(media)))
            handler.on_modified(SimpleNamespace(is_directory=False, src_path=str(notes)))
            handler.flush_ready()

            self.assertTrue(queue.empty())

            time.sleep(0.12)
            handler.flush_ready()

            self.assertEqual(queue.get(), media)
            self.assertTrue(queue.empty())


if __name__ == "__main__":
    unittest.main()
