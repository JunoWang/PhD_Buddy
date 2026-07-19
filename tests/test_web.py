from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from phd_buddy.app import app
from phd_buddy.routers import auth as auth_router
from phd_buddy.routers import profile as profile_router
from phd_buddy.routers import reading as reading_router
from phd_buddy.routers import research as research_router
from phd_buddy.storage.models import Paper, PaperAsset


def test_signup_and_signin_use_local_user_store(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(auth_router, "DEFAULT_USERS_PATH", tmp_path / "users.json")
    client = TestClient(app)

    signup = client.post(
        "/api/auth/signup",
        json={"email": "Student@School.edu", "password": "password123", "name": "Juno Wang"},
    )

    assert signup.status_code == 200
    assert signup.json()["user"]["email"] == "student@school.edu"
    assert signup.json()["session_token"]
    assert (tmp_path / "users.json").exists()

    signin = client.post(
        "/api/auth/signin",
        json={"email": "student@school.edu", "password": "password123"},
    )

    assert signin.status_code == 200
    assert signin.json()["user"]["name"] == "Juno Wang"


def test_create_onboarding_writes_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(profile_router, "DEFAULT_OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(profile_router, "DEFAULT_PROFILE_PATH", tmp_path / "onboarding_profile.json")
    client = TestClient(app)

    response = client.post(
        "/api/onboarding",
        json={
            "major_field": "Machine Learning",
            "subdomains": ["Information Retrieval", "NLP"],
            "venues": ["ACL"],
            "google_scholar_url": "https://scholar.google.com/citations?user=test",
            "known_seed_papers": ["Paper A"],
            "recent_keywords": ["agentic search"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["plan"]["profile"]["major_field"] == "Machine Learning"
    assert payload["plan"]["profile"]["subdomains"] == ["Information Retrieval", "NLP"]
    assert "PhD Buddy Onboarding Profile" in payload["markdown"]
    assert (tmp_path / "onboarding_profile.json").exists()
    assert (tmp_path / "onboarding_profile.md").exists()
    assert list((tmp_path / "fundamental_papers").glob("*/summarize.md"))


def test_create_onboarding_accepts_skipped_fields(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(profile_router, "DEFAULT_OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(profile_router, "DEFAULT_PROFILE_PATH", tmp_path / "onboarding_profile.json")
    client = TestClient(app)

    response = client.post("/api/onboarding", json={"major_field": "AI", "subdomains": ["In-context learning"]})

    assert response.status_code == 200
    payload = response.json()
    assert payload["plan"]["profile"]["major_field"] == "AI"
    assert payload["plan"]["fundamental_papers"]
    assert "Fundamental Paper Starter Set" in payload["markdown"]


def test_research_chat_uses_latest_onboarding(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(profile_router, "DEFAULT_OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(profile_router, "DEFAULT_PROFILE_PATH", tmp_path / "onboarding_profile.json")
    monkeypatch.setattr(research_router, "DEFAULT_PROFILE_PATH", tmp_path / "onboarding_profile.json")
    client = TestClient(app)

    client.post("/api/onboarding", json={"major_field": "AI", "subdomains": ["In-context learning"]})
    response = client.post(
        "/api/research/chat",
        json={"message": "Which paper should I read first?", "first_goal": "plan first paper summary"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "AI / In-context learning" in payload["message"]
    assert payload["suggested_actions"]
    assert payload["referenced_papers"]


def test_research_chat_requires_onboarding(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(research_router, "DEFAULT_PROFILE_PATH", tmp_path / "missing.json")
    client = TestClient(app)

    response = client.post("/api/research/chat", json={"message": "Where do I start?"})

    assert response.status_code == 404


def test_latest_onboarding_returns_404_when_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(profile_router, "DEFAULT_OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(profile_router, "DEFAULT_PROFILE_PATH", tmp_path / "onboarding_profile.json")
    client = TestClient(app)

    response = client.get("/api/onboarding/latest")

    assert response.status_code == 404


def test_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_reader_exposes_full_markdown_and_original_pdf(tmp_path: Path, monkeypatch) -> None:
    markdown_path = tmp_path / "paper.md"
    markdown = "# Complete Paper\n\n## Page 1\n\nThe complete readable text.\n"
    markdown_path.write_text(markdown, encoding="utf-8")
    pdf_path = tmp_path / "paper.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with pdf_path.open("wb") as pdf_file:
        writer.write(pdf_file)

    paper = Paper(
        paper_id="paper-complete",
        title="Complete Paper",
        authors=["Ada Lovelace"],
        year="2026",
        assets=[
            PaperAsset(kind="markdown", uri=str(markdown_path), created_at="now"),
            PaperAsset(kind="pdf", uri=str(pdf_path), created_at="now"),
        ],
    )
    monkeypatch.setattr(reading_router, "load_paper", lambda paper_id: paper if paper_id == paper.paper_id else None)
    client = TestClient(app)

    content = client.get("/api/reading/papers/paper-complete/content")
    original = client.get("/api/reading/papers/paper-complete/pdf")

    assert content.status_code == 200
    assert content.json()["markdown"] == markdown
    assert content.json()["page_count"] == 1
    assert content.json()["source_pdf_available"] is True
    assert original.status_code == 200
    assert original.headers["content-type"] == "application/pdf"
    assert original.headers["content-disposition"].startswith("inline")
