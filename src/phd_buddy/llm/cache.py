"""LLM-output cache keyed by content hash + harness version (ARCHITECTURE.md §6).

Every LLM artifact is cached so a re-read costs $0. Implemented in Phase 1 together
with the summary track.
"""

from __future__ import annotations
