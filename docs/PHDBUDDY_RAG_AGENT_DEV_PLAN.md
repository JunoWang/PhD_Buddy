# PhD Buddy RAG And Agent Development Plan

## Goal

PhD Buddy should use a production RAG architecture for paper search, summary, and deep-dive understanding, while using LangGraph-style agent workflows for Schedule Buddy and Mental Support Buddy.

The reference implementation is:

- https://github.com/jamwithai/production-agentic-rag-course

PhD Buddy should use that project as an architecture reference, not as a direct copy. PhD Buddy remains the product and UI layer.

## Target Architecture

```text
Frontend
  Onboarding
  Dashboard
  Research Buddy
  Reading Buddy
  Schedule Buddy
  Mental Support Buddy
  Profile

Backend
  Profile / Auth
  Paper ingestion
  Paper search
  Paper summaries
  Deep-dive chat
  Agent workflows

Infrastructure
  PostgreSQL: papers, chunks, tasks, profile, check-ins
  OpenSearch: BM25 + hybrid search
  Object/vault storage: PDFs, markdown, summarize.md
  Background jobs: ingestion, parsing, summarization
  LangGraph: agent workflows
  LLM provider: OpenAI or local Ollama
```

## Phase 1: RAG Foundation For Papers

Goal: real paper search and paper storage.

Build:

- Paper metadata model
- Paper asset model
- arXiv search/import endpoint
- PDF download/storage
- Markdown extraction pipeline
- Local vault path convention

Endpoints:

```text
POST /api/papers/search
POST /api/papers/import
GET  /api/papers/{paper_id}
GET  /api/papers/{paper_id}/assets
```

Start simpler than the reference course: use arXiv API plus local JSON, SQLite, or PostgreSQL first. Add OpenSearch after the ingestion flow is stable.

## Phase 2: Search

Goal: Research Buddy can search papers by field and subfield.

Implement:

- BM25 keyword search first
- Filters: year, venue, author, field, subfield
- Ranking based on onboarding profile
- Search history

Then add:

- Section-aware chunking
- Embeddings
- Hybrid search
- Reranking

This maps to the reference course's Week 3 and Week 4 concepts.

## Phase 3: Summary Pipeline

Goal: every imported paper gets a real `summarize.md`.

Pipeline:

```text
PDF -> parsed markdown -> chunks -> summary -> summarize.md
```

Summary structure:

```md
# Paper Title

## Why This Paper Matters
## Core Problem
## Method
## Key Claims
## Evidence
## Limitations
## How It Connects To My Research
## Questions To Ask Advisor
```

Endpoints:

```text
POST /api/papers/{paper_id}/summarize
GET  /api/papers/{paper_id}/summary
```

## Phase 4: Deep-Dive Understanding Chat

Goal: Reading Buddy becomes conversational.

Implement RAG chat over selected paper chunks:

```text
User question
-> retrieve relevant chunks
-> answer with citations
-> show source sections
-> suggest next question
```

Endpoints:

```text
POST /api/reading/chat
POST /api/reading/deep-dive/start
POST /api/reading/deep-dive/message
```

Deep-dive modes:

- Explain like I am new
- Method walkthrough
- Experiment critique
- Advisor meeting prep
- Compare with another paper

This maps to the reference course's Week 5 RAG pipeline and streaming response design.

## Phase 5: Agentic Research Buddy

Goal: Research Buddy decides what to do next.

Use LangGraph for the agent workflow.

Research graph:

```text
classify_intent
  -> paper_search
  -> grade_results
  -> rewrite_query if weak
  -> retrieve_chunks
  -> answer_or_summarize
  -> suggest_next_action
```

Nodes:

- `detect_research_intent`
- `search_papers`
- `grade_relevance`
- `rewrite_query`
- `retrieve_context`
- `generate_answer`
- `create_reading_plan`

This maps closely to the reference course's Week 7 agentic RAG workflow.

## Phase 6: Schedule Buddy With LangGraph

Goal: turn PhD goals into a weekly plan.

Schedule graph:

```text
collect_context
  -> classify_goal
  -> break_down_task
  -> estimate_effort
  -> check_calendar_constraints
  -> build_week_plan
  -> ask_user_to_confirm
  -> save_schedule
```

Inputs:

- Onboarding profile
- Degree stage
- Milestones
- Current goals
- Weekly availability
- Pain points
- Active papers/tasks

Outputs:

- Weekly research plan
- Task list
- Reading blocks
- Writing blocks
- Advisor prep blocks

## Phase 7: Mental Support Buddy With Guardrails

Goal: supportive, non-clinical companion.

This buddy must not pretend to be therapy.

Mental support graph:

```text
check_in
  -> classify_state
  -> detect_risk
  -> if risk: crisis-safe response / recommend human help
  -> if low-risk: supportive reflection
  -> suggest small action
  -> optionally adjust schedule
```

Features:

- Mood check-in
- Stress source
- Tiny next action
- Schedule adjustment
- Journaling prompt
- "I am stuck" workflow

Guardrails:

- No diagnosis
- No medical claims
- Crisis escalation path
- Encourage professional support when needed

## Recommended Next Sequence

1. Add real paper model and storage:
   - `Paper`
   - `PaperAsset`
   - `PaperChunk`
   - `PaperSummary`

2. Add arXiv paper search:
   - Search by onboarding `major_field` and `subdomains`
   - Return real papers instead of hardcoded starter papers

3. Add paper import:
   - Save metadata
   - Store PDF URL
   - Create paper record

4. Add summary generation stub:
   - Initially deterministic/template-based
   - Later replace with LLM RAG summary

5. Replace current fundamental paper cards:
   - From hardcoded recommendations
   - To real arXiv/search results

After that, move into OpenSearch and hybrid RAG.

## Immediate Sprint

Build:

```text
/api/papers/search
/api/papers/import
/api/papers/recommended-from-profile
```

Update the UI so after onboarding:

- Research Buddy shows real paper search results
- User can import/save papers
- Reading Buddy shows saved papers
- Each saved paper has a placeholder `summarize.md`

This gives PhD Buddy the RAG foundation before adding LangGraph and full RAG complexity.
