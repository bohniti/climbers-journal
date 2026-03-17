# 0003: Activities Overhaul — Strava Types, Session Grouping & Crag Browser

> Align activity types with Strava's taxonomy, group climbing ascents into explicit sessions, add a unified activity feed, and introduce a crag/topo browser.

## Context

Three problems with the current activity system:

1. **Activity types & icons are ad-hoc** — only 7 endurance types have icons (Run, Ride, Hike, TrailRun, Swim, Walk, VirtualRide). Strava supports ~50 sport types. Climbing is treated as a single category instead of having fine-grained sub-types (sport, boulder, multi-pitch, trad, alpine) like Strava does.

2. **No explicit climbing session** — ascents are flat records. When you climb 5 routes at Kletterhalle Wien, the log shows 5 separate cards instead of one session containing 5 routes. The data model has no `ClimbingSession` entity — sessions are implicit (same date + crag).

3. **No crag/topo browser** — there's no way to view all sessions at a location, browse areas within a crag, or see what routes exist at a venue.

**Additional issue from review:** The frontend splits activities into "climbing" vs "endurance" buckets — but this distinction is confusing. All activities should feel like peers in a unified feed. A RockClimbing activity from a Garmin watch (synced via intervals.icu) should auto-link to the manual climbing session, merging HR/duration data.

## Approach

```
┌────────────────────────────────────────────────────────────────┐
│                     Unified Activity Feed                      │
│                                                                │
│  ┌─ Session Card ──────────────────────────────────────────┐  │
│  │ 🧗 Kletterhalle Wien · Mar 12 · 2h 45m                 │  │
│  │ 5 routes · hardest 7a · 3× sport  2× boulder           │  │
│  │ ┌─ Summary (expand level 1) ──────────────────────┐    │  │
│  │ │ 5 routes · hardest 7a · 3 sends · 2 attempts    │    │  │
│  │ │ [Show all 5 routes]                              │    │  │
│  │ │ ┌─ Routes (expand level 2) ───────────────────┐ │    │  │
│  │ │ │ Moonlight 7a  ⚡ Flash                       │ │    │  │
│  │ │ │ Crux Move 6c+ 🔴 Redpoint                   │ │    │  │
│  │ │ │ ...                                          │ │    │  │
│  │ │ └─────────────────────────────────────────────┘ │    │  │
│  │ └────────────────────────────────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌─ Endurance Card ────────────────────────────────────────┐  │
│  │ 🏃 Morning Run · Mar 11 · 45m · 8.2 km                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌─ Endurance Card ────────────────────────────────────────┐  │
│  │ 🚴 Gravel Ride · Mar 10 · 2h 10m · 48.3 km             │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

- Adopt Strava's `SportType` enum as the canonical activity taxonomy. Map intervals.icu types on sync.
- For climbing, keep `RouteStyle` enum (sport, trad, boulder, multi_pitch, alpine) as first-class display categories.
- Introduce `ClimbingSession` table with `UNIQUE(date, crag_id)` grouping ascents by date+crag. Migrate existing ascents.
- Auto-link `RockClimbing` endurance activities to climbing sessions by date, merging duration/HR data.
- Build a unified activity feed via `GET /feed` backend endpoint (SQL UNION, single cursor pagination).
- Add crag browser pages (list + detail) with stats and session history.
- Implement name propagation on crag/route rename (resolves TODOS.md item).
- Add `get_sessions()` copilot tool for session-grouped queries.

## Steps

### Step 1: Strava-aligned activity taxonomy & icons

- [x] Create `SPORT_TYPES` constant mapping every Strava SportType to `{ icon, label, category }`. Categories: `run`, `ride`, `swim`, `winter`, `climbing`, `water`, `fitness`, `other`
- [x] Full Strava SportType list: AlpineSki, BackcountrySki, Badminton, Canoeing, Crossfit, EBikeRide, Elliptical, EMountainBikeRide, Golf, GravelRide, Handcycle, HighIntensityIntervalTraining, Hike, IceSkate, InlineSkate, Kayaking, Kitesurf, MountainBikeRide, NordicSki, Pickleball, Pilates, Racquetball, Ride, RockClimbing, RollerSki, Rowing, Run, Sail, Skateboard, Snowboard, Snowshoe, Soccer, Squash, StairStepper, StandUpPaddling, Surfing, Swim, TableTennis, Tennis, TrailRun, Velomobile, VirtualRide, VirtualRow, VirtualRun, Walk, WeightTraining, Wheelchair, Windsurf, Workout, Yoga
- [x] Add climbing sub-type icons: 🧗 sport, 🪨 boulder, ⛰️ multi-pitch, 🏔️ trad/alpine
- [x] Replace `ACTIVITY_ICONS` and `mapEnduranceType()` with the new taxonomy
- [x] Fallback for unknown types: map to `Workout` category with 💪 icon, log `console.warn`
- [x] Update `ACTIVITY_TYPE_COLORS` to cover the new categories
- [x] Update `WeeklyActivity` chart legend and stacked bars to use new categories
- [x] Update `EnduranceCard` in log page to use new icons
- [x] Update `DayAccordion` in weekly activity to use new icons
- [x] Update calendar page day cells to use new icons

**Files:** `app/frontend/src/lib/constants.ts`, `app/frontend/src/components/WeeklyActivity.tsx`, `app/frontend/src/app/log/page.tsx`, `app/frontend/src/app/calendar/page.tsx`, `app/frontend/src/app/page.tsx`

### Step 2: ClimbingSession model & API

- [x] Add `ClimbingSession` SQLModel:
  - `id`, `date`, `crag_id` (FK), `crag_name` (denorm), `notes` (session-level notes)
  - `linked_activity_id` (nullable FK to `endurance_activity.id` — for auto-linked watch data)
  - `created_at`
  - `UNIQUE(date, crag_id)` — one session per crag per day, idempotent creates
  - Keep `partner` on Ascent (per-route partner is valid — belayer changes between routes)
  - Keep `notes` on Ascent too (route-specific beta vs session-level notes)
- [x] Add `session_id` FK to `Ascent` model (nullable for migration)
- [x] Alembic migration: create `climbing_session` table, add `session_id` column to `ascent`
  - Add indexes: `ix_session_date`, `ix_session_crag_id`, `ix_ascent_session_id`
- [x] Data migration: group existing ascents by (date, crag_id) → create sessions, backfill `session_id`
  - Handle: ascents with NULL crag_id → skip, log warning
  - Handle: ascents from different API calls but same (date, crag) → merge into one session
- [x] Update `create_climbing_session` service to create a `ClimbingSession` record and link ascents
  - If session already exists for (date, crag_id): return existing and append ascents (idempotent)
- [x] Add `GET /sessions/climbing` endpoint — returns sessions with nested ascents
  - Pagination by session count (not ascent count): `?offset=0&limit=20`
  - Eager-load ascents: `selectinload(ClimbingSession.ascents)`
  - Filters: `date_from`, `date_to`, `crag_id`
- [x] Add `GET /sessions/climbing/{session_id}` endpoint — single session detail
- [x] Update `ClimbingSessionResponse` to include session ID, nested ascent list, and linked activity data (duration, HR)
- [x] Keep `GET /ascents` working for backward compatibility (copilot tools use it)
- [x] Auto-link `RockClimbing` endurance activities:
  - On session create: check if a RockClimbing endurance activity exists for the same date → link it
  - On endurance sync: check if type=RockClimbing and a session exists for that date → link it
  - Ambiguous match (multiple sessions same date): pick session with most ascents, log warning
- [x] Add `GET /feed` endpoint in `stats.py`:
  - SQL `UNION ALL` of sessions + endurance activities, ordered by date desc
  - Single cursor pagination: `?offset=0&limit=20&type=all|climbing|endurance`
  - Returns `ActivityItem[]` (discriminated union with `kind` field)
- [x] Add `GET /stats/health` endpoint: total sessions, ascents, endurance activities, orphaned ascents (session_id=NULL), unknown sport types — for migration verification
- [x] Name propagation helper: `propagate_crag_name(session, crag_id, new_name)` updates `crag_name` on all related Ascent AND ClimbingSession records (resolves TODOS.md P2 item). DRY: single function for both tables.
- [x] Add `get_sessions()` copilot tool in `tools/journal.py`: query sessions with nested ascents by date range, crag name, etc. Complements existing `get_ascents()`.

**Files:** `app/backend/climbers_journal/models/climbing.py`, `app/backend/climbers_journal/routers/climbing.py`, `app/backend/climbers_journal/services/climbing.py`, `app/backend/alembic/versions/` (new migration), `app/backend/climbers_journal/routers/stats.py`, `app/backend/climbers_journal/tools/journal.py`

### Step 3: Unified activity feed

The activity log becomes a single chronological feed where climbing sessions and endurance activities are peers — no more "climbing" vs "endurance" bucket split.

- [x] Define unified `ActivityItem` type:
  ```
  type ActivityItem =
    | { kind: "session"; date: string; data: ClimbingSessionResponse }
    | { kind: "endurance"; date: string; data: ActivityResponse }
  ```
- [x] Replace flat `ClimbingCard` with `ClimbingSessionCard`:
  - **Collapsed state:** session icon + crag name + date + duration (from linked watch) + route count + tick type pills
  - **Expand level 1 (summary):** stats line "5 routes · hardest 7a · 3 sends · 2 attempts" + "Show all N routes" button
  - **Expand level 2 (routes):** full route list with grade, tick type, tries
  - For sessions with >10 routes, level 1 is the default expand (avoids overwhelming)
- [x] Update `LogPage` to fetch from single `GET /feed` endpoint (no more dual-cursor merge)
- [x] Pagination: single offset/limit cursor via the `/feed` endpoint
- [x] Endurance cards use new sport type icons from Step 1
- [x] Update filter bar:
  - "All activities" / "Climbing" / "Endurance"
  - Removed tick_type filter from top level (tick types shown as pills on session cards)
- [x] Show linked watch duration on session cards when available ("2h 45m at Kletterhalle Wien")
- [x] Update dashboard recent activity section to reuse unified feed component (replace flat `recent_climbing` / `recent_endurance` with `/feed?limit=10`)

**Files:** `app/frontend/src/app/log/page.tsx`, `app/frontend/src/lib/api.ts`, `app/frontend/src/lib/constants.ts`, `app/frontend/src/app/page.tsx`

### Step 4: Crag browser & topo pages

- [x] Add `/crags` page — searchable list of all crags:
  - Venue type badge (gym/outdoor)
  - Country/region
  - **"Last visited: 3 weeks ago"** relative date badge
  - Session count
  - Sort: last visited (default), name, session count
- [x] Add `/crags/[id]` detail page with:
  - **Crag quick-stats header:** "12 sessions · 47 routes logged · best send: 7b+ · last visited: Mar 2"
  - Session history (reverse chronological, reusing `ClimbingSessionCard`)
- [x] Add `GET /crags/{crag_id}/sessions` backend endpoint — sessions at a crag with nested ascents
  - Eager-load: `selectinload(ClimbingSession.ascents)`
- [x] Add `GET /crags/{crag_id}/stats` backend endpoint — session count, route count, hardest send, last visited date
- [x] Add nav link to crag browser
- [x] Paginate sessions on crag detail (20 per page with load more)

**Files:** `app/frontend/src/app/crags/page.tsx` (new), `app/frontend/src/app/crags/[id]/page.tsx` (new), `app/frontend/src/lib/api.ts`, `app/frontend/src/components/Nav.tsx`, `app/backend/climbers_journal/routers/climbing.py`, `app/backend/climbers_journal/services/climbing.py`

## Edge Cases & Risks

- **Unknown intervals.icu types** — fallback to `Workout` category with 💪 icon. Backend logs `logger.warning(f"Unknown sport type: {type}")`.
- **Migration safety** — data migration groups ascents by (date, crag_id), handles NULLs, runs in transaction. Verify with `GET /stats/health` post-migration.
- **Nullable session_id** — nullable during migration. After backfill and verification, a follow-up migration makes it NOT NULL (tracked in TODOS.md).
- **Copilot tool compatibility** — `GET /ascents` and `POST /sessions/climbing` both keep working. New `get_sessions()` tool added. The copilot's `record.py` DraftCard flow is unchanged.
- **Empty crags** — crag browser shows "No sessions yet" empty state.
- **RockClimbing auto-link ambiguity** — multiple sessions on same date: pick session with most ascents, log warning. No match: activity stays standalone in the feed.
- **Duplicate session create** — UNIQUE(date, crag_id) constraint enforces idempotent creates.
- **Name propagation** — crag/route rename propagates via `propagate_crag_name()` helper to all denormalized fields on Ascent and ClimbingSession.

## Testing

- Backend: test `ClimbingSession` CRUD, migration script, session list with nested ascents
- Backend: test data migration — ascents grouped correctly, orphans handled, session_id backfilled
- Backend: test auto-link — RockClimbing matched to session, no match handled, ambiguous match handled
- Backend: test name propagation — rename crag, verify Ascent.crag_name and Session.crag_name updated
- Backend: test Strava type fallback for unknown activity types
- Backend: test `GET /stats/health` returns correct counts post-migration
- Backend: test duplicate session create returns existing + appends
- Backend: test `GET /feed` pagination — correct interleave, type filter, offset/limit
- Backend: test `get_sessions()` copilot tool — returns sessions with nested ascents
- Backend: test crag stats endpoint — session count, route count, hardest send, last visit
- Frontend: verify unified activity feed shows sessions and endurance as peers
- Frontend: verify two-level session expand (summary → routes)
- Frontend: verify weekly chart and calendar use new icons/categories
- Frontend: test crag browser — list with last-visited, detail with quick-stats
- Frontend: test session card shows linked watch duration when available
- Frontend: test dashboard recent activity uses unified feed
- E2E: create a session via copilot → verify it appears grouped in the unified feed

## Out of Scope

- Training load analytics (CTL/ATL/TSB) — separate feature
- Map view for crags with coordinates — future enhancement
- Editing sessions (only create for now; individual ascent edit still works)
- Strava direct integration (we sync from intervals.icu which already has Strava data)
- Photo attachments — exists in TODOS.md, could attach to sessions later
- Multi-user auth — no auth system yet
- Route database / community grades — future social feature
- Frontend unit tests — QA covers frontend validation
