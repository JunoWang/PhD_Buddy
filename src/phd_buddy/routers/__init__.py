"""API routers, one module per feature surface (ARCHITECTURE.md §4).

Every feature ships as a JSON endpoint before it ships as a screen; the web SPA and
the later mobile app are both clients of these routers.
"""

from . import (
    auth,
    checkin,
    digest,
    ideas,
    jobs,
    library,
    profile,
    reading,
    research,
    schedule,
    support,
    tasks,
)

ALL_ROUTERS = [
    auth.router,
    profile.router,
    library.router,
    research.router,
    reading.router,
    ideas.router,
    digest.router,
    tasks.router,
    schedule.router,
    checkin.router,
    support.router,
    jobs.router,
]
