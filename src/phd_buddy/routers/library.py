"""Research buddy: paper library — search, add, verify, assets (Phase 1)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/library", tags=["research"])
