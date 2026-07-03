"""Cross-buddy signal bus (ARCHITECTURE.md §3.4).

Small internal events table (emitter, kind, payload, created_at); each buddy service
subscribes to the kinds it cares about. Only coarse signals cross the mental-health
boundary (e.g. ``stress_trend: high``), never check-in content.
"""

from __future__ import annotations
