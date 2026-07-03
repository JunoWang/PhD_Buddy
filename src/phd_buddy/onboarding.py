"""Onboarding workflow primitives for PhD Buddy."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


GROUNDING_RULES = {
    "grounded": "Stated in the paper; assert plainly and cite section, figure, table, or short phrase.",
    "inferred": "Assistant reasoning about the paper; flag as 'my read' and invite verification.",
    "external": "General knowledge outside the paper; flag as lower-confidence and ask the student to verify.",
}

DEEP_DIVE_LENSES = [
    "Where it sits",
    "The problem",
    "Baselines",
    "Why baselines fall short",
    "The method, with a concrete example",
    "Pros and cons",
    "Experiments vs. claims",
    "Generalizability",
]


@dataclass(frozen=True)
class ResearchProfile:
    """The student-facing profile fields collected during onboarding."""

    major_field: str
    subdomains: list[str]
    venues: list[str]
    google_scholar_url: str = ""
    known_seed_papers: list[str] = field(default_factory=list)
    recent_keywords: list[str] = field(default_factory=list)

    @property
    def research_identity(self) -> str:
        subdomains = ", ".join(self.subdomains) if self.subdomains else "unspecified subdomain"
        return f"{self.major_field} -> {subdomains}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "major_field": self.major_field,
            "subdomains": self.subdomains,
            "venues": self.venues,
            "google_scholar_url": self.google_scholar_url,
            "known_seed_papers": self.known_seed_papers,
            "recent_keywords": self.recent_keywords,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ResearchProfile:
        return cls(
            major_field=str(raw.get("major_field", raw.get("field", ""))).strip(),
            subdomains=_clean_list(raw.get("subdomains", [raw.get("sub_area"), raw.get("topic")])),
            venues=_clean_list(raw.get("venues", [raw.get("venue")])),
            google_scholar_url=str(raw.get("google_scholar_url", "")).strip(),
            known_seed_papers=_clean_list(raw.get("known_seed_papers", [])),
            recent_keywords=_clean_list(raw.get("recent_keywords", [])),
        )


@dataclass(frozen=True)
class OnboardingPlan:
    """A generated first-pass plan from the onboarding profile."""

    profile_id: str
    created_at: str
    profile: ResearchProfile
    workflow: dict[str, Any]
    deep_dive_harness: dict[str, Any]

    @classmethod
    def from_profile(cls, profile: ResearchProfile) -> OnboardingPlan:
        return cls(
            profile_id=str(uuid4()),
            created_at=datetime.now(UTC).isoformat(),
            profile=profile,
            workflow=_workflow_for(profile),
            deep_dive_harness={
                "opening_lenses": DEEP_DIVE_LENSES,
                "grounding_rules": GROUNDING_RULES,
                "student_role": "The student verifies claims against the paper instead of passively accepting a summary.",
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "created_at": self.created_at,
            "profile": self.profile.to_dict(),
            "workflow": self.workflow,
            "deep_dive_harness": self.deep_dive_harness,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> OnboardingPlan:
        return cls(
            profile_id=str(raw["profile_id"]),
            created_at=str(raw["created_at"]),
            profile=ResearchProfile.from_dict(raw["profile"]),
            workflow=dict(raw["workflow"]),
            deep_dive_harness=dict(raw["deep_dive_harness"]),
        )


def save_plan(plan: OnboardingPlan, output_dir: Path) -> tuple[Path, Path]:
    """Write canonical JSON and vault-friendly markdown."""

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "onboarding_profile.json"
    markdown_path = output_dir / "onboarding_profile.md"

    json_path.write_text(
        json.dumps(plan.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(plan), encoding="utf-8")
    return json_path, markdown_path


def load_plan(path: Path) -> OnboardingPlan:
    return OnboardingPlan.from_dict(json.loads(path.read_text(encoding="utf-8")))


def render_markdown(plan: OnboardingPlan) -> str:
    profile = plan.profile
    subdomains = _markdown_list(profile.subdomains)
    venues = _markdown_list(profile.venues)
    scholar = profile.google_scholar_url or "Not provided"
    seeds = _markdown_list(profile.known_seed_papers)
    keywords = _markdown_list(profile.recent_keywords)

    return "\n".join(
        [
            "# PhD Buddy Onboarding Profile",
            "",
            f"Profile ID: `{plan.profile_id}`",
            f"Created: `{plan.created_at}`",
            "",
            "## Research Identity",
            "",
            f"- Major field: {profile.major_field}",
            f"- Google Scholar profile: {scholar}",
            "",
            "Subdomains:",
            subdomains,
            "",
            "Interested venues/conferences:",
            venues,
            "",
            "## Seed Inputs",
            "",
            "Known seed papers:",
            seeds,
            "",
            "Recent-search keywords:",
            keywords,
            "",
        ]
    )


def _workflow_for(profile: ResearchProfile) -> dict[str, Any]:
    return {
        "foundational_lineage": {
            "source": "onboarding_profile",
            "instruction": (
                "Start from known seed papers and walk the citation graph to identify "
                f"origins and landmarks for {profile.research_identity}."
            ),
            "inputs": profile.known_seed_papers,
        },
        "recent_search": {
            "source": "onboarding_profile",
            "instruction": (
                "Expand recent-search queries from the major field, subdomains, and venues; "
                "retrieve candidates through literature APIs; re-rank by relevance."
            ),
            "inputs": [profile.major_field, *profile.subdomains, *profile.venues, *profile.recent_keywords],
        },
        "student_publication_search": {
            "source": "onboarding_profile",
            "instruction": "Use the Google Scholar profile link, when provided, to inspect the student's publication history.",
            "input": profile.google_scholar_url,
        },
        "citation_verification": {
            "source": "system",
            "instruction": "Confirm title, authors, and year against real citations; flag unverified items.",
        },
        "acquisition": {
            "source": "system",
            "instruction": "Acquire open-access PDFs when available, convert to structure-aware markdown, and store PDF, markdown, and metadata together.",
        },
        "summary_track": {
            "source": "system",
            "instruction": "Create cheap one-pass summaries for broad scanning before deeper reading.",
            "depth": "summary",
        },
        "deep_dive_track": {
            "source": "system",
            "instruction": "Use the 8-point opening, constrained conversation, and three-bucket grounding for selected papers.",
            "depth": "deep_dive",
        },
        "dual_format_cache": {
            "source": "system",
            "instruction": "Persist one canonical JSON object plus student-facing prose and panel fields for the vault.",
        },
    }


def _clean_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = value.split(",")
    else:
        items = list(value)
    return [str(item).strip() for item in items if str(item).strip()]


def _markdown_list(items: list[str]) -> str:
    if not items:
        return "- None provided yet"
    return "\n".join(f"- {item}" for item in items)
