"""Local auth endpoints for the first web onboarding flow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services import auth


DEFAULT_USERS_PATH = Path("vault/auth/users.json")

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    name: str = ""


@router.post("/signup")
def signup(payload: AuthRequest) -> dict[str, Any]:
    try:
        user = auth.signup(payload.email, payload.password, payload.name, DEFAULT_USERS_PATH)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"user": user.public_dict(), "session_token": auth.issue_session_token()}


@router.post("/signin")
def signin(payload: AuthRequest) -> dict[str, Any]:
    try:
        user = auth.signin(payload.email, payload.password, DEFAULT_USERS_PATH)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {"user": user.public_dict(), "session_token": auth.issue_session_token()}
