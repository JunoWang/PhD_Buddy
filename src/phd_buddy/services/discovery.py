"""Research buddy: foundational lineage + recent search + re-rank (Phase 1).

Walks the citation graph from seed papers and expands recent-search queries via
Semantic Scholar, then re-ranks candidates by relevance (ARCHITECTURE.md §3.1).
"""

from __future__ import annotations
