"""Task → model routing so cost stays inside the $20–50/month ceiling (ARCHITECTURE.md §6)."""

from __future__ import annotations

from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent / "harnesses"

# task name -> (model tier, execution mode)
MODEL_ROUTES: dict[str, tuple[str, str]] = {
    "paper_summary": ("haiku", "async_job"),
    "deep_dive_chat": ("sonnet", "sse_stream"),
    "recent_search_rerank": ("haiku", "async_job"),
    "idea_structuring": ("sonnet", "sync"),
    "idea_persona_panel": ("sonnet", "async_job"),
    "weekly_digest": ("haiku", "cron"),
    "task_decompose": ("sonnet", "sync"),
    "weekly_plan": ("sonnet", "sync"),
    "checkin_ack": ("haiku", "sync"),
    "supportive_chat": ("sonnet", "sse_stream"),
}


def load_harness(name: str) -> str:
    """Load a versioned system-prompt harness, e.g. ``deep_dive`` or ``idea_panel/venue_reviewer``."""

    return (HARNESS_DIR / f"{name}.md").read_text(encoding="utf-8")
