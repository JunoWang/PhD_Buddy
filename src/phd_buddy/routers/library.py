"""Research buddy: paper library — search, add, verify, assets (Phase 1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services import discovery
from ..services.acquisition import acquire_pdf_markdown
from ..services.library import DEFAULT_LIBRARY_DIR, import_paper, list_papers, load_paper
from ..services.paper_rag import index_paper_chunks
from ..services.profile import load_plan

router = APIRouter(prefix="/api/library", tags=["research"])

DEFAULT_PROFILE_PATH = Path("vault/onboarding/onboarding_profile.json")


class PaperSearchRequest(BaseModel):
    query: str = ""
    max_results: int = Field(default=10, ge=1, le=25)
    use_onboarding: bool = True


class PaperImportRequest(BaseModel):
    title: str
    authors: list[str] = Field(default_factory=list)
    year: str = ""
    abstract: str = ""
    venue: str = "arXiv"
    source: str = "manual"
    external_ids: dict[str, str] = Field(default_factory=dict)
    pdf_url: str = ""
    landing_url: str = ""
    relevance_score: float = 0.0


@router.post("/search")
def search_library(payload: PaperSearchRequest) -> dict[str, Any]:
    try:
        if payload.use_onboarding and not payload.query.strip() and DEFAULT_PROFILE_PATH.exists():
            plan = load_plan(DEFAULT_PROFILE_PATH)
            candidates = discovery.search_from_onboarding(plan, max_results=payload.max_results)
        else:
            candidates = discovery.search_arxiv(payload.query, max_results=payload.max_results)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Paper source search failed: {exc}") from exc

    if payload.query.strip():
        candidates = discovery.rerank_candidates(candidates, [payload.query])
    return {"results": [candidate.to_dict() for candidate in candidates]}


@router.get("/papers")
def papers() -> dict[str, Any]:
    return {"papers": [paper.to_dict() for paper in list_papers(DEFAULT_LIBRARY_DIR)]}


@router.post("/papers/import")
def import_library_paper(payload: PaperImportRequest) -> dict[str, Any]:
    paper = import_paper(payload.model_dump(), DEFAULT_LIBRARY_DIR)
    acquisition_error = ""
    if paper.pdf_url:
        try:
            paper, _ = acquire_pdf_markdown(paper.paper_id, DEFAULT_LIBRARY_DIR)
            paper = index_paper_chunks(paper.paper_id)
        except Exception as exc:
            acquisition_error = str(exc)
    return {"paper": paper.to_dict(), "acquisition_error": acquisition_error}


@router.get("/papers/{paper_id}")
def paper_detail(paper_id: str) -> dict[str, Any]:
    paper = load_paper(paper_id, DEFAULT_LIBRARY_DIR)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    return {"paper": paper.to_dict()}


@router.get("/papers/{paper_id}/assets")
def paper_assets(paper_id: str) -> dict[str, Any]:
    paper = load_paper(paper_id, DEFAULT_LIBRARY_DIR)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    return {"assets": [asset.to_dict() for asset in paper.assets]}
