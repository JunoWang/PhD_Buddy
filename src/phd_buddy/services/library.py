"""Local paper library storage for Phase 1 Research Buddy."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable
from uuid import uuid5, NAMESPACE_URL

from ..storage.models import Paper, PaperAsset


DEFAULT_LIBRARY_DIR = Path("vault/library")
INDEX_FILE = "papers.json"


def import_paper(candidate: dict[str, object], library_dir: Path | None = None) -> Paper:
    """Create or update a local paper record from a normalized search candidate."""

    library_dir = library_dir or DEFAULT_LIBRARY_DIR
    now = datetime.now(UTC).isoformat()
    paper_id = _paper_id(candidate)
    external_ids = _string_dict(candidate.get("external_ids", {}))
    pdf_url = str(candidate.get("pdf_url", "")).strip()
    landing_url = str(candidate.get("landing_url", "")).strip()

    assets = [
        PaperAsset(
            kind="metadata",
            uri=str(_paper_dir(library_dir, paper_id) / "metadata.json"),
            created_at=now,
            metadata={"source": str(candidate.get("source", "manual")).strip() or "manual"},
        )
    ]
    if pdf_url:
        assets.append(PaperAsset(kind="pdf_url", uri=pdf_url, created_at=now))

    paper = Paper(
        paper_id=paper_id,
        title=str(candidate.get("title", "")).strip(),
        authors=_string_list(candidate.get("authors", [])),
        year=str(candidate.get("year", "")).strip(),
        venue=str(candidate.get("venue", "")).strip(),
        abstract=str(candidate.get("abstract", "")).strip(),
        source=str(candidate.get("source", "manual")).strip() or "manual",
        external_ids=external_ids,
        verification_status=str(candidate.get("verification_status", "unverified")).strip() or "unverified",
        pdf_url=pdf_url,
        landing_url=landing_url,
        imported_at=now,
        assets=assets,
    )
    save_paper(paper, library_dir)
    return paper


def save_paper(paper: Paper, library_dir: Path | None = None) -> Path:
    library_dir = library_dir or DEFAULT_LIBRARY_DIR
    paper_dir = _paper_dir(library_dir, paper.paper_id)
    paper_dir.mkdir(parents=True, exist_ok=True)
    path = paper_dir / "metadata.json"
    path.write_text(json.dumps(paper.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_index(list_papers(library_dir, include_missing=False, extra=paper), library_dir)
    return path


def load_paper(paper_id: str, library_dir: Path | None = None) -> Paper | None:
    library_dir = library_dir or DEFAULT_LIBRARY_DIR
    path = _paper_dir(library_dir, paper_id) / "metadata.json"
    if not path.exists():
        return None
    return Paper.from_dict(json.loads(path.read_text(encoding="utf-8")))


def list_papers(
    library_dir: Path | None = None,
    *,
    include_missing: bool = True,
    extra: Paper | None = None,
) -> list[Paper]:
    library_dir = library_dir or DEFAULT_LIBRARY_DIR
    papers: dict[str, Paper] = {}
    index_path = library_dir / INDEX_FILE
    if index_path.exists():
        raw = json.loads(index_path.read_text(encoding="utf-8"))
        for item in raw.get("papers", []):
            paper = Paper.from_dict(item)
            if include_missing or (_paper_dir(library_dir, paper.paper_id) / "metadata.json").exists():
                papers[paper.paper_id] = paper
    if library_dir.exists():
        for path in library_dir.glob("*/metadata.json"):
            paper = Paper.from_dict(json.loads(path.read_text(encoding="utf-8")))
            papers[paper.paper_id] = paper
    if extra:
        papers[extra.paper_id] = extra
    return sorted(papers.values(), key=lambda item: item.imported_at, reverse=True)


def _write_index(papers: Iterable[Paper], library_dir: Path) -> None:
    library_dir.mkdir(parents=True, exist_ok=True)
    payload = {"papers": [paper.to_dict() for paper in papers]}
    (library_dir / INDEX_FILE).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _paper_id(candidate: dict[str, object]) -> str:
    external_ids = _string_dict(candidate.get("external_ids", {}))
    stable_key = external_ids.get("arxiv") or external_ids.get("doi") or str(candidate.get("landing_url", ""))
    if not stable_key:
        stable_key = f"{candidate.get('title', '')}:{','.join(_string_list(candidate.get('authors', [])))}"
    return f"paper-{uuid5(NAMESPACE_URL, stable_key).hex[:12]}"


def _paper_dir(library_dir: Path, paper_id: str) -> Path:
    return library_dir / _safe_path_part(paper_id)


def _safe_path_part(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-") or "paper"


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _string_dict(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key).strip(): str(item).strip() for key, item in value.items() if str(key).strip() and str(item).strip()}
