"""Entity definitions for all three buddies (ARCHITECTURE.md §5).

Planned tables:

- shared: Profile, Event, Job, Notification
- research: Paper, PaperAsset, Summary, DeepDiveSession, DeepDiveMessage,
  Idea, IdeaReview, IdeaRoute, AdvisorPersona
- schedule: Task, TaskStep, WeeklyPlan, ScheduleBlock
- mental (sensitive, local-only by default): CheckIn, SupportAction, ReminderRule

Implemented incrementally starting in Phase 1 (Paper + PaperAsset first).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PaperAsset:
    """A stored or reference asset associated with a paper."""

    kind: str
    uri: str
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "uri": self.uri,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PaperAsset":
        return cls(
            kind=str(raw.get("kind", "")).strip(),
            uri=str(raw.get("uri", raw.get("path", ""))).strip(),
            created_at=str(raw.get("created_at", "")).strip(),
            metadata=dict(raw.get("metadata", {})),
        )


@dataclass(frozen=True)
class PaperChunk:
    """A section-aware text chunk, ready for later retrieval work."""

    chunk_id: str
    paper_id: str
    section: str
    text: str
    order: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "paper_id": self.paper_id,
            "section": self.section,
            "text": self.text,
            "order": self.order,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PaperChunk":
        return cls(
            chunk_id=str(raw.get("chunk_id", "")).strip(),
            paper_id=str(raw.get("paper_id", "")).strip(),
            section=str(raw.get("section", "")).strip(),
            text=str(raw.get("text", "")).strip(),
            order=int(raw.get("order", 0)),
        )


@dataclass(frozen=True)
class PaperSummary:
    """A summary artifact for a paper."""

    paper_id: str
    content_md: str
    model: str
    created_at: str
    path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "paper_id": self.paper_id,
            "content_md": self.content_md,
            "model": self.model,
            "created_at": self.created_at,
            "path": self.path,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PaperSummary":
        return cls(
            paper_id=str(raw.get("paper_id", "")).strip(),
            content_md=str(raw.get("content_md", "")).strip(),
            model=str(raw.get("model", "")).strip(),
            created_at=str(raw.get("created_at", "")).strip(),
            path=str(raw.get("path", "")).strip(),
        )


@dataclass(frozen=True)
class Paper:
    """Canonical local record for an imported paper."""

    paper_id: str
    title: str
    authors: list[str]
    year: str
    venue: str = ""
    abstract: str = ""
    source: str = "manual"
    external_ids: dict[str, str] = field(default_factory=dict)
    verification_status: str = "unverified"
    pdf_url: str = ""
    landing_url: str = ""
    imported_at: str = ""
    assets: list[PaperAsset] = field(default_factory=list)
    chunks: list[PaperChunk] = field(default_factory=list)
    summary: PaperSummary | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "paper_id": self.paper_id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "venue": self.venue,
            "abstract": self.abstract,
            "source": self.source,
            "external_ids": self.external_ids,
            "verification_status": self.verification_status,
            "pdf_url": self.pdf_url,
            "landing_url": self.landing_url,
            "imported_at": self.imported_at,
            "assets": [asset.to_dict() for asset in self.assets],
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "summary": self.summary.to_dict() if self.summary else None,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Paper":
        return cls(
            paper_id=str(raw.get("paper_id", "")).strip(),
            title=str(raw.get("title", "")).strip(),
            authors=[str(author).strip() for author in raw.get("authors", []) if str(author).strip()],
            year=str(raw.get("year", "")).strip(),
            venue=str(raw.get("venue", "")).strip(),
            abstract=str(raw.get("abstract", "")).strip(),
            source=str(raw.get("source", "manual")).strip() or "manual",
            external_ids={str(key): str(value) for key, value in dict(raw.get("external_ids", {})).items()},
            verification_status=str(raw.get("verification_status", "unverified")).strip() or "unverified",
            pdf_url=str(raw.get("pdf_url", "")).strip(),
            landing_url=str(raw.get("landing_url", "")).strip(),
            imported_at=str(raw.get("imported_at", "")).strip(),
            assets=[PaperAsset.from_dict(item) for item in raw.get("assets", [])],
            chunks=[PaperChunk.from_dict(item) for item in raw.get("chunks", [])],
            summary=PaperSummary.from_dict(raw["summary"]) if raw.get("summary") else None,
        )
