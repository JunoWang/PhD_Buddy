from pathlib import Path

from fastapi.testclient import TestClient

from phd_buddy.app import app
from phd_buddy.routers import auth as auth_router
from phd_buddy.routers import profile as profile_router


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
