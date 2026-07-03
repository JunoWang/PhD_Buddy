"""Mental buddy: mood pings + stress history; data is sensitive/local-only (Phase 4)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/checkin", tags=["mental"])
