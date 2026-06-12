"""SQLite database for tracking processed sources and podcast libraries."""

from __future__ import annotations

import shutil
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
    _ensure_podcast_schema(conn)
    conn.commit()


def _ensure_podcast_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS podcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            podcast_index_id INTEGER UNIQUE,
            title TEXT NOT NULL,
            rss_url TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_fetched TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            podcast_id INTEGER NOT NULL,
            guid TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            description TEXT,
            audio_url TEXT,
            published_at TIMESTAMP,
            duration_seconds INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (podcast_id) REFERENCES podcasts (id) ON DELETE CASCADE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transcriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            episode_id INTEGER NOT NULL UNIQUE,
            transcript_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (episode_id) REFERENCES episodes (id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_podcasts_rss_url ON podcasts (rss_url)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_episodes_podcast_id ON episodes (podcast_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_episodes_guid ON episodes (guid)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_transcriptions_episode_id ON transcriptions (episode_id)")


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


def add_podcast(
    title: str,
    rss_url: str,
    *,
    podcast_index_id: Optional[int] = None,
) -> int:
    with get_db() as conn:
        row = conn.execute("SELECT id FROM podcasts WHERE rss_url = ?", (rss_url,)).fetchone()
        if row:
            conn.execute(
                "UPDATE podcasts SET title = ? WHERE id = ?",
                (title, row["id"]),
            )
            conn.commit()
            return int(row["id"])

        cur = conn.execute(
            """
            INSERT INTO podcasts (podcast_index_id, title, rss_url)
            VALUES (?, ?, ?)
            """,
            (podcast_index_id, title, rss_url),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_podcast_by_rss_url(rss_url: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM podcasts WHERE rss_url = ?", (rss_url,)).fetchone()
        return dict(row) if row else None


def get_podcast_by_title(title: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM podcasts WHERE title = ?", (title,)).fetchone()
        return dict(row) if row else None


def get_all_podcasts() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM podcasts ORDER BY title").fetchall()
        return [dict(row) for row in rows]


def update_podcast_last_fetched(podcast_id: int) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE podcasts SET last_fetched = CURRENT_TIMESTAMP WHERE id = ?",
            (podcast_id,),
        )
        conn.commit()


def upsert_episode(
    podcast_id: int,
    guid: str,
    title: str,
    *,
    description: Optional[str] = None,
    audio_url: Optional[str] = None,
    published_at=None,
    duration_seconds: Optional[int] = None,
) -> int:
    with get_db() as conn:
        row = conn.execute("SELECT id FROM episodes WHERE guid = ?", (guid,)).fetchone()
        if row:
            episode_id = int(row["id"])
            conn.execute(
                """
                UPDATE episodes
                   SET podcast_id = ?, title = ?, description = ?, audio_url = ?,
                       published_at = ?, duration_seconds = ?
                 WHERE id = ?
                """,
                (
                    podcast_id,
                    title,
                    description,
                    audio_url,
                    published_at,
                    duration_seconds,
                    episode_id,
                ),
            )
            conn.commit()
            return episode_id

        cur = conn.execute(
            """
            INSERT INTO episodes (
                podcast_id, guid, title, description, audio_url, published_at, duration_seconds
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                podcast_id,
                guid,
                title,
                description,
                audio_url,
                published_at,
                duration_seconds,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_episode_by_guid(guid: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM episodes WHERE guid = ?", (guid,)).fetchone()
        return dict(row) if row else None


def get_episode_by_id(episode_id: int) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,)).fetchone()
        return dict(row) if row else None


def get_episodes_by_podcast(podcast_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT e.*, t.transcript_path
            FROM episodes e
            LEFT JOIN transcriptions t ON t.episode_id = e.id
            WHERE e.podcast_id = ?
            ORDER BY e.published_at DESC, e.title
            """,
            (podcast_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_all_episodes() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT e.*, p.title AS podcast_title, t.transcript_path
            FROM episodes e
            JOIN podcasts p ON p.id = e.podcast_id
            LEFT JOIN transcriptions t ON t.episode_id = e.id
            ORDER BY e.published_at DESC, p.title, e.title
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_episodes_without_transcription() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT e.*, p.title AS podcast_title
            FROM episodes e
            JOIN podcasts p ON p.id = e.podcast_id
            LEFT JOIN transcriptions t ON t.episode_id = e.id
            WHERE t.episode_id IS NULL
            ORDER BY e.published_at DESC, p.title, e.title
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_transcription_by_episode(episode_id: int) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM transcriptions WHERE episode_id = ?",
            (episode_id,),
        ).fetchone()
        return dict(row) if row else None


def get_transcription_by_guid(guid: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT t.*
            FROM transcriptions t
            JOIN episodes e ON e.id = t.episode_id
            WHERE e.guid = ?
            """,
            (guid,),
        ).fetchone()
        return dict(row) if row else None


def mark_transcription(episode_id: int, transcript_path: Path) -> None:
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO transcriptions (episode_id, transcript_path)
            VALUES (?, ?)
            """,
            (episode_id, str(transcript_path)),
        )
        conn.commit()


def fetch_podcast_episodes(podcast_id: int, rss_url: str) -> tuple[int, int]:
    from digg_transcriber.rss import fetch_podcast_metadata_from_rss

    metadata = fetch_podcast_metadata_from_rss(rss_url)
    episodes = metadata.get("episodes", [])
    new_count = 0
    for episode in episodes:
        existing = get_episode_by_guid(episode["guid"])
        episode_id = upsert_episode(
            podcast_id,
            episode["guid"],
            episode["title"],
            description=episode.get("description"),
            audio_url=episode.get("audio_url"),
            published_at=episode.get("published_at"),
            duration_seconds=episode.get("duration_seconds"),
        )
        if existing is None:
            new_count += 1

    update_podcast_last_fetched(podcast_id)
    return new_count, len(episodes)


def _safe_path_component(value: Optional[str], default: str) -> str:
    safe = (value or default).replace("/", "_").replace("\\", "_").strip()
    safe = safe or default
    return safe[:100]


def _resolve_pod_transcriber_root(source_root: Path) -> Path:
    if (source_root / "data" / "podcasts.db").is_file() and (source_root / "transcripts").is_dir():
        return source_root
    if source_root.name == "transcripts" and (source_root.parent / "data" / "podcasts.db").is_file():
        return source_root.parent
    raise FileNotFoundError(
        "Could not find pod-transcriber data/podcasts.db and transcripts/ under the provided path"
    )


def import_pod_transcriber_transcripts(
    source_root: Path,
    *,
    podcast_title: Optional[str] = None,
    output_dir: Optional[Path] = None,
    dry_run: bool = False,
) -> dict[str, int]:
    root = _resolve_pod_transcriber_root(source_root)
    pod_db = root / "data" / "podcasts.db"
    transcripts_root = root / "transcripts"
    destination_root = (output_dir or Path.home() / "Transcripts").expanduser()

    conn = sqlite3.connect(f"file:{pod_db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT p.title AS podcast_title, p.rss_url,
                   e.guid, e.title AS episode_title, e.description,
                   e.audio_url, e.published_at, e.duration_seconds,
                   t.transcript_file
            FROM transcriptions t
            JOIN episodes e ON e.id = t.episode_id
            JOIN podcasts p ON p.id = e.podcast_id
            WHERE (? IS NULL OR p.title = ?)
            ORDER BY p.title, e.published_at DESC, e.title
            """,
            (podcast_title, podcast_title),
        ).fetchall()
    finally:
        conn.close()

    imported = 0
    missing = 0
    podcast_ids: set[int] = set()
    for row in rows:
        digg_podcast_id = add_podcast(row["podcast_title"], row["rss_url"])
        podcast_ids.add(digg_podcast_id)
        episode_id = upsert_episode(
            digg_podcast_id,
            row["guid"],
            row["episode_title"],
            description=row["description"],
            audio_url=row["audio_url"],
            published_at=row["published_at"],
            duration_seconds=row["duration_seconds"],
        )

        source_txt = transcripts_root / row["transcript_file"]
        podcast_component = _safe_path_component(row["podcast_title"], "untitled-podcast")
        episode_component = _safe_path_component(row["episode_title"], "untitled-episode")
        destination_txt = destination_root / podcast_component / episode_component / f"{episode_component}.txt"

        if not dry_run:
            if not source_txt.is_file():
                missing += 1
                continue
            destination_txt.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_txt, destination_txt)
            mark_transcription(episode_id, destination_txt)
            mark_processed(f"podcast:{row['guid']}", "podcast", row["episode_title"], destination_txt)

        imported += 1

    return {
        "imported": imported,
        "missing": missing,
        "podcasts": len(podcast_ids),
    }


__all__ = [
    "get_db_path",
    "get_db",
    "mark_processed",
    "is_processed",
    "get_processed_path",
    "add_podcast",
    "get_podcast_by_rss_url",
    "get_podcast_by_title",
    "get_all_podcasts",
    "update_podcast_last_fetched",
    "upsert_episode",
    "get_episode_by_guid",
    "get_episode_by_id",
    "get_episodes_by_podcast",
    "get_all_episodes",
    "get_episodes_without_transcription",
    "get_transcription_by_episode",
    "get_transcription_by_guid",
    "mark_transcription",
    "fetch_podcast_episodes",
    "import_pod_transcriber_transcripts",
]
