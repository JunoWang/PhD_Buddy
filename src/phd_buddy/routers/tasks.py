"""Schedule buddy: task intake + decomposition (Phase 3)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/tasks", tags=["schedule"])
