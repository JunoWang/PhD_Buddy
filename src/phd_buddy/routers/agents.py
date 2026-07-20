"""Unified LangGraph API for cross-buddy conversations."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.buddy_graph import read_buddy_thread, run_buddy_graph

router = APIRouter(prefix="/api/agents", tags=["agents"])


class BuddyChatRequest(BaseModel):
    message: str = Field(min_length=1)
    thread_id: str = ""
    paper_id: str = ""
    reading_context: dict[str, Any] = Field(default_factory=dict)


@router.post("/chat")
def buddy_chat(payload: BuddyChatRequest) -> dict[str, Any]:
    try:
        return run_buddy_graph(
            payload.message,
            thread_id=payload.thread_id,
            paper_id=payload.paper_id,
            reading_context=payload.reading_context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/threads/{thread_id}")
def buddy_thread(thread_id: str) -> dict[str, Any]:
    thread = read_buddy_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Agent thread not found.")
    return thread
