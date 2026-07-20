"""Reusable paper-ingestion steps orchestrated by the Airflow DAG."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .acquisition import acquire_pdf_markdown, pdf_asset_path
from .discovery import search_from_onboarding
from .library import list_papers
from .paper_rag import index_paper_chunks
from .profile import load_plan

DEFAULT_PROFILE_PATH = Path("vault/onboarding/onboarding_profile.json")
DEFAULT_INGESTION_DIR = Path("vault/ingestion")


def sync_recommendations(max_results: int = 10) -> dict[str, Any]:
    """Fetch a daily recommendation snapshot without silently importing papers."""

    if not DEFAULT_PROFILE_PATH.exists():
        return {"status": "skipped", "reason": "onboarding profile not found", "count": 0}
    plan = load_plan(DEFAULT_PROFILE_PATH)
    candidates = search_from_onboarding(plan, max_results=max_results)
    output_dir = DEFAULT_INGESTION_DIR / "recommendations"
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(UTC)
    output_path = output_dir / f"{generated_at:%Y%m%dT%H%M%SZ}.json"
    output_path.write_text(
        json.dumps(
            {
                "generated_at": generated_at.isoformat(),
                "candidates": [candidate.to_dict() for candidate in candidates],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return {"status": "done", "count": len(candidates), "path": str(output_path)}


def acquire_pending_papers() -> dict[str, Any]:
    """Download and parse imported papers whose local PDF is still missing."""

    acquired: list[str] = []
    skipped: list[str] = []
    failures: dict[str, str] = {}
    for paper in list_papers():
        if pdf_asset_path(paper):
            skipped.append(paper.paper_id)
            continue
        if not paper.pdf_url:
            failures[paper.paper_id] = "No PDF URL is available."
            continue
        try:
            acquire_pdf_markdown(paper.paper_id)
            acquired.append(paper.paper_id)
        except Exception as exc:
            failures[paper.paper_id] = str(exc)
    return {"acquired": acquired, "skipped": skipped, "failures": failures}


def index_library_papers() -> dict[str, Any]:
    """Create or refresh searchable chunks for every readable library paper."""

    indexed: dict[str, int] = {}
    failures: dict[str, str] = {}
    for paper in list_papers():
        try:
            updated = index_paper_chunks(paper.paper_id)
            indexed[paper.paper_id] = len(updated.chunks)
        except Exception as exc:
            failures[paper.paper_id] = str(exc)
    return {"indexed": indexed, "failures": failures}


def write_ingestion_report(
    recommendations: dict[str, Any],
    acquisition: dict[str, Any],
    indexing: dict[str, Any],
) -> dict[str, Any]:
    output_dir = DEFAULT_INGESTION_DIR / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(UTC)
    run_id = f"ingestion-{created_at:%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
    output_path = output_dir / f"{run_id}.json"
    payload = {
        "run_id": run_id,
        "created_at": created_at.isoformat(),
        "recommendations": recommendations,
        "acquisition": acquisition,
        "indexing": indexing,
    }
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"run_id": run_id, "path": str(output_path)}


def cleanup_ingestion_artifacts(*, keep: int = 30) -> dict[str, Any]:
    """Prune only reproducible ingestion reports and recommendation snapshots."""

    removed: list[str] = []
    for directory in (
        DEFAULT_INGESTION_DIR / "reports",
        DEFAULT_INGESTION_DIR / "recommendations",
    ):
        if not directory.exists():
            continue
        files = sorted(directory.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        for path in files[keep:]:
            path.unlink()
            removed.append(str(path))
    return {"removed": removed, "kept_per_directory": keep}
