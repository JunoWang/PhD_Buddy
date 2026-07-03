"""Dual-format vault cache writer: one canonical JSON object plus student-facing markdown.

The vault is the human-readable, Obsidian-compatible projection of canonical state
(ARCHITECTURE.md §5). Every service that persists a student-facing artifact writes
through this module.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_dual_format(
    output_dir: Path,
    stem: str,
    payload: dict[str, Any],
    markdown: str,
) -> tuple[Path, Path]:
    """Write `<stem>.json` (canonical) and `<stem>.md` (student-facing) to the vault."""

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{stem}.json"
    markdown_path = output_dir / f"{stem}.md"

    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(markdown, encoding="utf-8")
    return json_path, markdown_path


def read_json(path: Path) -> dict[str, Any]:
    """Read a canonical JSON vault artifact."""

    return json.loads(path.read_text(encoding="utf-8"))
