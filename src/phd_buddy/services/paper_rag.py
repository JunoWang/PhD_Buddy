"""Course-inspired local RAG and agentic pipeline for Paper Buddy.

This mirrors the production-agentic-rag-course stages while keeping the default
backend local and deterministic: chunk -> retrieve -> grade -> rewrite -> answer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..storage.models import Paper, PaperChunk
from .acquisition import markdown_asset_path
from .library import load_paper, list_papers, save_paper


@dataclass(frozen=True)
class RetrievedChunk:
    paper_id: str
    chunk_id: str
    title: str
    section: str
    text: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "paper_id": self.paper_id,
            "chunk_id": self.chunk_id,
            "title": self.title,
            "section": self.section,
            "text": self.text,
            "score": self.score,
        }


@dataclass(frozen=True)
class AgentStep:
    node: str
    status: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {"node": self.node, "status": self.status, "detail": self.detail}


@dataclass(frozen=True)
class AgenticRagResult:
    query: str
    answer: str
    sources: list[RetrievedChunk]
    reasoning_steps: list[AgentStep]
    retrieval_attempts: int
    route: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "answer": self.answer,
            "sources": [source.to_dict() for source in self.sources],
            "reasoning_steps": [step.to_dict() for step in self.reasoning_steps],
            "retrieval_attempts": self.retrieval_attempts,
            "route": self.route,
        }


@dataclass
class AgentState:
    query: str
    paper_id: str = ""
    rewritten_query: str = ""
    retrieval_attempts: int = 0
    sources: list[RetrievedChunk] = field(default_factory=list)
    reasoning_steps: list[AgentStep] = field(default_factory=list)
    route: str = "retrieve"


class TextChunker:
    """Section-aware chunker with a word-overlap fallback."""

    def __init__(self, chunk_size: int = 220, overlap_size: int = 40, min_chunk_size: int = 30):
        if overlap_size >= chunk_size:
            raise ValueError("overlap_size must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.min_chunk_size = min_chunk_size

    def chunk_paper(self, paper: Paper, full_text: str = "") -> list[PaperChunk]:
        sections = {
            "Abstract": paper.abstract,
            "Imported Metadata": full_text,
        }
        chunks: list[PaperChunk] = []
        for section, text in sections.items():
            if not text.strip():
                continue
            chunks.extend(self._chunk_text(paper.paper_id, section, text, len(chunks)))
        return chunks

    def _chunk_text(self, paper_id: str, section: str, text: str, offset: int) -> list[PaperChunk]:
        words = re.findall(r"\S+", text)
        if not words:
            return []
        if len(words) <= max(self.min_chunk_size, self.chunk_size):
            return [
                PaperChunk(
                    chunk_id=f"{paper_id}-chunk-{offset}",
                    paper_id=paper_id,
                    section=section,
                    text=" ".join(words),
                    order=offset,
                )
            ]

        chunks: list[PaperChunk] = []
        position = 0
        while position < len(words):
            end = min(position + self.chunk_size, len(words))
            chunk_words = words[position:end]
            chunks.append(
                PaperChunk(
                    chunk_id=f"{paper_id}-chunk-{offset + len(chunks)}",
                    paper_id=paper_id,
                    section=section,
                    text=" ".join(chunk_words),
                    order=offset + len(chunks),
                )
            )
            if end >= len(words):
                break
            position += self.chunk_size - self.overlap_size
        return chunks


def index_paper_chunks(paper_id: str, full_text: str = "") -> Paper:
    paper = load_paper(paper_id)
    if not paper:
        raise ValueError(f"Paper not found: {paper_id}")
    source_text = full_text or read_paper_markdown(paper) or ""
    chunks = TextChunker().chunk_paper(paper, source_text)
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
        assets=paper.assets,
        chunks=chunks,
        summary=paper.summary,
    )
    save_paper(updated)
    return updated


def read_paper_markdown(paper: Paper) -> str:
    path = markdown_asset_path(paper)
    if not path or not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def retrieve_chunks(query: str, *, top_k: int = 5, paper_id: str = "") -> list[RetrievedChunk]:
    query_terms = _keywords(query)
    results: list[RetrievedChunk] = []
    for paper in list_papers():
        if paper_id and paper.paper_id != paper_id:
            continue
        chunks = paper.chunks or TextChunker().chunk_paper(paper)
        for chunk in chunks:
            terms = _keywords(f"{paper.title} {chunk.section} {chunk.text}")
            score = _score(query_terms, terms)
            if score <= 0:
                continue
            results.append(
                RetrievedChunk(
                    paper_id=paper.paper_id,
                    chunk_id=chunk.chunk_id,
                    title=paper.title,
                    section=chunk.section,
                    text=chunk.text,
                    score=round(score, 4),
                )
            )
    return sorted(results, key=lambda item: item.score, reverse=True)[:top_k]


def answer_with_rag(query: str, *, top_k: int = 5, paper_id: str = "") -> dict[str, Any]:
    sources = retrieve_chunks(query, top_k=top_k, paper_id=paper_id)
    if not sources:
        return {
            "query": query,
            "answer": "I could not find relevant imported paper context yet. Import papers or broaden the query first.",
            "sources": [],
            "search_mode": "local_bm25",
        }
    lead = sources[0]
    answer = (
        f"Based on the imported paper context, the closest match is `{lead.title}`. "
        f"The relevant section is {lead.section.lower()}, which says: {lead.text[:420]}"
    )
    if len(lead.text) > 420:
        answer += "..."
    return {
        "query": query,
        "answer": answer,
        "sources": [source.to_dict() for source in sources],
        "search_mode": "local_bm25",
    }


def ask_agentic(query: str, *, top_k: int = 5, max_attempts: int = 2, paper_id: str = "") -> AgenticRagResult:
    if not query.strip():
        raise ValueError("Query cannot be empty")

    state = AgentState(query=query.strip(), paper_id=paper_id)
    _guardrail(state)
    if state.route == "out_of_scope":
        return AgenticRagResult(
            query=state.query,
            answer="Paper Buddy can only answer questions about imported research papers and research-reading tasks.",
            sources=[],
            reasoning_steps=state.reasoning_steps,
            retrieval_attempts=0,
            route=state.route,
        )

    while state.retrieval_attempts < max_attempts:
        _retrieve(state, top_k=top_k)
        _grade_documents(state)
        if state.route == "generate_answer":
            break
        _rewrite_query(state)

    answer = _generate_answer(state)
    return AgenticRagResult(
        query=state.query,
        answer=answer,
        sources=state.sources,
        reasoning_steps=state.reasoning_steps,
        retrieval_attempts=state.retrieval_attempts,
        route=state.route,
    )


def _guardrail(state: AgentState) -> None:
    research_terms = {
        "paper",
        "papers",
        "research",
        "method",
        "experiment",
        "abstract",
        "model",
        "dataset",
        "baseline",
        "citation",
        "summary",
        "author",
        "reading",
    }
    terms = _keywords(state.query)
    if terms & research_terms or len(terms) <= 3:
        state.reasoning_steps.append(AgentStep("guardrail", "continue", "Query is compatible with paper retrieval."))
        return
    state.route = "out_of_scope"
    state.reasoning_steps.append(AgentStep("guardrail", "blocked", "Query appears outside Paper Buddy scope."))


def _retrieve(state: AgentState, *, top_k: int) -> None:
    active_query = state.rewritten_query or state.query
    state.sources = retrieve_chunks(active_query, top_k=top_k, paper_id=state.paper_id)
    state.retrieval_attempts += 1
    state.reasoning_steps.append(
        AgentStep("retrieve", "done", f"Retrieved {len(state.sources)} chunks for `{active_query}`.")
    )


def _grade_documents(state: AgentState) -> None:
    if state.sources and state.sources[0].score >= 0.08:
        state.route = "generate_answer"
        state.reasoning_steps.append(AgentStep("grade_documents", "relevant", "Top chunk passed local relevance threshold."))
        return
    state.route = "rewrite_query"
    state.reasoning_steps.append(AgentStep("grade_documents", "weak", "Retrieved context was missing or weak."))


def _rewrite_query(state: AgentState) -> None:
    terms = list(_keywords(state.query))
    state.rewritten_query = " ".join(terms[:8])
    state.reasoning_steps.append(AgentStep("rewrite_query", "done", f"Rewritten query: `{state.rewritten_query}`."))


def _generate_answer(state: AgentState) -> str:
    if not state.sources:
        state.reasoning_steps.append(AgentStep("generate_answer", "no_context", "No source chunks available."))
        return "I could not find enough imported paper context to answer. Try importing a more relevant paper first."
    source = state.sources[0]
    state.reasoning_steps.append(AgentStep("generate_answer", "done", f"Answered from {source.chunk_id}."))
    return (
        f"From `{source.title}`, the strongest retrieved evidence is in {source.section.lower()}: "
        f"{source.text[:520]}{'...' if len(source.text) > 520 else ''}"
    )


def _score(query_terms: set[str], doc_terms: set[str]) -> float:
    if not query_terms or not doc_terms:
        return 0.0
    return len(query_terms & doc_terms) / len(query_terms)


def _keywords(text: str) -> set[str]:
    stop = {"the", "and", "for", "with", "from", "that", "this", "into", "using", "what", "how", "why"}
    return {word for word in re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", text.lower()) if word not in stop}
