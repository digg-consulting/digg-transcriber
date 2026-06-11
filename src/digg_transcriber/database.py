"""SQLite database for tracking processed sources."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional


def get_db_path() -> Path:
    from digg_transcriber.xdg import dt_cache_dir
    db_dir = dt_cache_dir()
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "processed.db"


@contextmanager
def get_db():
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        _ensure_schema(conn)
        yield conn
    finally:
        conn.close()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS processed (
            source_id TEXT PRIMARY KEY,
            source_type TEXT NOT NULL,
            title TEXT,
            output_path TEXT NOT NULL,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def mark_processed(
    source_id: str,
    source_type: str,
    title: Optional[str],
    output_path: Path,
) -> None:
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO processed (source_id, source_type, title, output_path)
            VALUES (?, ?, ?, ?)
            """,
            (source_id, source_type, title, str(output_path)),
        )
        conn.commit()


def is_processed(source_id: str) -> bool:
    with get_db() as conn:
        cur = conn.execute(
            "SELECT 1 FROM processed WHERE source_id = ?",
            (source_id,),
        )
        return cur.fetchone() is not None


def get_processed_path(source_id: str) -> Optional[Path]:
    with get_db() as conn:
        cur = conn.execute(
            "SELECT output_path FROM processed WHERE source_id = ?",
            (source_id,),
        )
        row = cur.fetchone()
        if row:
            return Path(row["output_path"])
        return None


__all__ = [
    "get_db_path",
    "get_db",
    "mark_processed",
    "is_processed",
    "get_processed_path",
]