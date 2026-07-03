from pathlib import Path

from phd_buddy.services.profile import OnboardingPlan, ResearchProfile, load_plan, render_markdown, save_plan


def sample_profile() -> ResearchProfile:
    return ResearchProfile(
        major_field="Machine Learning",
        subdomains=["Information Retrieval", "NLP"],
        venues=["ACL", "CHI"],
        google_scholar_url="https://scholar.google.com/citations?user=test",
        known_seed_papers=["Paper A", "Paper B"],
        recent_keywords=["agentic search", "citation verification"],
    )


def test_plan_contains_onboarding_tracks() -> None:
    plan = OnboardingPlan.from_profile(sample_profile())

    assert "walk the citation graph" in plan.workflow["foundational_lineage"]["instruction"]
    assert "re-rank by relevance" in plan.workflow["recent_search"]["instruction"]
    assert plan.workflow["summary_track"]["depth"] == "summary"
    assert plan.workflow["deep_dive_track"]["depth"] == "deep_dive"
    assert "grounded" in plan.deep_dive_harness["grounding_rules"]


def test_save_plan_writes_json_and_markdown(tmp_path: Path) -> None:
    plan = OnboardingPlan.from_profile(sample_profile())

    json_path, markdown_path = save_plan(plan, tmp_path)

    assert json_path.exists()
    assert markdown_path.exists()
    loaded = load_plan(json_path)
    assert loaded.profile.major_field == "Machine Learning"
    assert loaded.profile.subdomains == ["Information Retrieval", "NLP"]
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "## Research Identity" in markdown
    assert "## Generated Onboarding Workflow" not in markdown


def test_markdown_includes_student_facing_fields() -> None:
    markdown = render_markdown(OnboardingPlan.from_profile(sample_profile()))

    assert markdown.startswith("# PhD Buddy Onboarding Profile")
    assert "Major field: Machine Learning" in markdown
    assert "- ACL" in markdown
    assert "- Paper A" in markdown
    assert "Deep Dive Harness" not in markdown
