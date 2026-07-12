"""Research buddy: summaries + deep-dive chat sessions over SSE (Phase 1)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from ..services.library import load_paper
from ..services.paper_rag import answer_with_rag, ask_agentic, index_paper_chunks, read_paper_markdown

router = APIRouter(prefix="/api/reading", tags=["research"])


class IndexPaperRequest(BaseModel):
    full_text: str = ""


class AskRequest(BaseModel):
    query: str
    paper_id: str = ""
    top_k: int = Field(default=5, ge=1, le=10)


@router.post("/papers/{paper_id}/index")
def index_paper(paper_id: str, payload: IndexPaperRequest) -> dict[str, Any]:
    try:
        paper = index_paper_chunks(paper_id, payload.full_text)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"paper": paper.to_dict(), "chunk_count": len(paper.chunks)}


@router.get("/papers/{paper_id}/markdown", response_class=PlainTextResponse)
def paper_markdown(paper_id: str) -> str:
    paper = load_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    markdown = read_paper_markdown(paper)
    if not markdown:
        raise HTTPException(status_code=404, detail="Markdown has not been created for this paper yet.")
    return markdown


@router.post("/ask")
def ask(payload: AskRequest) -> dict[str, Any]:
    return answer_with_rag(payload.query, top_k=payload.top_k, paper_id=payload.paper_id)


@router.post("/ask-agentic")
def ask_agentic_endpoint(payload: AskRequest) -> dict[str, Any]:
    try:
        return ask_agentic(payload.query, top_k=payload.top_k, paper_id=payload.paper_id).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
