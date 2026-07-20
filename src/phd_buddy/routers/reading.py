"""Research buddy: summaries + deep-dive chat sessions over SSE (Phase 1)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field

from ..services.acquisition import (
    extract_pdf_figures,
    extract_pdf_formulas,
    extract_pdf_tables,
    pdf_asset_path,
    pdf_extraction_report,
    pdf_to_markdown,
    render_pdf_figure,
    render_pdf_formula,
    render_pdf_table,
    render_pdf_tables,
)
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


@router.get("/papers/{paper_id}/content")
def paper_content(paper_id: str) -> dict[str, Any]:
    """Return the entire extracted reading text plus source-completeness evidence."""

    paper = load_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    markdown = read_paper_markdown(paper)
    pdf_path = pdf_asset_path(paper)
    figures: list[dict[str, Any]] = []
    formulas: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    if pdf_path and pdf_path.exists():
        figures = extract_pdf_figures(paper)
        formulas = extract_pdf_formulas(paper)
        tables = extract_pdf_tables(paper)
        render_pdf_tables(paper, tables)
        markdown = pdf_to_markdown(
            pdf_path,
            title=paper.title,
            figures=figures,
            formulas=formulas,
            tables=tables,
        )
        report = pdf_extraction_report(pdf_path, markdown)
    else:
        if not markdown:
            raise HTTPException(status_code=404, detail="Markdown has not been created for this paper yet.")
        page_count = markdown.count("## Page ")
        report = {
            "page_count": page_count,
            "extracted_page_count": page_count,
            "missing_text_pages": [],
            "text_extraction_complete": bool(page_count),
            "character_count": len(markdown),
            "word_count": len(markdown.split()),
        }
    return {
        "markdown": markdown,
        "source_pdf_available": bool(pdf_path and pdf_path.exists()),
        "figures": figures,
        "formulas": formulas,
        "tables": tables,
        **report,
    }


@router.get("/papers/{paper_id}/pdf", response_class=FileResponse)
def paper_pdf(paper_id: str) -> FileResponse:
    """Serve the locally stored original PDF inline as the complete source."""

    paper = load_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    pdf_path = pdf_asset_path(paper)
    if not pdf_path or not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Original PDF is not available locally.")
    safe_name = "".join(character if character.isalnum() or character in {"-", "_"} else "-" for character in paper.title)
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"{safe_name.strip('-') or paper.paper_id}.pdf",
        content_disposition_type="inline",
    )


@router.get("/papers/{paper_id}/figures/{figure_id}.png", response_class=FileResponse)
def paper_figure_image(paper_id: str, figure_id: str) -> FileResponse:
    """Render a detected figure by itself, preserving vector and bitmap content."""

    paper = load_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    try:
        image_path = render_pdf_figure(paper, figure_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(
        image_path,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/papers/{paper_id}/formulas/{formula_id}.png", response_class=FileResponse)
def paper_formula_image(paper_id: str, formula_id: str) -> FileResponse:
    """Render a displayed formula using the source PDF's original glyph layout."""

    paper = load_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    try:
        image_path = render_pdf_formula(paper, formula_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(
        image_path,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/papers/{paper_id}/tables/{table_id}.png", response_class=FileResponse)
def paper_table_image(paper_id: str, table_id: str) -> FileResponse:
    """Render a complete table and caption with their original PDF layout."""

    paper = load_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    try:
        image_path = render_pdf_table(paper, table_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(
        image_path,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.post("/ask")
def ask(payload: AskRequest) -> dict[str, Any]:
    return answer_with_rag(payload.query, top_k=payload.top_k, paper_id=payload.paper_id)


@router.post("/ask-agentic")
def ask_agentic_endpoint(payload: AskRequest) -> dict[str, Any]:
    try:
        return ask_agentic(payload.query, top_k=payload.top_k, paper_id=payload.paper_id).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
