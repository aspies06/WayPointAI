"""Private, local SQLite storage for reusable experience stories.

Each browser library has a random bearer key. Only its SHA-256 digest is stored,
and every story query includes that library's digest. Connections are opened per
operation so FastAPI worker threads do not share SQLite connections.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
from uuid import uuid4


DEFAULT_DB = Path(__file__).resolve().parent / ".local" / "story-bank.sqlite3"


@contextmanager
def _database():
    path = Path(os.getenv("WAYPOINT_STORY_DB", str(DEFAULT_DB))).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Create with owner-only permissions before SQLite opens the file.
    descriptor = os.open(path, os.O_CREAT | os.O_WRONLY, 0o600)
    os.close(descriptor)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS libraries (
                key_hash TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS stories (
                id TEXT PRIMARY KEY,
                library_hash TEXT NOT NULL REFERENCES libraries(key_hash),
                answers TEXT NOT NULL,
                organization TEXT NOT NULL,
                dates TEXT NOT NULL,
                narrative TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS stories_library
                ON stories(library_hash, created_at);
        """)
        with connection:
            yield connection
    finally:
        connection.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def key_digest(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def create_library() -> str:
    key = secrets.token_urlsafe(32)
    with _database() as db:
        db.execute("INSERT INTO libraries (key_hash, created_at) VALUES (?, ?)",
                   (key_digest(key), _now()))
    return key


def library_exists(library_hash: str) -> bool:
    with _database() as db:
        return db.execute("SELECT 1 FROM libraries WHERE key_hash = ?",
                          (library_hash,)).fetchone() is not None


def _story(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "answers": json.loads(row["answers"]),
        "organization": row["organization"],
        "dates": row["dates"],
        "narrative": row["narrative"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_stories(library_hash: str) -> list[dict]:
    with _database() as db:
        rows = db.execute("SELECT * FROM stories WHERE library_hash = ? "
                          "ORDER BY created_at DESC, id DESC", (library_hash,)).fetchall()
    return [_story(row) for row in rows]


def create_story(library_hash: str, data: dict) -> dict:
    story_id, now = uuid4().hex, _now()
    with _database() as db:
        db.execute("""INSERT INTO stories
                      (id, library_hash, answers, organization, dates, narrative, created_at, updated_at)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                   (story_id, library_hash, json.dumps(data["answers"], ensure_ascii=False),
                    data["organization"], data["dates"], data["narrative"], now, now))
        row = db.execute("SELECT * FROM stories WHERE id = ? AND library_hash = ?",
                         (story_id, library_hash)).fetchone()
    return _story(row)


def update_story(library_hash: str, story_id: str, data: dict) -> dict | None:
    with _database() as db:
        result = db.execute("""UPDATE stories SET answers = ?, organization = ?, dates = ?,
                               narrative = ?, updated_at = ? WHERE id = ? AND library_hash = ?""",
                            (json.dumps(data["answers"], ensure_ascii=False), data["organization"],
                             data["dates"], data["narrative"], _now(), story_id, library_hash))
        if not result.rowcount:
            return None
        row = db.execute("SELECT * FROM stories WHERE id = ? AND library_hash = ?",
                         (story_id, library_hash)).fetchone()
    return _story(row)


def delete_library(library_hash: str) -> bool:
    """Erase a story bank and every story in it."""
    with _database() as db:
        db.execute("DELETE FROM stories WHERE library_hash = ?", (library_hash,))
        result = db.execute("DELETE FROM libraries WHERE key_hash = ?", (library_hash,))
        return result.rowcount > 0


def delete_story(library_hash: str, story_id: str) -> bool:
    with _database() as db:
        result = db.execute("DELETE FROM stories WHERE id = ? AND library_hash = ?",
                            (story_id, library_hash))
        return result.rowcount > 0
