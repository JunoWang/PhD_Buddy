"""LangGraph supervisor connecting Research, Task, and Mental Buddy workflows."""

from __future__ import annotations

import operator
import os
from pathlib import Path
from typing import Annotated, Any, Literal, TypedDict
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from ..storage.db import DEFAULT_DB_PATH, connect_database
from . import events
from .paper_rag import ask_agentic

BuddyRoute = Literal["research", "task", "mental", "mental_task"]


class BuddyState(TypedDict, total=False):
    messages: Annotated[list[dict[str, str]], operator.add]
    query: str
    paper_id: str
    reading_context: dict[str, Any]
    route: BuddyRoute
    response: str
    research_response: str
    task_response: str
    mental_response: str
    sources: list[dict[str, Any]]
    reasoning_steps: list[dict[str, str]]
    suggested_actions: list[str]
    buddies: list[str]


def classify_buddy_intent(message: str, *, paper_id: str = "") -> BuddyRoute:
    terms = set(message.lower().replace("-", " ").split())
    mental_terms = {
        "anxious",
        "anxiety",
        "burned",
        "burnout",
        "depressed",
        "exhausted",
        "overwhelmed",
        "panic",
        "stressed",
        "stress",
        "unsafe",
    }
    task_terms = {
        "assignment",
        "deadline",
        "milestone",
        "plan",
        "schedule",
        "task",
        "tasks",
        "todo",
        "week",
    }
    has_mental = bool(terms & mental_terms)
    has_task = bool(terms & task_terms)
    if has_mental and has_task:
        return "mental_task"
    if has_mental:
        return "mental"
    if has_task and not paper_id:
        return "task"
    return "research"


def build_buddy_graph(checkpointer: SqliteSaver):
    builder = StateGraph(BuddyState)
    builder.add_node("classify", _classify_node)
    builder.add_node("research_buddy", _research_node)
    builder.add_node("task_buddy", _task_node)
    builder.add_node("mental_buddy", _mental_node)
    builder.add_node("finalize", _finalize_node)
    builder.add_edge(START, "classify")
    builder.add_conditional_edges(
        "classify",
        lambda state: state["route"],
        {
            "research": "research_buddy",
            "task": "task_buddy",
            "mental": "mental_buddy",
            "mental_task": "mental_buddy",
        },
    )
    builder.add_edge("research_buddy", "finalize")
    builder.add_edge("task_buddy", "finalize")
    builder.add_conditional_edges(
        "mental_buddy",
        lambda state: "task_buddy" if state["route"] == "mental_task" else "finalize",
    )
    builder.add_edge("finalize", END)
    return builder.compile(checkpointer=checkpointer)


def run_buddy_graph(
    message: str,
    *,
    thread_id: str = "",
    paper_id: str = "",
    reading_context: dict[str, Any] | None = None,
    database_path: Path | None = None,
) -> dict[str, Any]:
    query = message.strip()
    if not query:
        raise ValueError("Message cannot be empty")
    active_thread_id = thread_id.strip() or str(uuid4())
    db_path = database_path or DEFAULT_DB_PATH
    os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")
    connection = connect_database(db_path)
    try:
        checkpointer = SqliteSaver(connection)
        graph = build_buddy_graph(checkpointer)
        result = graph.invoke(
            {
                "messages": [{"role": "user", "content": query}],
                "query": query,
                "paper_id": paper_id,
                "reading_context": reading_context or {},
            },
            {"configurable": {"thread_id": active_thread_id}},
        )
    finally:
        connection.close()

    events.emit(
        active_thread_id,
        "supervisor",
        "buddy_response",
        {"route": result["route"], "buddies": result.get("buddies", [])},
        database_path=db_path,
    )
    return {
        "thread_id": active_thread_id,
        "route": result["route"],
        "buddies": result.get("buddies", []),
        "answer": result.get("response", ""),
        "sources": result.get("sources", []),
        "reasoning_steps": result.get("reasoning_steps", []),
        "suggested_actions": result.get("suggested_actions", []),
        "reading_context": result.get("reading_context", {}),
    }


def read_buddy_thread(
    thread_id: str,
    *,
    database_path: Path | None = None,
) -> dict[str, Any] | None:
    connection = connect_database(database_path or DEFAULT_DB_PATH)
    try:
        graph = build_buddy_graph(SqliteSaver(connection))
        snapshot = graph.get_state({"configurable": {"thread_id": thread_id}})
        if not snapshot.values:
            return None
        return {
            "thread_id": thread_id,
            "route": snapshot.values.get("route", ""),
            "messages": snapshot.values.get("messages", []),
            "buddies": snapshot.values.get("buddies", []),
        }
    finally:
        connection.close()


def _classify_node(state: BuddyState) -> dict[str, Any]:
    return {"route": classify_buddy_intent(state["query"], paper_id=state.get("paper_id", ""))}


def _research_node(state: BuddyState) -> dict[str, Any]:
    query = _conversation_aware_query(state)
    context = state.get("reading_context", {})
    if context:
        anchor = " ".join(
            str(context.get(key, ""))
            for key in ("section", "page_number", "visible_element_id")
            if context.get(key)
        )
        if anchor:
            query = f"{query} Reading location: {anchor}."
    result = ask_agentic(query, paper_id=state.get("paper_id", ""))
    payload = result.to_dict()
    return {
        "research_response": payload["answer"],
        "sources": payload["sources"],
        "reasoning_steps": payload["reasoning_steps"],
        "suggested_actions": ["Open the strongest cited source in the paper."],
    }


def _task_node(state: BuddyState) -> dict[str, Any]:
    query = state["query"]
    if state["route"] == "mental_task":
        response = (
            "Task Buddy can reduce the load: choose one must-do outcome, split it into a 25-minute "
            "first step, and move everything else into a later queue. This remains a draft until you confirm it."
        )
        actions = ["Name the one must-do outcome.", "Confirm or edit the proposed 25-minute first step."]
    else:
        response = (
            f"Task Buddy received: “{query}” I would turn this into a draft assignment with a clear outcome, "
            "deadline, and first 25-minute step. Confirm the details before it is scheduled."
        )
        actions = ["Add the deadline.", "Confirm the first step."]
    return {"task_response": response, "suggested_actions": actions}


def _mental_node(state: BuddyState) -> dict[str, Any]:
    lower = state["query"].lower()
    crisis_terms = ("suicide", "kill myself", "self-harm", "hurt myself", "immediate danger")
    if any(term in lower for term in crisis_terms):
        response = (
            "Your safety matters more than the work. Please contact local emergency services or a crisis line "
            "now, and reach out to someone you trust who can stay with you. I will not use an AI-generated "
            "intervention for an immediate-safety situation."
        )
    else:
        response = (
            "Mental Buddy hears that the workload feels heavy. Pause for one slow breath, then choose whether "
            "you want a lighter plan, a short break, or to talk through what is making this feel difficult."
        )
    return {"mental_response": response}


def _finalize_node(state: BuddyState) -> dict[str, Any]:
    route = state["route"]
    if route == "mental_task":
        parts = [state.get("mental_response", ""), state.get("task_response", "")]
        buddies = ["mental", "task"]
    elif route == "mental":
        parts = [state.get("mental_response", "")]
        buddies = ["mental"]
    elif route == "task":
        parts = [state.get("task_response", "")]
        buddies = ["task"]
    else:
        parts = [state.get("research_response", "")]
        buddies = ["research"]
    response = "\n\n".join(part for part in parts if part)
    return {
        "response": response,
        "buddies": buddies,
        "messages": [{"role": "assistant", "content": response}],
    }


def _conversation_aware_query(state: BuddyState) -> str:
    query = state["query"]
    follow_up_terms = ("that", "those", "previous", "it", "they", "this")
    if not any(term in query.lower().split() for term in follow_up_terms):
        return query
    previous = [message["content"] for message in state.get("messages", [])[:-1]][-2:]
    if not previous:
        return query
    return f"Previous conversation: {' '.join(previous)} Follow-up question: {query}"
