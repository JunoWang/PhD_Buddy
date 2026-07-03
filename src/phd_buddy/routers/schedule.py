"""Schedule buddy: weekly plan + replan; plans are draft-until-accepted (Phase 3)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/schedule", tags=["schedule"])
