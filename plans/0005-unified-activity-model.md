# 0005: Unified Activity Model

> Replace the split `EnduranceActivity` + `ClimbingSession` tables with a single `Activity` table. Activities are distinguished by type/subtype, not by source.

## Context

The current data model has two separate tables for activities:

- **`endurance_activity`** — synced from intervals.icu. Sparse data: name, duration, HR metrics. Includes `RockClimbing` activities that are essentially climbing sessions with no route detail.
- **`climbing_session`** — user-curated. Rich data: crag, routes, ascents, grades, tick types.

These are bridged by `ClimbingSession.linked_activity_id`, but the fundamental split causes problems:

1. **Synced climbing activities are second-class** — When intervals.icu syncs a `RockClimbing` activity named "Nagelplatten" (a crag), it only creates an `EnduranceActivity`. No crag, no session, no routes.
2. **Two code paths for everything** — Feed, dashboard, stats, edit UI, LLM tools all need separate handling for `kind: "session"` vs `kind: "endurance"`. Every new feature doubles the work.
3. **Fragile linking** — The `linked_activity_id` bridge is date-based and breaks with multiple climbing sessions per day.

**Goal:** One `Activity` table where the `type` field (climbing, run, ride, etc.) determines the shape of the data, not the source (UI, sync, CSV).

**Approach: Hard DB reset.** We are in development with no production database. intervals.icu is the source of truth for endurance data; climbing data was CSV-imported or manually entered. Instead of a complex data-preserving migration, we:
1. Squash all Alembic migrations into one clean initial migration
2. Drop and recreate the database
3. Re-import from intervals.icu + climbing CSV

## Approach

```
┌─────────────────────────────────────────────────────────┐
│                    BEFORE (current)                      │
│                                                         │
│  endurance_activity ──linked_activity_id──┐             │
│  (synced from intervals)                  │             │
│                                           ▼             │
│  climbing_session ◄── ascent.session_id                 │
│  (manual/CSV/copilot)     │                             │
│       │                   ▼                             │
│       └──────────► crag ◄── route                      │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    AFTER (this plan)                     │
│                                                         │
│  activity ◄── ascent.activity_id                        │
│  (all sources, all types)                               │
│       │                                                 │
│       └──────────► crag ◄── route                      │
│                                                         │
│  type="climbing" → has crag_id, ascents                 │
│  type="run/ride/..." → has duration, distance, HR       │
│  Both types can have both sets of fields (merged)       │
└─────────────────────────────────────────────────────────┘
```

**Activity model:**

```
activity
  id              PK
  date            date, indexed
  type            string ("climbing", "run", "ride", "fitness", etc.)
  subtype         string (Strava type: "TrailRun", "RockClimbing", etc.)
  name            string, nullable
  notes           string, nullable
  source          enum (intervals_icu | manual | csv_import)
  intervals_id    string, nullable, unique (sync dedup)
  duration_s      int, nullable
  distance_m      float, nullable
  elevation_gain_m float, nullable
  avg_hr          int, nullable
  max_hr          int, nullable
  training_load   float, nullable
  intensity       float, nullable
  crag_id         FK → crag.id, nullable
  crag_name       string, nullable (denormalized)
  raw_data        JSONB, nullable
  created_at      datetime

  UNIQUE(date, crag_id)   -- NULL crag_ids allow duplicates (SQL NULL semantics)
  INDEX(date), INDEX(type), INDEX(crag_id), UNIQUE(intervals_id)
```

**Type/subtype taxonomy** (mirrors frontend `sportCategory()` mapping):

| type | subtypes | has crag/ascents? |
|------|----------|-------------------|
| climbing | RockClimbing | yes |
| run | Run, TrailRun, VirtualRun | no |
| ride | Ride, GravelRide, MountainBikeRide, ... | no |
| swim | Swim | no |
| winter | AlpineSki, BackcountrySki, Snowboard, ... | no |
| water | Canoeing, Kayaking, ... | no |
| fitness | Hike, Walk, Yoga, WeightTraining, ... | no |
| other | Badminton, Golf, ... | no |

The `subtype` stores the original Strava type string. The `type` is the derived category. For manually created climbing sessions (no Strava origin), subtype defaults to `RockClimbing`.

## Steps

### Step 1: Activity model + clean Alembic migration

Replace both old models with a unified Activity model. Squash all migrations into one.

- [x] **Create `Activity` model** in `models/activity.py` (new file):
  - Fields as described in Approach above
  - `source` enum: `ActivitySource` (intervals_icu | manual | csv_import)
  - Relationships: `ascents` (list[Ascent]), `crag` (Crag | None)
  - Indexes: `ix_activity_date`, `ix_activity_type`, `ix_activity_intervals_id` (unique), `ix_activity_crag_id`, `uq_activity_date_crag` (regular UNIQUE on date + crag_id)
- [x] **Add `sport_category()` helper** to `models/activity.py`:
  - Maps Strava subtype string → type category (mirrors frontend `sportCategory()`)
  - Returns `"other"` for unknown subtypes with `logger.warning`
- [x] **Update `Ascent` model** in `models/climbing.py`:
  - Rename `session_id` → `activity_id` (FK → activity.id)
  - Rename `session` relationship → `activity`
  - Update index name: `ix_ascent_session_id` → `ix_ascent_activity_id`
- [x] **Update `Crag` model** relationship:
  - Rename `sessions` → `activities` (back_populates)
- [x] **Delete `models/endurance.py`**
- [x] **Remove `ClimbingSession` class** from `models/climbing.py`
- [x] **Squash Alembic migrations**: delete all files in `alembic/versions/`, write one clean initial migration that creates the final schema:
  - `crag`, `area`, `route` tables (unchanged)
  - `activity` table (replaces endurance_activity + climbing_session)
  - `ascent` table with `activity_id` FK (was `session_id`)
  - All indexes
- [x] **Write `scripts/dev-reset.sh`**:
  - Drops and recreates the database
  - Runs `alembic upgrade head`
  - Prints instructions: "Re-import: POST /sync/intervals + POST /import/climbing-csv"

**Files:** `app/backend/climbers_journal/models/activity.py` (new), `app/backend/climbers_journal/models/climbing.py` (edit), `app/backend/climbers_journal/models/endurance.py` (delete), `app/backend/alembic/versions/` (squash), `scripts/dev-reset.sh` (new)

### Step 2: Backend refactor (services + routers + LLM tools)

Update all backend code to use the unified Activity model.

**Services:**

- [x] **Rename `services/climbing.py` → `services/activity.py`** (the file now handles all activity types, not just climbing)
- [x] **Refactor `services/activity.py`**:
  - Replace all `ClimbingSession` references with `Activity` (filtered by `type == "climbing"`)
  - `get_or_create_session()` → `get_or_create_climbing_activity()`: creates `Activity(type="climbing", subtype="RockClimbing", ...)`
  - `list_climbing_sessions()` → `list_climbing_activities()`: filter `Activity.type == "climbing"`, eager load ascents
  - `get_climbing_session()` → `get_climbing_activity()`
  - `cascade_session_crag()` → `cascade_activity_crag()`: update `ascent.activity_id`
  - `serialize_session()` → `serialize_activity()`: unified serializer, includes both endurance and climbing fields
  - Remove `_try_link_activity()` and `auto_link_activity_to_session()` — no more linking
  - `get_activity_feed()`: simplify — single `SELECT` from `Activity` ordered by date, no union/dedup
  - `create_climbing_session()` → `create_climbing_activity()`: creates Activity + ascents
  - `get_data_health()`: update queries (activity_id instead of session_id)
- [x] **Refactor `services/sync.py`**:
  - `_parse_activity()`: returns `Activity`-shaped dict with `type` (category) and `subtype` (Strava type)
  - `upsert_activity()`: upserts into `Activity` table by `intervals_id`
  - Remove `auto_link_activity_to_session()` import and calls
  - `list_activities()`: query `Activity` with optional type filter
  - `update_activity()`: update any Activity's editable fields

**Routers:**

- [x] **Refactor `routers/climbing.py`**:
  - Keep existing URLs (`POST /sessions/climbing`, etc.), internally use Activity
  - Update request/response schemas: `session_id` → `activity_id` in responses
  - Include endurance fields in climbing response when present (duration, HR)
- [x] **Refactor `routers/sync.py`**:
  - `POST /sync/intervals` → upserts into `Activity`
  - `GET /activities` → returns all activities (optional type filter)
  - `PUT /activities/{id}` → update any activity (expand editable fields: name, notes, crag_id for climbing)
  - Update `ActivityResponse` schema to include climbing fields (crag_id, crag_name, ascent_count)
- [x] **Refactor `routers/stats.py`**:
  - Replace `EnduranceActivity` queries with `Activity`
  - Replace `ClimbingSession` queries with `Activity.type == "climbing"`
  - Feed endpoint: single query on `Activity`, no union/dedup
  - Weekly stats: query `Activity` grouped by type
  - Calendar: query `Activity`
- [x] **Refactor `routers/import_csv.py`**:
  - CSV import creates `Activity(type="climbing", source="csv_import")`

**LLM Tools:**

- [x] **Refactor `tools/journal.py`**:
  - Replace `ClimbingSession` with `Activity`
  - `get_sessions` tool: query `Activity.type == "climbing"`
  - `get_training_overview`: query `Activity` for all types
- [x] **Refactor `tools/record.py`**:
  - `parse_climbing_session`: creates draft that becomes `Activity(type="climbing")`

**Files:** `app/backend/climbers_journal/services/climbing.py` (→ `services/activity.py`), `app/backend/climbers_journal/services/sync.py`, `app/backend/climbers_journal/routers/climbing.py`, `app/backend/climbers_journal/routers/sync.py`, `app/backend/climbers_journal/routers/stats.py`, `app/backend/climbers_journal/routers/import_csv.py`, `app/backend/climbers_journal/tools/journal.py`, `app/backend/climbers_journal/tools/record.py`

### Step 3: Backend tests

Update all tests to use the unified model.

- [x] **Update `test_climbing.py`**:
  - Replace `ClimbingSession` fixtures with `Activity(type="climbing")`
  - Update assertions: `session_id` → `activity_id`
  - Test `create_climbing_activity()`, crag cascade, unified feed
- [x] **Update `test_sync.py`**:
  - Replace `EnduranceActivity` fixtures with `Activity`
  - Remove auto-link tests (concept no longer exists)
  - Test sync creates Activity with correct type/subtype
- [x] **Update `test_journal_tools.py`**: replace model fixtures
- [x] **Update `test_stats.py`**: replace model fixtures
- [x] **Add `test_sport_category()`**: verify all known Strava types map to correct category
- [x] **Add `test_serialize_activity()`**: verify unified serializer returns correct shape:
  - Climbing activity with ascents → includes `ascents`, `crag_name`, `crag_id`
  - Endurance activity → includes `duration_s`, `avg_hr`, `ascents: []`
  - Merged activity (climbing + HR data) → includes both sets of fields
- [x] **Verify**: `cd app/backend && uv run pytest` passes (140 tests)

**Files:** `app/backend/tests/test_climbing.py`, `app/backend/tests/test_sync.py`, `app/backend/tests/test_journal_tools.py`, `app/backend/tests/test_stats.py`

### Step 4: Frontend refactor

Unify frontend types and components to match the new backend.

- [x] **Update `api.ts` types**:
  - Merge `FeedSessionData` + `ActivityResponse` → single `Activity` type:
    - `id, date, type, subtype, name, notes, source`
    - `duration_s?, distance_m?, elevation_gain_m?, avg_hr?, max_hr?, training_load?`
    - `crag_id?, crag_name?`
    - `ascents?: Ascent[], ascent_count?: number`
  - Remove `FeedLinkedActivity` type
  - Simplify `FeedItem`: `type` field on Activity replaces `kind` discriminator
  - Update `CragSessionResponse` → reuse `Activity` type
- [x] **Update `api.ts` functions**:
  - `updateSession()` + `updateActivity()` → single `updateActivity(id, data)`
  - `fetchFeed()` returns `Activity[]`
  - `fetchCragSessions()` returns `Activity[]`
- [x] **Merge edit modals**:
  - `SessionEditModal` + `EnduranceEditModal` → single `ActivityEditModal`
  - Shows crag picker for climbing type, name/notes edit for all types
  - Reuses `CragCombobox`
- [x] **Update `app/log/page.tsx`**:
  - Remove `kind` discriminator logic
  - Render card based on `activity.type`: climbing gets expandable ascent rows, others get endurance metrics
- [x] **Update `app/page.tsx` (dashboard)**:
  - `RecentSessionRow` + `RecentEnduranceRow` → unified row component
- [x] **Update `app/crags/[id]/page.tsx`**: use `Activity` type
- [x] **Update `WeeklyActivity.tsx`**: minimal changes (already category-based)
- [x] **Update `app/calendar/page.tsx`**: use unified Activity
- [x] **Update `app/log/add/page.tsx`**: check response handling
- [x] **Verify**: `npx tsc --noEmit` — zero TypeScript errors

**Files:** `app/frontend/src/lib/api.ts`, `app/frontend/src/components/SessionEditModal.tsx` (→ `ActivityEditModal.tsx`), `app/frontend/src/components/EnduranceEditModal.tsx` (delete), `app/frontend/src/app/log/page.tsx`, `app/frontend/src/app/page.tsx`, `app/frontend/src/app/crags/[id]/page.tsx`, `app/frontend/src/components/WeeklyActivity.tsx`, `app/frontend/src/app/calendar/page.tsx`

## Edge Cases & Risks

- **Manual data loss on DB reset** — Manually entered climbing sessions are lost. Accepted: this is dev data, can be re-entered. No backup needed.
- **sport_category() drift** — Python and TypeScript mappings must stay in sync. Tracked in TODOS.md.
- **UNIQUE(date, crag_id) with NULLs** — SQL NULL semantics: `NULL != NULL`, so multiple activities without a crag on the same day are allowed. No partial index needed.
- **Frontend backward compatibility** — API response shape changes. Backend + frontend must be updated and deployed together (run dev-reset, then start both).
- **RockClimbing activities without crags** — Synced RockClimbing activities will have `crag_id=NULL` until the auto-crag enrichment feature (deferred). They show in the feed as regular activity cards. Users can manually assign crags via the edit UI.

## Testing

- **Sync creates Activity**: sync from intervals.icu → Activity records with correct type/subtype/source
- **Create climbing activity**: manual form → Activity(type="climbing") with ascents
- **CSV import**: upload → Activity(type="climbing", source="csv_import")
- **Feed returns unified activities**: single query, all types, ordered by date
- **Crag browser**: shows activities (was sessions), counts correct
- **Edit UI**: can edit name/notes on any activity, crag on climbing type
- **LLM tools**: training overview, sessions query returns correct data
- **sport_category()**: all known Strava types → correct category, unknown → "other"
- **Dev-reset script**: drops DB, creates schema, ready for re-import

## Out of Scope

- Auto-crag creation from synced RockClimbing activity names — follow-up plan, tracked in TODOS.md
- Shell session "Add routes" CTA — follow-up, depends on auto-crag
- Data-preserving migration — unnecessary, DB is reset
- Dashboard overhaul, vitals, photos — see [backlog/0006](backlog/0006-dashboard-vitals-photos.md)
