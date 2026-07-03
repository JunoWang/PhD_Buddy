"""Database session and engine management.

Phase 1 (ARCHITECTURE.md §5): SQLModel on SQLite; Postgres + pgvector only when
multi-device sync is needed (Phase 5). No engine exists yet — the onboarding slice
persists through the vault alone.
"""

from __future__ import annotations
