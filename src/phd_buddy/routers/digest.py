"""Research buddy: scheduled recent-search digests (Phase 1)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/digest", tags=["research"])
