from pathlib import Path

from fastapi.testclient import TestClient

from phd_buddy.app import app
from phd_buddy.routers import library as library_router
from phd_buddy.routers import reading as reading_router
from phd_buddy.services import library as library_service
from phd_buddy.services.discovery import parse_arxiv_feed
from phd_buddy.services.library import import_paper, load_paper, save_paper
from phd_buddy.services.paper_rag import ask_agentic, index_paper_chunks, retrieve_chunks
from phd_buddy.storage.models import Paper, PaperAsset


ARXIV_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2401.00001v1</id>
    <title>Agentic Retrieval for Research Papers</title>
    <summary>We study retrieval augmented generation for academic paper reading and citation grounded answers.</summary>
    <published>2024-01-01T00:00:00Z</published>
    <author><name>Ada Lovelace</name></author>
    <author><name>Grace Hopper</name></author>
    <link title="pdf" href="http://arxiv.org/pdf/2401.00001v1" type="application/pdf"/>
  </entry>
</feed>
"""


def test_parse_arxiv_feed_normalizes_candidates() -> None:
    candidates = parse_arxiv_feed(ARXIV_FEED)

    assert len(candidates) == 1
    assert candidates[0].title == "Agentic Retrieval for Research Papers"
    assert candidates[0].authors == ["Ada Lovelace", "Grace Hopper"]
    assert candidates[0].year == "2024"
    assert candidates[0].external_ids["arxiv"] == "2401.00001v1"
    assert candidates[0].pdf_url.endswith("2401.00001v1")


def test_import_paper_writes_local_library(tmp_path: Path) -> None:
    paper = import_paper(
        {
            "title": "Agentic Retrieval for Research Papers",
            "authors": ["Ada Lovelace"],
            "year": "2024",
            "abstract": "Retrieval augmented generation for paper reading.",
            "source": "arxiv",
            "external_ids": {"arxiv": "2401.00001v1"},
            "pdf_url": "http://arxiv.org/pdf/2401.00001v1",
        },
        tmp_path,
    )

    loaded = load_paper(paper.paper_id, tmp_path)
    assert loaded is not None
    assert loaded.title == paper.title
    assert loaded.assets[0].kind == "metadata"
    assert (tmp_path / "papers.json").exists()


def test_library_api_search_and_import(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(library_router, "DEFAULT_LIBRARY_DIR", tmp_path)
    monkeypatch.setattr(library_service, "DEFAULT_LIBRARY_DIR", tmp_path)
    monkeypatch.setattr(
        library_router.discovery,
        "search_arxiv",
        lambda query, max_results=10: parse_arxiv_feed(ARXIV_FEED),
    )
    client = TestClient(app)

    search = client.post("/api/library/search", json={"query": "agentic retrieval", "use_onboarding": False})
    assert search.status_code == 200
    result = search.json()["results"][0]

    imported = client.post("/api/library/papers/import", json=result)
    assert imported.status_code == 200
    paper_id = imported.json()["paper"]["paper_id"]

    detail = client.get(f"/api/library/papers/{paper_id}")
    assert detail.status_code == 200
    assert detail.json()["paper"]["title"] == "Agentic Retrieval for Research Papers"


def test_local_agentic_rag_pipeline(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(library_service, "DEFAULT_LIBRARY_DIR", tmp_path)
    paper = import_paper(
        {
            "title": "Agentic Retrieval for Research Papers",
            "authors": ["Ada Lovelace"],
            "year": "2024",
            "abstract": "Retrieval augmented generation helps answer paper questions with grounded citation context.",
            "source": "arxiv",
            "external_ids": {"arxiv": "2401.00001v1"},
        },
        tmp_path,
    )

    indexed = index_paper_chunks(paper.paper_id, "The method retrieves chunks, grades relevance, and rewrites weak queries.")
    chunks = retrieve_chunks("How does retrieval augmented generation answer paper questions?")
    result = ask_agentic("How does retrieval augmented generation answer paper questions?")

    assert indexed.chunks
    assert chunks
    assert result.sources
    assert [step.node for step in result.reasoning_steps] == [
        "guardrail",
        "retrieve",
        "grade_documents",
        "generate_answer",
    ]


def test_paper_markdown_endpoint_and_indexing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(library_service, "DEFAULT_LIBRARY_DIR", tmp_path)
    markdown_path = tmp_path / "paper-test" / "paper.md"
    markdown_path.parent.mkdir(parents=True)
    markdown_path.write_text("# Test Paper\n\n## Method\n\nThe method uses graph retrieval and markdown chunks.", encoding="utf-8")
    paper = Paper(
        paper_id="paper-test",
        title="Test Paper",
        authors=["Ada Lovelace"],
        year="2024",
        abstract="",
        assets=[PaperAsset(kind="markdown", uri=str(markdown_path), created_at="now")],
    )
    save_paper(paper, tmp_path)
    client = TestClient(app)

    indexed = index_paper_chunks("paper-test")
    response = client.get("/api/reading/papers/paper-test/markdown")

    assert response.status_code == 200
    assert "graph retrieval" in response.text
    assert indexed.chunks
    assert "markdown chunks" in indexed.chunks[0].text
