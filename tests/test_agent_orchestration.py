from pathlib import Path

from fastapi.testclient import TestClient

from phd_buddy.app import app
from phd_buddy.routers import agents as agents_router
from phd_buddy.services import ingestion
from phd_buddy.services.buddy_graph import (
    classify_buddy_intent,
    read_buddy_thread,
    run_buddy_graph,
)


def test_langgraph_routes_mental_then_task_and_keeps_thread_memory(tmp_path: Path) -> None:
    database_path = tmp_path / "phd_buddy.sqlite3"

    first = run_buddy_graph(
        "I am overwhelmed by my deadline and task list",
        database_path=database_path,
    )
    second = run_buddy_graph(
        "Can you make the task smaller?",
        thread_id=first["thread_id"],
        database_path=database_path,
    )
    thread = read_buddy_thread(first["thread_id"], database_path=database_path)

    assert first["route"] == "mental_task"
    assert first["buddies"] == ["mental", "task"]
    assert second["route"] == "task"
    assert thread is not None
    assert [message["role"] for message in thread["messages"]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]


def test_selected_paper_keeps_planning_question_with_research_buddy() -> None:
    assert classify_buddy_intent("Make a reading plan", paper_id="paper-1") == "research"
    assert classify_buddy_intent("Schedule my week") == "task"
    assert classify_buddy_intent("I feel stressed") == "mental"


def test_agent_api_exposes_unified_chat_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        agents_router,
        "run_buddy_graph",
        lambda message, **kwargs: {
            "thread_id": "thread-test",
            "route": "research",
            "buddies": ["research"],
            "answer": f"Grounded response to {message}",
            "sources": [],
            "reasoning_steps": [],
            "suggested_actions": [],
            "reading_context": kwargs["reading_context"],
        },
    )
    client = TestClient(app)

    response = client.post(
        "/api/agents/chat",
        json={
            "message": "Explain this table",
            "paper_id": "paper-1",
            "reading_context": {"page_number": 9, "visible_element_id": "table-2-page-9"},
        },
    )

    assert response.status_code == 200
    assert response.json()["thread_id"] == "thread-test"
    assert response.json()["reading_context"]["visible_element_id"] == "table-2-page-9"


def test_ingestion_report_and_scoped_cleanup(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(ingestion, "DEFAULT_INGESTION_DIR", tmp_path)
    first = ingestion.write_ingestion_report({}, {"acquired": []}, {"indexed": {}})
    second = ingestion.write_ingestion_report({}, {"acquired": []}, {"indexed": {}})

    cleanup = ingestion.cleanup_ingestion_artifacts(keep=1)

    assert len(cleanup["removed"]) == 1
    assert sum(Path(item["path"]).exists() for item in (first, second)) == 1
