"""Onboarding profile endpoints (moved from the original ``phd_buddy.web``)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from ..services.profile import (
    OnboardingPlan,
    ResearchProfile,
    load_plan,
    render_markdown,
    save_plan,
)


DEFAULT_OUTPUT_DIR = Path("vault/onboarding")
DEFAULT_PROFILE_PATH = DEFAULT_OUTPUT_DIR / "onboarding_profile.json"

router = APIRouter(prefix="/api/onboarding", tags=["profile"])


class ResearchProfileRequest(BaseModel):
    major_field: str = ""
    subdomains: list[str] = Field(default_factory=list)
    venues: list[str] = Field(default_factory=list)
    name: str = ""
    preferred_name: str = ""
    sex: str = ""
    age: str = ""
    school: str = ""
    department: str = ""
    degree_stage: str = ""
    advisor: str = ""
    milestones: list[str] = Field(default_factory=list)
    current_goals: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    notification_preferences: list[str] = Field(default_factory=list)
    weekly_availability: str = ""
    google_scholar_url: str = ""
    known_seed_papers: list[str] = Field(default_factory=list)
    recent_keywords: list[str] = Field(default_factory=list)

    def to_profile(self) -> ResearchProfile:
        raw = self.model_dump()
        raw["student"] = {
            "name": raw.pop("name"),
            "preferred_name": raw.pop("preferred_name"),
            "sex": raw.pop("sex"),
            "age": raw.pop("age"),
            "school": raw.pop("school"),
            "department": raw.pop("department"),
            "degree_stage": raw.pop("degree_stage"),
            "advisor": raw.pop("advisor"),
            "milestones": raw.pop("milestones"),
            "current_goals": raw.pop("current_goals"),
            "pain_points": raw.pop("pain_points"),
            "notification_preferences": raw.pop("notification_preferences"),
            "weekly_availability": raw.pop("weekly_availability"),
        }
        return ResearchProfile.from_dict(raw)


@router.post("")
def create_onboarding(payload: ResearchProfileRequest) -> dict[str, Any]:
    plan = OnboardingPlan.from_profile(payload.to_profile())
    json_path, markdown_path = save_plan(plan, DEFAULT_OUTPUT_DIR)
    return {
        "plan": plan.to_dict(),
        "paths": {
            "json": str(json_path),
            "markdown": str(markdown_path),
        },
        "markdown": render_markdown(plan),
    }


@router.get("/latest")
def latest_onboarding() -> dict[str, Any]:
    if not DEFAULT_PROFILE_PATH.exists():
        raise HTTPException(status_code=404, detail="No onboarding profile has been saved yet.")
    plan = load_plan(DEFAULT_PROFILE_PATH)
    return {
        "plan": plan.to_dict(),
        "paths": {
            "json": str(DEFAULT_PROFILE_PATH),
            "markdown": str(DEFAULT_OUTPUT_DIR / "onboarding_profile.md"),
        },
        "markdown": render_markdown(plan),
    }


@router.get("/latest/markdown", response_class=PlainTextResponse)
def latest_onboarding_markdown() -> str:
    if not DEFAULT_PROFILE_PATH.exists():
        raise HTTPException(status_code=404, detail="No onboarding profile has been saved yet.")
    return render_markdown(load_plan(DEFAULT_PROFILE_PATH))
