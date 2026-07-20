"""SQLite application state shared by Airflow jobs and LangGraph buddy workflows."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path("vault/phd_buddy.sqlite3")


def connect_database(path: Path | None = None) -> sqlite3.Connection:
    """Open the local application database with safe concurrent-reader settings."""

    database_path = path or DEFAULT_DB_PATH
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=30, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=30000")
    initialize_database(connection)
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS buddy_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT NOT NULL,
            emitter TEXT NOT NULL,
            kind TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_buddy_events_thread
            ON buddy_events(thread_id, created_at);

        CREATE TABLE IF NOT EXISTS ingestion_runs (
            run_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            report_path TEXT NOT NULL DEFAULT '',
            details_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            finished_at TEXT
        );
        """
    )
    connection.commit()


def record_buddy_event(
    *,
    thread_id: str,
    emitter: str,
    kind: str,
    payload: dict[str, Any],
    path: Path | None = None,
) -> None:
    with connect_database(path) as connection:
        connection.execute(
            """
            INSERT INTO buddy_events(thread_id, emitter, kind, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                thread_id,
                emitter,
                kind,
                json.dumps(payload, ensure_ascii=False),
                datetime.now(UTC).isoformat(),
            ),
        )


def list_buddy_events(thread_id: str, *, path: Path | None = None) -> list[dict[str, Any]]:
    with connect_database(path) as connection:
        rows = connection.execute(
            """
            SELECT emitter, kind, payload_json, created_at
            FROM buddy_events
            WHERE thread_id = ?
            ORDER BY event_id
            """,
            (thread_id,),
        ).fetchall()
    return [
        {
            "emitter": row["emitter"],
            "kind": row["kind"],
            "payload": json.loads(row["payload_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]
