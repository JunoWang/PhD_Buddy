# PhD Buddy — Platform Architecture

Status: draft v2 · 2026-07-03
Sources: `PhD 陪伴系统.md`, `phd_buddy_decision_tree.svg`, `research_buddy_idea_pipeline.svg`, `Research Idea Sell Platform.md`

## 1. What we are building

One PhD companion platform, one shared user profile, **three buddy modules**:

```text
                    ┌─────────────────────────┐
                    │      Student Profile     │
                    │ field · subdomains ·     │
                    │ venues · goals · advisor │
                    └───────────┬─────────────┘
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Research Buddy  │  │  Schedule Buddy  │  │   Mental Buddy   │
│ paper discovery  │  │ task intake      │  │ daily check-in   │
│ summary/deep-dive│  │ decompose        │  │ stress detect    │
│ idea brainstorm  │  │ weekly schedule  │  │ support actions  │
│ persona panel    │  │ overwhelm loop   │  │ sleep/meal pings │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         └─────────────────────┼─────────────────────┘
                               ▼
                 shared platform: API · LLM layer ·
                 jobs/scheduler · vault · notifications
```

The buddies are peers in the architecture. They ship in order (Research → Schedule → Mental) but every shared component below is designed so that adding the next buddy is adding a router + service + models, not re-architecting.

### Constraints from discovery (these drive every technical choice)

| Question | Answer | Consequence |
|---|---|---|
| Who | Single PhD student, self-serve | No enterprise auth/compliance; mild privacy for health data |
| Volume | 5–20 interactions/day across all buddies | Conversational UI + scheduled triggers, not batch tooling |
| Error rate | Papers ~5% OK · **mental health <0.1%** | Papers: student validates. Mental: HITL guardrail, no autonomous advice |
| Cost ceiling | ~$20–50/month | Haiku for cheap passes, Sonnet for deep work; Semantic Scholar (free); cache every LLM artifact |
| Latency | Chat <3s perceived · digests/pings async | Streaming responses for all chat; cron jobs for digests, check-ins, reminders |

## 2. Client strategy: web now, mobile later, one API

The rule that makes mobile cheap later: **the backend never renders product state into HTML; every feature is an API endpoint first.** The web app is just the first client.

```text
┌───────────────────────────┐   ┌────────────────────────────┐
│  Web app (now)            │   │  Mobile app (later)         │
│  SPA + PWA manifest       │   │  React Native / Expo        │
│  responsive layout        │   │  reuses API client + types  │
└─────────────┬─────────────┘   └──────────────┬─────────────┘
              │        HTTPS / JSON / SSE      │
              ▼                                ▼
┌──────────────────────────────────────────────────────────────┐
│                    FastAPI  (single backend)                  │
│                                                              │
│  routers/    profile · library · reading · ideas · digest    │
│              tasks · schedule · checkin · support · jobs     │
│  services/   one module per buddy + shared discovery/verify  │
│  llm/        model router · prompt harnesses · cache          │
│  jobs/       scheduler (digests, check-ins, reminders)        │
│  storage/    vault adapter (files now → DB+S3 later)          │
│  notify/     notification abstraction (web now, push later)   │
└───────┬──────────────────┬──────────────────┬────────────────┘
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐  ┌────────────────┐  ┌─────────────────────┐
│ SQLite (now)  │  │ Vault (files)  │  │ External services   │
│ → Postgres    │  │ pdf + md + json│  │ Semantic Scholar     │
│   + pgvector  │  │ Obsidian-ready │  │ OpenAlex/Crossref    │
└───────────────┘  └────────────────┘  │ Anthropic API        │
                                       │ (later: wearable API)│
                                       └─────────────────────┘
```

### Web-first decisions

- **Frontend**: keep the current static `index.html` only while onboarding is the sole screen. When the library/reading screens land (Phase 1), move to a **React + TypeScript + Vite SPA** with a PWA manifest. PWA gives an installable, phone-usable app for free — that is the "mobile app" until usage justifies a native build. This matters doubly here: check-ins and reminders (Mental/Schedule buddy) are phone-shaped interactions, and a PWA with notifications covers them long before a native app exists.
- **Why not Next.js**: no SEO, no public pages, single user. A plain SPA against FastAPI is one less server, and keeps all rendering client-side — which is exactly what React Native will need too.
- **Mobile later**: Expo/React Native app that imports the same generated API client. Only screens are rewritten; all buddy logic lives behind the API.

### Mobile-readiness rules (enforced from day one)

1. Every feature ships as a JSON endpoint before it ships as a screen.
2. Auth is token-based from the start (even a static local token), never cookie-session-only.
3. Long operations return a `job_id` immediately; clients poll `GET /api/jobs/{id}` or subscribe to SSE. No endpoint blocks longer than ~3s.
4. All chat (deep-dive, mental check-in conversation, task intake) streams over SSE; the same event stream can feed a native client later.
5. Notifications go through `notify/` (in-app inbox + web push now, native push later) — no buddy talks to a notification channel directly.
6. Generated OpenAPI schema is the contract — the TS client for web and later mobile is generated from it, never handwritten.

## 3. The three buddy modules

### 3.1 Research Buddy

**Flows** (from the literature pipeline + idea pipeline diagrams):

```text
Onboarding profile (field → sub-area → topic + venues + scholar URL)
   ├── Foundational lineage: seed papers → walk citation graph → landmarks
   └── Recent search: expand keywords → Semantic Scholar → re-rank
          ↓
   Verify against real citations (title/authors/year; flag unverified)
          ↓
   Acquire + convert + store (OA pdf → structure-aware markdown → vault)
          ↓
   ├── Summary track: cheap one-pass (Haiku), cached
   └── Deep-dive track: 8-lens opening, constrained conversation,
       three-bucket grounding (grounded / inferred / external),
       student positioned as the verifier                (Sonnet)
          ↓
   Dual-format cache → vault (canonical JSON + student-facing md)
          ↓
   Feeds idea brainstorm panel:
   brainstorm → idea structuring (problem · mechanism · novelty)
   → SOTA/baseline mapping → gap analysis
   → multi-persona review panel:
        venue reviewer · senior researcher · advisor persona · industry voice
   → assessment report (strengths · gaps · pivots · risk)
   → route by goal: finish-PhD plan | research-line agenda | industry map
```

**API surface**: `routers/library.py` (search, add, verify, assets), `routers/reading.py` (summaries, deep-dive sessions over SSE), `routers/ideas.py` (brainstorm, structuring, panel, routing), `routers/digest.py` (scheduled recent-search digests).

**Guardrail**: nothing unverified feeds the idea panel silently; `verification_status` is always surfaced.

### 3.2 Schedule Buddy

**Flows** (from the decision tree):

```text
Task intake (class · advisor · personal)  — conversational or form
   ↓
Decompose task: divide & conquer into steps with estimates
   ↓
Weekly schedule: priority + time blocks (respects deadlines, energy patterns)
   ↓
User overwhelmed?
   ├── No → done; scheduled reminders fire through notify/
   └── Yes → re-plan loop: shrink scope, push deadlines, drop/renegotiate
             (this is also a signal INTO Mental Buddy — see §3.4)
```

**API surface**: `routers/tasks.py` (CRUD, `POST /tasks/{id}/decompose`), `routers/schedule.py` (`GET /schedule/week`, `POST /schedule/replan`, block CRUD).

**LLM usage**: decomposition and weekly planning are Sonnet calls with the profile + task list as context; reminders are pure scheduler, zero LLM cost.

**Guardrail**: the buddy proposes schedules, the student confirms them — a plan is `draft` until accepted, so a bad decomposition costs nothing.

### 3.3 Mental Buddy

**Flows** (from the decision tree):

```text
Daily check-in: mood ping (scheduled, phone-shaped, 10 seconds to answer)
   ↓
Stress detect: self-report first; wearable integration later
   ↓
Stress level?
   ├── Low  → light acknowledgement; log the trend
   └── High → Support action: meditate / walk / chat
              (chat = supportive conversation harness, NOT therapy)
Plus: sleep + meal reminders (pure scheduler)
```

**API surface**: `routers/checkin.py` (ping responses, mood/stress history), `routers/support.py` (support actions, supportive chat over SSE).

**The <0.1% error budget is met by design, not by model quality:**

1. **Canned-first**: support actions are a fixed, human-authored menu (meditate / walk / journal / call someone). The LLM may *select and phrase*, never invent interventions.
2. **HITL gate**: any generated output that goes beyond the canned menu requires explicit student acknowledgement (`SupportAction.human_ack`) before it is treated as accepted; nothing escalates autonomously.
3. **Crisis routing is hardcoded**: keyword/classifier trip-wire → static, pre-written resource card (hotlines, campus counseling). No LLM in that path, ever.
4. **Supportive chat harness** is scoped like the deep-dive harness: versioned system prompt in git, explicitly bounded ("companion, not clinician"), refusal-to-diagnose built in.
5. **Privacy**: health data (check-ins, stress, sleep) is tagged `sensitive`, stays in the local vault/DB, is excluded from any future server sync by default, and never enters Research/Schedule prompts — only the coarse cross-buddy signals in §3.4 cross the boundary.

### 3.4 Cross-buddy signals (why one platform instead of three apps)

The shared profile + event bus is the payoff:

| Signal | From → To | Effect |
|---|---|---|
| Repeated "overwhelmed" re-plans | Schedule → Mental | check-in tone shifts; suggests a lighter week |
| High-stress streak | Mental → Schedule | weekly planner lowers load, protects sleep blocks |
| High-stress streak | Mental → Research | digest pauses "you're behind on reading" framing |
| Deadline crunch (paper submission) | Research → Schedule | auto-proposes writing blocks |
| Advisor-meeting notes | Research ↔ Schedule | advisor persona + task intake share the same source |

Implementation: a small internal `events` table (`emitter, kind, payload, created_at`); each buddy's service subscribes to the kinds it cares about. Only coarse signals cross the mental-health boundary (e.g. `stress_trend: high`), never check-in content.

## 4. Backend structure

Evolves the existing `src/phd_buddy/` package; nothing is thrown away.

```text
src/phd_buddy/
├── app.py                  # FastAPI factory, router registration (from web.py)
├── cli.py                  # existing CLI entry points
├── routers/
│   ├── profile.py          # onboarding CRUD (existing endpoints move here)
│   ├── library.py          # research: papers, verify, assets
│   ├── reading.py          # research: summaries + deep-dive chat (SSE)
│   ├── ideas.py            # research: brainstorm → persona panel → routing
│   ├── digest.py           # research: scheduled digests
│   ├── tasks.py            # schedule: intake + decomposition
│   ├── schedule.py         # schedule: weekly plan + replan
│   ├── checkin.py          # mental: mood pings + history
│   ├── support.py          # mental: support actions + supportive chat (SSE)
│   └── jobs.py             # generic async-job status
├── services/
│   ├── profile.py          # from onboarding.py
│   ├── discovery.py        # lineage + recent search + re-rank
│   ├── verification.py     # citation check
│   ├── acquisition.py      # OA pdf → structure-aware markdown
│   ├── reading.py          # summary/deep-dive orchestration
│   ├── ideas.py            # structuring, gap analysis, persona panel
│   ├── scheduling.py       # decomposition, weekly planner, replan loop
│   ├── wellbeing.py        # check-ins, stress trends, support actions
│   └── events.py           # cross-buddy signal bus (§3.4)
├── llm/
│   ├── router.py           # task → model map (§6)
│   ├── harnesses/          # versioned system prompts
│   │   ├── deep_dive.md    # three-bucket grounding + 8 lenses (written)
│   │   ├── summary.md
│   │   ├── idea_panel/     # venue_reviewer.md · senior_researcher.md ·
│   │   │                   # advisor_persona.md · industry_voice.md
│   │   ├── task_decompose.md
│   │   ├── weekly_plan.md
│   │   └── supportive_chat.md   # bounded companion harness (§3.3)
│   └── cache.py            # content-hash keyed LLM-output cache
├── jobs/
│   ├── runner.py           # APScheduler in-process; queue only if ever needed
│   └── tasks.py            # digest_cron, acquire_paper, checkin_ping,
│                           # sleep_meal_reminders, run_idea_panel
├── notify/
│   └── channels.py         # in-app inbox + web push now; native push later
├── storage/
│   ├── db.py               # SQLModel, SQLite now → Postgres later
│   ├── vault.py            # dual-format cache writer (JSON canonical + md)
│   └── models.py           # entities (§5)
└── static/                 # replaced by apps/web build output in Phase 1
```

Repo layout once the SPA lands (light monorepo, no workspace tooling needed):

```text
PhD_Buddy/
├── src/phd_buddy/          # FastAPI backend (uv-managed, as today)
├── apps/web/               # React+TS+Vite SPA, PWA manifest
│   └── src/api/            # client generated from /openapi.json
├── vault/                  # user-owned artifacts (Obsidian-compatible)
├── docs/
└── tests/
```

## 5. Data model

Canonical state in the DB; the **vault stays the human-readable projection** (dual-format cache: one canonical JSON + student-facing markdown), written by `storage/vault.py` on every mutation. This preserves the local-first/Obsidian property while giving mobile a real API to sync from later.

```text
# shared
Profile            major_field, subdomains[], venues[], scholar_url,
                   seed_papers[], keywords[], goal: finish_phd|research_line|industry
Event              emitter, kind, payload, created_at        (cross-buddy bus)
Job                kind, status: queued|running|done|failed, payload, result_uri
Notification       channel, title, body, read_at, source_buddy

# research buddy
Paper              external_ids (S2/DOI/arXiv), title, authors, year, venue,
                   verification_status: unverified|verified|flagged,
                   source: lineage|recent_search|manual|digest
PaperAsset         paper_id, kind: pdf|markdown|metadata, path/uri
Summary            paper_id, model, content_md, cost, created_at    (cached)
DeepDiveSession    paper_id, harness_version, started_at
DeepDiveMessage    session_id, role, content, buckets_used[]
Idea               raw_text, problem_statement, mechanism, claimed_novelty,
                   status: draft|structured|reviewed|routed
IdeaReview         idea_id, persona: venue|senior|advisor|industry,
                   strengths[], gaps[], suggested_pivots[], risk_level
IdeaRoute          idea_id, goal, plan_md
AdvisorPersona     sources: lab_papers|meeting_notes|feedback_patterns|priorities,
                   distilled_md, version        (used by idea panel + task intake)

# schedule buddy
Task               title, origin: class|advisor|personal, deadline, estimate,
                   status: inbox|decomposed|scheduled|done|dropped
TaskStep           task_id, description, estimate, order, done
WeeklyPlan         week_of, status: draft|accepted|replanned, generated_by
ScheduleBlock      plan_id, task_step_id?, start, end, kind: work|class|rest|protected

# mental buddy  (all rows tagged sensitive; local-only by default)
CheckIn            date, mood, stress_level, note, source: self_report|wearable
SupportAction      checkin_id?, kind: meditate|walk|journal|reach_out|chat,
                   generated_text?, human_ack: bool, outcome
ReminderRule       kind: sleep|meal, schedule, enabled
```

## 6. LLM layer

Central `llm/router.py` maps task → model so cost stays inside $20–50/mo:

| Task | Buddy | Model | Mode |
|---|---|---|---|
| One-pass paper summary | Research | Haiku | async job, cached forever |
| Deep-dive chat | Research | Sonnet | SSE stream, <3s to first token |
| Recent-search re-rank | Research | Haiku | async |
| Idea structuring | Research | Sonnet | sync |
| Persona review panel | Research | Sonnet | async job, 4-persona fan-out |
| Weekly digest | Research | Haiku | cron |
| Task decomposition | Schedule | Sonnet | sync |
| Weekly plan / replan | Schedule | Sonnet | sync, draft until accepted |
| Check-in acknowledgement | Mental | Haiku | sync, canned-first |
| Supportive chat | Mental | Sonnet | SSE stream, bounded harness |
| Sleep/meal reminders | Mental | none | pure scheduler, $0 |

Non-negotiables carried over from the design notes:

- **Three-bucket grounding** (grounded / inferred / external) is the deep-dive contract; the harness in `PhD 陪伴系统.md` becomes `llm/harnesses/deep_dive.md`, versioned in git.
- **Student is the verifier** for papers; **human-in-the-loop** for mental-health outputs; **draft-until-accepted** for schedules. Each buddy's error budget is enforced structurally, not by trusting the model.
- **Cache everything**: every LLM artifact keyed by content hash + harness version; a re-read costs $0.
- **PDF → markdown first**, then feed to the model (never raw PDF into prompts).

## 7. Scheduler & notifications

APScheduler inside the FastAPI process is enough at this scale (single user, 5–20 interactions/day):

| Job | Buddy | Cadence |
|---|---|---|
| `digest_cron` | Research | weekly (configurable) |
| `acquire_paper`, `summarize_paper`, `run_idea_panel` | Research | on demand |
| `reminder_fire` | Schedule | per accepted plan blocks |
| `checkin_ping` | Mental | daily, user-chosen time |
| `sleep_meal_reminders` | Mental | per ReminderRule |

All user-facing pings flow through `notify/channels.py`: in-app inbox + web push (PWA) now; the same interface backs native push when the mobile app exists.

## 8. Phased roadmap

Order comes from dependency + risk, not importance — Mental Buddy ships last because its guardrails deserve the most care, not because it matters least.

- **Phase 0 — done**: onboarding profile → dual-format vault cache; CLI + web form.
- **Phase 1 — Research Buddy core (web)**: Paper model + Semantic Scholar lineage/recent search → verification + library screen → acquisition + summary track → deep-dive chat (SSE, three-bucket harness). Replace static frontend with the React SPA + PWA manifest here. The `notify/`, `jobs/`, `events` scaffolding lands in this phase because the digest cron needs it — which means Schedule/Mental arrive onto ready rails.
- **Phase 2 — Idea pipeline**: brainstorm → structuring → gap analysis → persona panel (incl. first advisor-persona build) → assessment report → route by goal.
- **Phase 3 — Schedule Buddy**: task intake → decomposition → weekly schedule (draft/accept) → reminders → overwhelm replan loop → cross-buddy events wired.
- **Phase 4 — Mental Buddy**: daily check-in ping → stress trends → canned support actions → bounded supportive chat with HITL gate → crisis resource card (hardcoded) → sleep/meal reminders. Wearable integration deferred.
- **Phase 5 — Mobile + multi-device**: Expo app on the same API; SQLite→Postgres and vault→(DB + object storage with local vault export) only when a second device needs sync. Sensitive mental-buddy data stays local-only unless explicitly opted in.

**Adjacent project**: the Research Idea Sell Platform (claim–evidence engine, sellability canvas, sandboxed reproducibility) stays out of scope — but Phase 2's idea assessment report is designed to be its input, so the `Idea` schema keeps `problem_statement / mechanism / claimed_novelty` aligned with its `Claim` taxonomy.
