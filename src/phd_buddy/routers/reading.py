"""Research buddy: summaries + deep-dive chat sessions over SSE (Phase 1)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/reading", tags=["research"])
