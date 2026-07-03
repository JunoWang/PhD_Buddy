"""Mental buddy: support actions + supportive chat over SSE, HITL-gated (Phase 4)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/support", tags=["mental"])
