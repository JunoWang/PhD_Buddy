from pathlib import Path

from fastapi.testclient import TestClient

from phd_buddy.app import app
from phd_buddy.routers import profile as profile_router


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
