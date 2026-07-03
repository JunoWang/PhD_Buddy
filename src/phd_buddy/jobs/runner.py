"""In-process job runner (APScheduler) — enough at single-user scale (ARCHITECTURE.md §7).

Long operations return a job_id immediately; clients poll GET /api/jobs/{id} or
subscribe to SSE. A real queue is added only if reproducibility-sandbox work lands.
"""

from __future__ import annotations
