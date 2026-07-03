"""Research buddy: brainstorm → structuring → persona panel → routing (Phase 2)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/ideas", tags=["research"])
