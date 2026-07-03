"""Generic async-job status: long operations return a job_id immediately (Phase 1)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
