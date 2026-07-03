"""FastAPI application factory and router registration (ARCHITECTURE.md §4)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .routers import ALL_ROUTERS

PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_DIR / "static"


def create_app() -> FastAPI:
    app = FastAPI(title="PhD Buddy", version="0.1.0")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    for router in ALL_ROUTERS:
        app.include_router(router)

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
