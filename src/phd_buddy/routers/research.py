"""Research Buddy chat endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.profile import load_plan
from ..services.research_chat import reply_to_research_chat


DEFAULT_PROFILE_PATH = Path("vault/onboarding/onboarding_profile.json")

router = APIRouter(prefix="/api/research", tags=["research"])


class ResearchChatRequest(BaseModel):
    message: str = ""
    first_goal: str = ""


@router.post("/chat")
def research_chat(payload: ResearchChatRequest) -> dict[str, Any]:
    if not DEFAULT_PROFILE_PATH.exists():
        raise HTTPException(status_code=404, detail="Save onboarding before starting Research Buddy chat.")
    plan = load_plan(DEFAULT_PROFILE_PATH)
    return reply_to_research_chat(plan, payload.message, payload.first_goal).to_dict()
