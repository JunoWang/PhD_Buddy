"""Cross-buddy signal bus (ARCHITECTURE.md §3.4).

Small internal events table (emitter, kind, payload, created_at); each buddy service
subscribes to the kinds it cares about. Only coarse signals cross the mental-health
boundary (e.g. ``stress_trend: high``), never check-in content.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..storage.db import list_buddy_events, record_buddy_event


def emit(
    thread_id: str,
    emitter: str,
    kind: str,
    payload: dict[str, Any],
    *,
    database_path: Path | None = None,
) -> None:
    """Persist a coarse cross-buddy signal without leaking private raw notes."""

    record_buddy_event(
        thread_id=thread_id,
        emitter=emitter,
        kind=kind,
        payload=payload,
        path=database_path,
    )


def history(thread_id: str, *, database_path: Path | None = None) -> list[dict[str, Any]]:
    return list_buddy_events(thread_id, path=database_path)
