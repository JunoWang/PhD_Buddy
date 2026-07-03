"""Notification channels: in-app inbox + web push (PWA) now; native push later.

All user-facing pings (digests, reminders, check-ins) flow through this interface so
the mobile app can plug in without touching buddy logic (ARCHITECTURE.md §7).
"""

from __future__ import annotations
