"""Research buddy: open-access PDF acquisition → structure-aware markdown (Phase 1).

PDF is converted to markdown before any model sees it; PDF, markdown, and metadata
are stored together as PaperAssets (ARCHITECTURE.md §3.1, §6).
"""

from __future__ import annotations

import re
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from pypdf import PdfReader

from ..storage.models import Paper, PaperAsset
from .library import DEFAULT_LIBRARY_DIR, load_paper, save_paper


def acquire_pdf_markdown(paper_id: str, library_dir: Path | None = None) -> tuple[Paper, Path]:
    """Download a paper PDF and convert the original extracted text to markdown."""

    library_dir = library_dir or DEFAULT_LIBRARY_DIR
    paper = load_paper(paper_id, library_dir)
    if not paper:
        raise ValueError(f"Paper not found: {paper_id}")
    if not paper.pdf_url:
        raise ValueError(f"Paper has no PDF URL: {paper_id}")

    paper_dir = library_dir / paper.paper_id
    paper_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = paper_dir / "paper.pdf"
    markdown_path = paper_dir / "paper.md"

    _download(paper.pdf_url, pdf_path)
    markdown = pdf_to_markdown(pdf_path, title=paper.title)
    markdown_path.write_text(markdown, encoding="utf-8")
    extraction = pdf_extraction_report(pdf_path, markdown)

    now = datetime.now(UTC).isoformat()
    assets = [asset for asset in paper.assets if asset.kind not in {"pdf", "markdown"}]
    assets.extend(
        [
            PaperAsset(kind="pdf", uri=str(pdf_path), created_at=now, metadata={"source_url": paper.pdf_url}),
            PaperAsset(
                kind="markdown",
                uri=str(markdown_path),
                created_at=now,
                metadata={"source": "pdf_extract", **extraction},
            ),
        ]
    )
    updated = Paper(
        paper_id=paper.paper_id,
        title=paper.title,
        authors=paper.authors,
        year=paper.year,
        venue=paper.venue,
        abstract=paper.abstract,
        source=paper.source,
        external_ids=paper.external_ids,
        verification_status=paper.verification_status,
        pdf_url=paper.pdf_url,
        landing_url=paper.landing_url,
        imported_at=paper.imported_at,
        assets=assets,
        chunks=paper.chunks,
        summary=paper.summary,
    )
    save_paper(updated, library_dir)
    return updated, markdown_path


def pdf_to_markdown(pdf_path: Path, *, title: str = "") -> str:
    """Extract PDF text page-by-page and preserve it as a markdown reading file."""

    reader = PdfReader(str(pdf_path))
    lines: list[str] = []
    if title:
        lines.extend([f"# {title}", ""])
    lines.extend(["<!-- Original PDF text extracted page-by-page. -->", ""])
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = _normalize_text(text)
        if not text:
            text = "> This page has no extractable text. Switch to Original PDF to view the complete page."
        lines.extend([f"## Page {index}", "", text, ""])
    return "\n".join(lines).strip() + "\n"


def markdown_asset_path(paper: Paper) -> Path | None:
    for asset in paper.assets:
        if asset.kind == "markdown" and asset.uri:
            return Path(asset.uri)
    return None


def pdf_asset_path(paper: Paper) -> Path | None:
    """Return the locally stored source PDF, when acquisition succeeded."""

    for asset in paper.assets:
        if asset.kind == "pdf" and asset.uri:
            return Path(asset.uri)
    return None


def pdf_extraction_report(pdf_path: Path, markdown: str = "") -> dict[str, object]:
    """Describe whether every source page yielded readable text.

    The original PDF remains the completeness authority because text extraction
    cannot faithfully represent image-only pages, figures, or equations.
    """

    reader = PdfReader(str(pdf_path))
    missing_pages: list[int] = []
    extracted_page_count = 0
    for index, page in enumerate(reader.pages, start=1):
        if _normalize_text(page.extract_text() or ""):
            extracted_page_count += 1
        else:
            missing_pages.append(index)
    return {
        "page_count": len(reader.pages),
        "extracted_page_count": extracted_page_count,
        "missing_text_pages": missing_pages,
        "text_extraction_complete": not missing_pages,
        "character_count": len(markdown),
        "word_count": len(re.findall(r"\S+", markdown)),
    }


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "PhD-Buddy/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        destination.write_bytes(response.read())


def _normalize_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
