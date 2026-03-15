# 0001 — Climbers Journal Core: Unified Training Journal

## Context

The MVP (PROJ-1) proved the copilot concept — an LLM that queries intervals.icu data conversationally. Now the product needs to become the **actual journal**: the single place where a climber logs, views, and queries all their training — both climbing and endurance.

### Problem

Climbers currently juggle 3–5 apps:

| Domain | Apps used | Pain |
|--------|-----------|------|
| Endurance (run, bike, hike) | Garmin Connect → intervals.icu | Garmin UI is limited; intervals.icu adds analysis but is another app |
| Climbing ticks | Mountain Project, The Crag, Vertical Life | No free APIs; data is siloed; grade systems differ |
| Social sharing | Strava | Nice-to-have, not core |
| Training plans | intervals.icu | Good, keep integrating |

No single app combines climbing ticks with endurance training in a useful way.

### Solution

Build the **Climbers Journal** as the unified interface:

1. **Endurance data** flows in automatically via intervals.icu (already working) and gets persisted locally
2. **Climbing data** entered via **copilot** (primary) or forms (fallback), with a proper domain model (crags → areas → routes → ascents)
3. **CSV import** bootstraps existing climbing history from harmonized data
4. **Copilot** queries across both domains and is the **primary input method** — "I climbed at Frankenjura, sent Wallstreet 8a onsight, worked on Action Directe 7b+ fell twice" → structured draft card → confirm → saved

### Paywall positioning

The core journal (log + view) is free. The copilot is the premium differentiator.

### Core vision

The product serves the **whole athlete** — not just the climber, not just the runner. Every view (dashboard, calendar, log) shows both climbing and endurance data side by side. Effort metrics differ by domain: endurance = time/distance/HR, climbing = route count + difficulty. Don't force one metric system — show each domain in its native units.

---

## Data Model

### Climbing Domain

```
┌──────────────────┐
│      Crag         │  e.g. "Frankenjura", "El Chorro", "Boulderhalle Wien"
│──────────────────│
│ name              │
│ country           │
│ region            │
│ venue_type        │  enum: outdoor_crag, indoor_gym
│ default_grade_sys │  enum: french, yds, v_scale, uiaa, font (auto-suggested from country)
│ latitude?         │
│ longitude?        │
│ description?      │
└──────┬────────────┘
       │ 1:N
┌──────▼───────┐
│    Area       │  e.g. "Krottenseer Turm", "Sector Suizo", "Main Hall"
│──────────────│
│ name          │
│ description?  │
│ crag_id (FK)  │
└──────┬────────┘
       │ 1:N
┌──────▼───────┐
│    Route      │  e.g. "Action Directe", "La Dura Dura"
│──────────────│
│ name          │
│ grade         │  stored as raw string (e.g. "8a", "5.12a", "V10")
│ grade_system  │  enum: french, yds, v_scale, uiaa, font
│ style         │  enum: sport, trad, boulder, multi_pitch, alpine
│ pitches?      │  int (default 1)
│ height_m?     │  int
│ description?  │
│ area_id (FK)  │
└──────┬────────┘
       │ 1:N
┌──────▼──────────┐
│    Ascent        │  a.k.a. "tick" — one attempt/send of a route
│─────────────────│
│ date             │
│ tick_type        │  enum: onsight, flash, redpoint, pinkpoint, repeat, attempt, hang
│ tries?           │  int (how many attempts in this session)
│ rating?          │  1-5 stars (personal quality rating)
│ notes?           │
│ partner?         │  free text
│ route_id (FK)?   │  nullable — for indoor gym sessions without named routes
│ grade?           │  optional override — for gym ascents without a route record
│ crag_id (FK)     │  denormalized — allows gym ascents without route hierarchy
└──────────────────┘
```

**Indoor gym handling:** Crags with `venue_type = indoor_gym` allow ascents without a route record. For gym sessions, the ascent stores the grade directly and links to the crag. This supports "did 20 problems at the gym, hardest V6" without requiring route-level granularity.

**Grade system auto-suggestion:** When creating a crag, the `default_grade_sys` is auto-suggested from country (France → french, USA → YDS, Germany → UIAA, etc.) via a simple lookup. Routes inherit the crag's default but can override.

### Endurance Domain

```
┌────────────────────┐
│  EnduranceActivity  │  synced from intervals.icu, persisted locally
│────────────────────│
│ intervals_id        │  unique ID from intervals.icu (for dedup)
│ date                │
│ type                │  e.g. "Run", "Ride", "Hike", "TrailRun"
│ name?               │
│ duration_s           │
│ distance_m?          │
│ elevation_gain_m?    │
│ avg_hr?              │
│ max_hr?              │
│ training_load?       │  (icu_training_load from intervals.icu)
│ intensity?           │  float (icu_intensity)
│ source               │  enum: intervals_icu, manual
│ raw_data?            │  JSONB — full intervals.icu payload for copilot queries
└──────────────────────┘
```

### Deferred

- **Training Session grouping** — link climbing + approach hike by date for now, explicit session model later
- **Grade Normalization** — store raw strings with `grade_system` enum, cross-system comparison via copilot lookup table later

---

## Architecture Decisions

1. **PostgreSQL + SQLModel + Alembic** — persistence layer. SQLModel for pydantic-compatible models, Alembic for migrations.
2. **No auth in v1** — single-user, local-first. Auth comes later when/if multi-user is needed.
3. **Request-scoped context dict for DI** — tool registry `dispatch(name, args, context)` where context carries `db_session` (and `user_id` in future). Minimal refactor of existing registry, explicit, extensible.
4. **Copilot-first input** — the LLM parses natural language into a structured draft (JSON). The frontend renders this as an editable draft card. On confirm, the frontend calls the REST CRUD API to persist. The LLM never writes to the DB directly — keeps it out of the write path.
5. **Two access paths, one write path** — climbing data can be entered via copilot (draft card) or forms. Both go through the same CRUD service and REST API. No duplicate validation.
6. **intervals.icu sync with retry** — on-demand sync with exponential backoff for 429 rate limits.
7. **Prompt injection: acknowledged, not mitigated** — single-user app, all data is self-entered. Risk noted for future multi-user.

### Copilot Draft Card Flow

```
USER: "Climbed at Frankenjura, sent Wallstreet 8a onsight, worked on Action Directe 7b+ fell twice"
  │
  ▼
LLM: calls parse_climbing_session tool
  │
  ▼
TOOL: returns structured JSON draft (does NOT write to DB)
  {crag: "Frankenjura", ascents: [{route: "Wallstreet", grade: "8a", tick: "onsight"}, ...]}
  │
  ▼
FRONTEND: renders editable draft card with confirm/cancel
  │
  ▼ [user confirms, optionally edits]
  │
FRONTEND: calls REST API (POST /crags, POST /routes, POST /ascents)
  │
  ▼
DB: records persisted via normal CRUD path
```

---

## Implementation Plan

### Step 1: Database Layer
**Feature:** PROJ-2

**Goal:** Add PostgreSQL, SQLModel, and Alembic to the backend.

- [x] Add `sqlmodel`, `asyncpg`, `alembic` to `pyproject.toml`
- [x] Local PostgreSQL via `brew install postgresql@16` (Docker deferred to CI/CD — eng review #1)
- [x] Create `climbers_journal/db.py` — async engine, session factory
- [x] Configure Alembic with async support
- [x] Create initial (empty) migration to verify setup
- [x] Add `DATABASE_URL` to `.env.example`
- [x] Set up test foundation: `conftest.py` with test DB, async session fixture, DB connectivity smoke test (eng review #12)

### Step 2: Climbing Data Models + API
**Feature:** PROJ-3

**Goal:** CRUD for crags, areas, routes, ascents — with indoor gym support and grade auto-suggestion.

- [x] Create SQLModel models in `climbers_journal/models/`:
  - `Crag` — with `venue_type` enum, `default_grade_sys`, `name_normalized` (eng review #10)
  - `Area` — subdivision within a crag, `name_normalized`
  - `Route` — with `grade` as raw string + `grade_system` enum, `name_normalized`, **`area_id` nullable** (eng review #8)
  - `Ascent` — nullable `route_id` for gym sessions, `crag_id` always populated (eng review #5), denormalized `crag_name` + `route_name` (eng review #14)
- [x] Country → grade system auto-suggestion lookup (simple dict)
- [x] Create Alembic migration for climbing tables
  - Composite index on `ascent(crag_id, tick_type, date)` for grade pyramid queries
- [x] Create CRUD service in `climbers_journal/services/climbing.py`:
  - Create-or-find logic uses `name_normalized` for matching (eng review #10)
  - Dedup logic in service layer: same route + date + tick_type = duplicate (eng review #9)
- [x] Create REST endpoints in `climbers_journal/routers/climbing.py`:
  - `POST /sessions/climbing` — bulk create: crag + routes + ascents in one transaction (eng review #4)
  - `GET /crags` — list crags
  - `GET /crags/{id}/areas` — list areas within a crag
  - `GET /crags/{id}/routes` — list routes within a crag (or area)
  - `GET /ascents` — list all ascents with filters
  - `GET /ascents/{id}`, `PUT`, `DELETE` — single ascent CRUD
- [x] Pagination on all list endpoints (offset + limit, default 50)
- [x] Add validation: date not in future, outdoor ascents require route_id
- [x] Error responses: FastAPI HTTPException with `{detail, code?}` convention (eng review #11)
- [x] Tests: CRUD happy paths, validation rules, dedup, name normalization edge cases

### Step 3: Endurance Activity Sync
**Feature:** PROJ-4

**Goal:** Sync intervals.icu activities into the local DB with retry handling.

- [x] Create `EnduranceActivity` SQLModel in `climbers_journal/models/`
- [x] Create Alembic migration
- [x] Create sync service in `climbers_journal/services/sync.py`:
  - Pull activities from intervals.icu for a date range
  - Upsert by `intervals_id` (idempotent)
  - Store full payload in `raw_data` JSONB
  - Exponential backoff on HTTP 429 (retry 3x with 1s/2s/4s delays)
  - Paginate by month for date ranges > 90 days
  - **Commit per month-chunk** — partial failure returns structured report: `{synced: [...], failed: "YYYY-MM", error: "..."}` (eng review #7)
- [x] Create endpoint `POST /sync/intervals` — trigger a sync for a date range
- [x] Create endpoint `GET /activities` — list endurance activities with filters + pagination
- [x] Log sync start/end/error with activity count
- [x] Tests: upsert idempotency, 429 retry (mock httpx), partial failure reporting

### Step 4: CSV Import for Climbing History
**Feature:** PROJ-5

**Goal:** Import existing climbing ticks from a harmonized CSV.

- [x] Define expected CSV schema (columns, types, required fields)
- [x] Enforce 5MB file size limit at endpoint level
- [x] Create import service in `climbers_journal/services/import_csv.py`:
  - Stream-parse with `csv.reader` (don't load entire file into memory)
  - Validate rows, collect errors per row
  - Create-or-find crag → area → route hierarchy (uses `name_normalized` matching)
  - Area column optional in CSV (eng review #8)
  - Create ascent records via climbing service (inherits dedup logic — eng review #9)
  - Batch inserts (100 rows per commit)
  - Return import report: `{created: N, skipped: N, rows_imported: N, errors: [{row: N, reason: str}]}` — includes last successful row for resume on partial failure (eng review #16)
- [x] Create endpoint `POST /import/climbing-csv` — upload + process
- [x] Tests: happy path, invalid rows, dedup, file size limit, partial failure

### Step 5: Copilot Record Tools + Draft Card
**Feature:** PROJ-8a

**Goal:** The copilot can parse natural-language climbing sessions into structured drafts. The frontend renders draft cards for user confirmation.

- [x] Refactor tool registry: `dispatch(name, args, context)` — context carries `db_session`
- [x] New tool module `climbers_journal/tools/record.py`:
  - `parse_climbing_session` — accepts natural language description, returns structured JSON draft:
    ```json
    {
      "crag": {"name": "Frankenjura", "country": "Germany", "venue_type": "outdoor_crag"},
      "ascents": [
        {"route": "Wallstreet", "grade": "8a", "tick_type": "onsight", "tries": 1},
        {"route": "Action Directe", "grade": "8c", "tick_type": "attempt", "tries": 2}
      ]
    }
    ```
  - Tool searches existing crags/routes for matches (case-insensitive), marks as `existing` or `new`
  - Does NOT write to DB — returns draft only
- [x] Backend: surface tool result as `draft_card` field on `ChatResponse` (eng review #3)
- [x] Frontend: detect `draft_card` in response, render as editable card with:
  - Crag name (editable, shows "existing" or "new" badge)
  - List of ascents (each editable: route, grade, tick_type, tries)
  - Add/remove ascent buttons
  - Confirm / Cancel buttons
- [x] On confirm: frontend calls `POST /sessions/climbing` with the draft payload (eng review #4)
- [x] Update LLM system prompt to describe the parse_climbing_session tool

### Step 6: Frontend — Activity Log View
**Feature:** PROJ-6

**Goal:** Replace chat-only UI with a journal view as the primary screen.

- [x] Create `/log` page — chronological list of all activities (climbing + endurance)
- [x] Activity cards: show type icon, name/route, grade/distance, date
- [x] Filter bar: date range, activity type (climbing/endurance), tick type
- [x] Pagination (infinite scroll or page numbers)
- [x] Click-through to detail view
- [x] Keep `/chat` as the copilot (move from root to `/chat`)

### Step 7: Frontend — Add Climbing Session Form
**Feature:** PROJ-7

**Goal:** Form-based fallback for logging climbing sessions (for when you prefer structured input over chat).

- [ ] Create `/log/add` page with multi-step form:
  1. Select or create crag (search + autocomplete from existing, case-insensitive)
  2. Select or create area within crag
  3. Add one or more ticks: select/create route, tick_type, tries, rating, notes
- [ ] For indoor gyms: skip area/route selection, just grade + tick_type per problem
- [ ] Form supports adding multiple ticks per session (common: 5-10 routes per session)
- [ ] Auto-save draft to localStorage
- [ ] Success state shows summary of logged session

### Step 8: Copilot Query Tools
**Feature:** PROJ-8b

**Goal:** Extend the LLM tool registry to query the local DB for stats and insights.

- [ ] New tool module `climbers_journal/tools/journal.py`:
  - `search_routes` — find routes by name, grade, crag
  - `get_ascents` — query ascents with filters (date, grade, tick_type, crag)
  - `get_climbing_stats` — summary stats (sends by grade, onsight rate, volume over time)
  - `get_training_overview` — combined view: climbing volume + endurance load for a period
- [ ] Register tools in registry
- [ ] Update system prompt to describe both data sources (intervals.icu live + local journal)

### Step 9: Frontend — Dashboard
**Feature:** PROJ-9

**Goal:** A landing page that shows training at a glance.

- [ ] Create `/` page as dashboard:
  - Recent activity feed (last 7 days, both climbing + endurance)
  - **Grade pyramid** — sends only (onsight/flash/redpoint/repeat), with indoor/outdoor toggle
  - Endurance stats card: volume this week, CTL/ATL/TSB from intervals.icu
  - Climbing stats card: sends this week/month, hardest send
- [ ] Grade pyramid: horizontal bar chart by grade, filterable by:
  - Sends only (exclude attempts/hangs)
  - Indoor vs outdoor vs all
  - Time period (all time, this year, this month)
- [ ] Quick-add button → links to `/log/add`
- [ ] Copilot teaser → links to `/chat`

### Step 10: Frontend — Training Calendar
**Feature:** PROJ-10

**Goal:** A unified weekly/monthly calendar showing all training at a glance.

- [ ] Create `/calendar` page with week and month views
- [ ] Each day cell shows:
  - Climbing: route count + hardest grade (color-coded by venue_type)
  - Endurance: activity type icon + duration
- [ ] Click day → expands to show details or links to log view filtered by date
- [ ] REST endpoint: `GET /calendar?month=2026-03` — returns aggregated data per day
- [ ] Empty days are visually distinct (rest days are important too)

---

## Feature Specs to Create

| ID | Name | Plan Step |
|----|------|-----------|
| PROJ-2 | Database layer | Step 1 |
| PROJ-3 | Climbing data model + API (with indoor gym, grade auto-suggest) | Step 2 |
| PROJ-4 | Endurance activity sync (with retry) | Step 3 |
| PROJ-5 | CSV import | Step 4 |
| PROJ-6 | Activity log view | Step 6 |
| PROJ-7 | Add climbing session form | Step 7 |
| PROJ-8a | Copilot record tools + draft card | Step 5 |
| PROJ-8b | Copilot query tools | Step 8 |
| PROJ-9 | Dashboard + grade pyramid | Step 9 |
| PROJ-10 | Training calendar | Step 10 |

---

## Out of Scope (for now)

- **User auth / multi-user** — single-user local-first for now
- **Strava integration** — social sharing is low priority
- **Scraping Mountain Project / The Crag** — no free APIs, manual entry instead
- **Grade normalization / comparison** — store raw, compare in copilot logic later
- **Training plan builder** — intervals.icu handles this well already
- **Mobile app** — responsive web first
- **Training session grouping** — link by date for now, explicit session model later
- **Photo attachments** — deferred to TODOS.md (local disk storage when ready)
- **CSV export** — deferred to TODOS.md

---

## Review Decisions (from CEO review, 2026-03-15)

| # | Decision | Choice |
|---|----------|--------|
| 1 | Review mode | SCOPE EXPANSION |
| 2 | Indoor gym sessions | Extend model: `venue_type` on Crag, route-optional ascents |
| 3 | DI for tool handlers | Request-scoped context dict |
| 4 | Prompt injection risk | Acknowledge, don't mitigate (single-user) |
| 5 | LLM write confirmation | Draft card in frontend (LLM returns draft, frontend confirms via REST) |
| 6 | Grade pyramid | In scope — sends only, indoor/outdoor toggle |
| 7 | LLM-first input | Reordered: copilot logging (Step 5) before forms (Step 7) |
| 8 | Training calendar | In scope as Step 10 |
| 9 | Auto-suggest grade system | In scope (country → grade_system lookup in Step 2) |
| 10 | CSV export | Deferred to TODOS.md (P2) |
| 11 | Rate limit handling | Built into Step 3 (exponential backoff) |
| 12 | Photo storage | Deferred to TODOS.md — local disk, not S3 |

## Review Decisions (from Eng review, 2026-03-15)

| # | Issue | Decision |
|---|-------|---------|
| 1 | Dev PostgreSQL setup | Local install (`brew install postgresql@16`), Docker deferred to CI/CD |
| 2 | Tool registry refactor timing | Keep in Step 5 — Steps 2-4 are pure backend foundation |
| 3 | Draft card protocol | Structured `draft_card` field on `ChatResponse` (not markdown parsing) |
| 4 | Draft confirm atomicity | `POST /sessions/climbing` bulk endpoint, one DB transaction |
| 5 | Ascent `crag_id` denormalization | Always populated on all ascents, enforced at write time |
| 6 | Frontend state management | Native Next.js patterns (server components, fetch cache, local state). No library. |
| 7 | Sync partial failure | Commit per month-chunk, return structured report of succeeded/failed months |
| 8 | Area model | Keep but make optional — `area_id` on Route is nullable |
| 9 | Duplicate detection | Dedup logic in climbing service layer, inherited by all write paths |
| 10 | Case-insensitive matching | `name_normalized` column on Crag/Area/Route, populated at write time |
| 11 | Error response format | FastAPI HTTPException with `{detail, code?}` convention |
| 12 | Test foundation | pytest fixtures (test DB, async session) added in Step 1, tests in every step |
| 13 | Frontend testing | Deferred — use /qa skill for E2E. Add Vitest if frontend logic grows. |
| 14 | N+1 / read performance | Denormalize `crag_name` + `route_name` onto Ascent (future multi-user ready) |
| 15 | Grade pyramid index | Composite index on `ascent(crag_id, tick_type, date)` in Step 2 migration |
| 16 | CSV import partial failure | Include `rows_imported` in report for resume. Built into Step 4. |
