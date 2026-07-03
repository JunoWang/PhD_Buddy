"""Entity definitions for all three buddies (ARCHITECTURE.md §5).

Planned tables:

- shared: Profile, Event, Job, Notification
- research: Paper, PaperAsset, Summary, DeepDiveSession, DeepDiveMessage,
  Idea, IdeaReview, IdeaRoute, AdvisorPersona
- schedule: Task, TaskStep, WeeklyPlan, ScheduleBlock
- mental (sensitive, local-only by default): CheckIn, SupportAction, ReminderRule

Implemented incrementally starting in Phase 1 (Paper + PaperAsset first).
"""

from __future__ import annotations
