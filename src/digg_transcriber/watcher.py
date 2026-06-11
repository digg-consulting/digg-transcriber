"""Watch mode for digg-transcriber using watchdog."""

import logging
import queue
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from digg_transcriber.config import AppConfig
from digg_transcriber.core import run_job
from digg_transcriber.paths import OutputMode

logger = logging.getLogger(__name__)


class StableFileHandler(FileSystemEventHandler):
    def __init__(
        self,
        job_queue: queue.Queue[Path],
        extensions: set[str],
        debounce_seconds: float,
    ):
        self._queue = job_queue
        self._extensions = extensions
        self._debounce = debounce_seconds
        self._pending: dict[str, float] = {}

    def on_created(self, event):
        if event.is_directory:
            return
        self._schedule(Path(event.src_path))

    def on_modified(self, event):
        if event.is_directory:
            return
        self._schedule(Path(event.src_path))

    def _schedule(self, path: Path) -> None:
        if path.suffix.lower() not in self._extensions:
            return
        self._pending[str(path)] = time.time()

    def flush_ready(self) -> None:
        now = time.time()
        ready = [
            p for p, ts in list(self._pending.items()) if now - ts >= self._debounce
        ]
        for p in ready:
            del self._pending[p]
            self._queue.put(Path(p))


def run_watch(cfg: AppConfig, *, force: bool = False) -> int:
    if not cfg.watch_paths:
        logger.error("no watch.paths configured; run digg-transcriber init")
        return 2

    job_queue: queue.Queue[Path] = queue.Queue()
    extensions = {
        e.lower() if e.startswith(".") else f".{e.lower()}"
        for e in cfg.watch_extensions
    }
    handler = StableFileHandler(job_queue, extensions, cfg.watch_debounce_seconds)
    observer = Observer()
    scheduled = False

    for watch_path in cfg.watch_paths:
        if watch_path.exists():
            observer.schedule(handler, str(watch_path), recursive=True)
            logger.info("watching %s", watch_path)
            scheduled = True

    if not scheduled:
        logger.error("no valid watch paths exist")
        return 2

    observer.start()
    stop = threading.Event()

    exclude_under = (
        cfg.output_dir.resolve()
        if cfg.output_mode == OutputMode.ARCHIVE
        else None
    )

    def worker():
        while not stop.is_set():
            try:
                source = job_queue.get(timeout=0.5)
                if exclude_under and _is_under(source, exclude_under):
                    continue
                run_job(source, cfg, force=force)
            except queue.Empty:
                continue

    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()

    try:
        while True:
            handler.flush_ready()
            time.sleep(0.5)
    except KeyboardInterrupt:
        logger.info("stopping watch")
        stop.set()
        observer.stop()
    observer.join()
    return 0


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


__all__ = ["run_watch", "StableFileHandler"]