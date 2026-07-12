"""Research buddy: foundational lineage + recent search + re-rank (Phase 1).

Walks the citation graph from seed papers and expands recent-search queries via
Semantic Scholar, then re-ranks candidates by relevance (ARCHITECTURE.md §3.1).
"""

from __future__ import annotations

import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

from .profile import OnboardingPlan


ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


@dataclass(frozen=True)
class PaperCandidate:
    """Normalized search result before local import."""

    title: str
    authors: list[str]
    year: str
    abstract: str = ""
    venue: str = "arXiv"
    source: str = "arxiv"
    external_ids: dict[str, str] = field(default_factory=dict)
    pdf_url: str = ""
    landing_url: str = ""
    relevance_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "abstract": self.abstract,
            "venue": self.venue,
            "source": self.source,
            "external_ids": self.external_ids,
            "pdf_url": self.pdf_url,
            "landing_url": self.landing_url,
            "relevance_score": self.relevance_score,
            "verification_status": "unverified",
        }


def search_arxiv(query: str, *, max_results: int = 10, opener: Any | None = None) -> list[PaperCandidate]:
    """Search arXiv and return normalized candidates."""

    query = query.strip()
    if not query:
        return []

    params = urllib.parse.urlencode(
        {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
    )
    url = f"{ARXIV_API_URL}?{params}"
    open_url = opener or urllib.request.urlopen
    with open_url(url, timeout=10) as response:
        body = response.read()
    return parse_arxiv_feed(body)


def search_from_onboarding(plan: OnboardingPlan, *, max_results: int = 10) -> list[PaperCandidate]:
    profile = plan.profile
    query = " ".join(
        item
        for item in [profile.major_field, *profile.subdomains, *profile.recent_keywords]
        if item
    )
    candidates = search_arxiv(query, max_results=max_results)
    return rerank_candidates(candidates, [profile.major_field, *profile.subdomains, *profile.recent_keywords])


def parse_arxiv_feed(body: bytes | str) -> list[PaperCandidate]:
    root = ET.fromstring(body)
    candidates: list[PaperCandidate] = []
    for entry in root.findall("atom:entry", ATOM):
        title = _clean_text(entry.findtext("atom:title", default="", namespaces=ATOM))
        abstract = _clean_text(entry.findtext("atom:summary", default="", namespaces=ATOM))
        published = entry.findtext("atom:published", default="", namespaces=ATOM)
        landing_url = entry.findtext("atom:id", default="", namespaces=ATOM).strip()
        arxiv_id = landing_url.rstrip("/").split("/")[-1]
        authors = [
            _clean_text(author.findtext("atom:name", default="", namespaces=ATOM))
            for author in entry.findall("atom:author", ATOM)
        ]
        pdf_url = ""
        for link in entry.findall("atom:link", ATOM):
            if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                pdf_url = link.attrib.get("href", "")
                break
        candidates.append(
            PaperCandidate(
                title=title,
                authors=[author for author in authors if author],
                year=published[:4],
                abstract=abstract,
                external_ids={"arxiv": arxiv_id} if arxiv_id else {},
                pdf_url=pdf_url,
                landing_url=landing_url,
            )
        )
    return candidates


def rerank_candidates(candidates: list[PaperCandidate], terms: list[str]) -> list[PaperCandidate]:
    keywords = _keywords(" ".join(terms))
    scored = []
    for candidate in candidates:
        haystack = _keywords(f"{candidate.title} {candidate.abstract}")
        if not keywords:
            score = 0.0
        else:
            score = len(keywords & haystack) / len(keywords)
        scored.append(
            PaperCandidate(
                title=candidate.title,
                authors=candidate.authors,
                year=candidate.year,
                abstract=candidate.abstract,
                venue=candidate.venue,
                source=candidate.source,
                external_ids=candidate.external_ids,
                pdf_url=candidate.pdf_url,
                landing_url=candidate.landing_url,
                relevance_score=round(score, 4),
            )
        )
    return sorted(scored, key=lambda item: item.relevance_score, reverse=True)


def _keywords(text: str) -> set[str]:
    stop = {"the", "and", "for", "with", "from", "that", "this", "into", "using", "use", "paper"}
    return {word for word in re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", text.lower()) if word not in stop}


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
