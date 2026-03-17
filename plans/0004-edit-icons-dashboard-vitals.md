# 0004: Edit UI, Icon Refresh, Dashboard Overhaul, Vitals & Tech Debt

> Manual edit for sessions/ascents, replace emoji icons with PNGs, rich dashboard with filtered charts + vitals + climbing progression + PR badges, photo attachments, and session_id NOT NULL migration.

## Context

Five pain points converge:

1. **No edit UI** — users can't fix wrong crags on climbing activities. Data quality degrades over time. Backend has `PUT /ascents/{id}` but the frontend has no edit forms, and sessions can't be edited at all.
2. **Emoji icons** — `🧗🏃💪` look unprofessional and can't be styled/themed. The user has 8 PNG icons ready in Downloads.
3. **Basic dashboard** — only 2 stats cards + weekly bar chart + grade pyramid + recent feed. No per-sport breakdowns, no trends, no vitals.
4. **No vitals** — intervals.icu has wellness data (sleep, HR, HRV) and `get_wellness()` already exists in the backend but is unused.
5. **Tech debt** — `session_id` is still nullable, photos are deferred from plan 0003.

## Approach

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js 15)                       │
│                                                                     │
│  Dashboard (page.tsx → layout grid composing 6+ components)         │
│  ┌──────────────┐ ┌───────────────┐ ┌──────────────┐              │
│  │WeeklyActivity│ │QuarterlyTrend │ │ActivityStats │              │
│  │ +filter btns │ │(line, 12 wks) │ │(4 sport pane)│              │
│  ├──────────────┤ ├───────────────┤ ├──────────────┤              │
│  │ClimbingProg  │ │VitalsPanel    │ │PRBadges      │              │
│  │(grade trend) │ │(sleep/HR/HRV) │ │(new mileston)│              │
│  └──────────────┘ └───────────────┘ └──────────────┘              │
│                                                                     │
│  <ActivityIcon /> — shared component mapping category → PNG         │
│  Edit modals: SessionEditModal, AscentEditModal (searchable crag)   │
│  Photo upload + gallery on session/ascent cards                     │
│                                                                     │
│  public/icons/ — runner.png, climber.png, cycling.png, etc.        │
└────────────────────────────────────┬────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────┐
│                         BACKEND (FastAPI)                            │
│                                                                     │
│  New/updated endpoints:                                             │
│  PUT /sessions/climbing/{id}  — edit session (crag, notes)          │
│  PUT /ascents/{id}            — expanded (+ crag_id, route_id, grade)│
│  POST /photos/upload          — multipart file upload               │
│  GET /photos/{id}/file        — serve photo file                    │
│  POST /wellness/sync          — sync wellness from intervals.icu    │
│  GET /vitals                  — 7-day wellness data                 │
│  GET /stats/quarterly         — weekly activity counts over quarter │
│  GET /stats/activity-stats    — per-sport breakdowns                │
│  GET /stats/climbing-progress — grade milestones over time          │
│  GET /stats/personal-records  — PR detection for badges             │
│                                                                     │
│  New models: WellnessEntry, Photo                                   │
│  Migration: session_id NOT NULL, wellness_entry, photo tables       │
│                                                                     │
│  media/photos/ — local file storage (UUID-named)                    │
└─────────────────────────────────────────────────────────────────────┘
```

- Extract dashboard into self-fetching components (matches existing `WeeklyActivity.tsx` pattern)
- Replace emoji `icon` field in `SPORT_TYPES` with image paths, create `<ActivityIcon>` component
- Edit modals with cascade confirmation for crag changes, searchable combobox for crag picker
- Photo table with dual nullable FK (`ascent_id` OR `session_id`, CHECK at least one set)
- Wellness sync mirrors existing activity sync pattern (retry, backoff, per-entry error handling)
- PR detection via `MAX(grade)` comparison against historical data

## Steps

### Step 1: Icon system refresh

Replace all emoji icons with PNG images. Create a shared `<ActivityIcon>` component.

- [x] Copy icons from `/Users/timo/Downloads/icons/` to `app/frontend/public/icons/`
- [x] Rename `defauld.png` → `default.png`
- [x] Update `SPORT_TYPES` in `constants.ts`: change `icon` field from emoji string to image filename
  - `run` category → `runner.png`
  - `ride` category → `cycling.png`
  - `climbing` category → `climber.png`
  - `winter` category → `skiing.png`
  - `fitness` category → `gym.png`
  - `water` category → `default.png`
  - `other` category → `default.png`
  - Unknown/fallback → `default.png`
- [x] Update `CLIMBING_STYLE_ICONS` — map to `climber.png` (single icon for all climbing sub-types)
- [x] Create `<ActivityIcon>` component (`app/frontend/src/components/ActivityIcon.tsx`):
  - Props: `type: string` (sport type) OR `category: SportCategory`, `size?: "sm" | "md" | "lg"`
  - Renders `<Image>` (next/image) with the mapped PNG
  - Sizes: sm=16px, md=24px, lg=32px
- [x] Replace all `sportIcon()` emoji calls with `<ActivityIcon>` across:
  - `WeeklyActivity.tsx` (day accordion items, chart legend)
  - `app/log/page.tsx` (EnduranceCard, ClimbingSessionCard)
  - `app/page.tsx` (RecentEnduranceRow, RecentSessionRow)
  - `app/crags/page.tsx` (crag list items)
  - `app/crags/[id]/page.tsx` (session cards)
  - `app/calendar/page.tsx` (day cells)
- [x] Replace `🔥` streak emoji with a styled element or icon
- [x] Add `home.png` icon for crag/location display where appropriate
- [x] Verify: no emoji icons remain in any UI component

**Files:** `app/frontend/public/icons/` (new directory), `app/frontend/src/components/ActivityIcon.tsx` (new), `app/frontend/src/lib/constants.ts`, `app/frontend/src/components/WeeklyActivity.tsx`, `app/frontend/src/app/log/page.tsx`, `app/frontend/src/app/page.tsx`, `app/frontend/src/app/crags/page.tsx`, `app/frontend/src/app/crags/[id]/page.tsx`, `app/frontend/src/app/calendar/page.tsx`

### Step 2: Session & ascent edit UI

Build edit modals for climbing sessions and ascents. Expand backend edit surface.

**Pre-step fixes (from eng review):**
- [x] **Consolidate session serialization** — delete `_serialize_session()` from `climbing.py` router, use `serialize_session()` (renamed from `_session_to_dict`) in the service for all callers. Eliminates DRY violation before adding more call sites.
- [x] **Fix `update_ascent()` to support clearing fields** — change `body.model_dump(exclude_none=True)` to `body.model_dump(exclude_unset=True)` in the router. Remove `if value is not None` guard in the service. This allows setting fields to `null` (e.g., clearing notes).

- [x] **Backend: expand `AscentUpdate` schema** — add optional `route_id`, `grade` fields (NOT `crag_id` — crag changes are session-level only, per eng review)
- [x] **Backend: `PUT /sessions/climbing/{id}`** endpoint:
  - Accepts: `crag_id` (optional), `notes` (optional)
  - On crag change: validate target crag exists, check UNIQUE(date, crag_id) → 409 on conflict
  - Cascade: bulk `UPDATE ascent SET crag_id=?, crag_name=? WHERE session_id=?` (single query, not N+1)
  - Update `session.crag_id`, `session.crag_name`
  - Log: `"Session {id}: crag changed {old} → {new}, {n} ascents updated"`
  - Return updated session with nested ascents
- [x] **Backend: handle IntegrityError** on session crag update → return 409 "Session already exists at this crag on this date"
- [x] **Frontend: `SessionEditModal` component**:
  - Triggered by edit button on `ClimbingSessionCard`
  - Searchable crag combobox (type to filter, show recent/frequent at top)
  - Notes textarea
  - Confirmation dialog on crag change: "Move {N} routes to {new crag name}?"
  - Disable save button during submit (prevent double-click)
  - Error toast on failure, re-enable button
  - On success: refresh feed/session data
- [x] **Frontend: `AscentEditModal` component**:
  - Triggered by edit button on individual route row (expanded session card)
  - Fields: grade, tick_type, tries, rating, notes, partner
  - Crag change via session edit only (not per-ascent) for consistency
  - Route name/grade update
- [x] **Frontend: searchable crag combobox** (reusable component):
  - Fetches crags via `listCrags()`
  - Text input with filtered dropdown
  - Shows "No crags found" empty state
  - Handles 100+ crags performantly (virtual scroll if needed)
- [x] Add edit buttons to `ClimbingSessionCard` and route rows in log page
- [x] Add `updateSession` and update `updateAscent` in `api.ts`

**Post-implementation fixes (from QA):**
- [x] **Fix nested `<button>` hydration error** — `ClimbingSessionCard` wraps the header in a `<button>` for expand/collapse (line 277), and the edit `<button>` (line 316) is nested inside it. HTML forbids `<button>` inside `<button>`, causing a React hydration error. **Fix:** change the outer `<button>` to a `<div>` with `role="button"`, `tabIndex={0}`, `onClick`, and `onKeyDown` (Enter/Space) for accessibility.
- [x] **Fix `EnduranceCard` same pattern** — `EnduranceCard` uses a `<button>` as its outer wrapper (line 479). Change to `<div>` with click handler to match, and to allow adding an edit button inside.
- [x] **Add edit button to `EnduranceCard`** — endurance activities currently have no edit UI. Added `PUT /activities/{id}` backend endpoint (name field), `EnduranceEditModal` component, and edit button matching the `ClimbingSessionCard` pattern.

**Lessons learned:**
> The edit button was placed _inside_ the outer `<button>` element that handles expand/collapse. This violates HTML spec (`<button>` cannot contain `<button>`) and causes React hydration errors in Next.js. The root cause: the card's expand/collapse area was implemented as a `<button>` for accessibility, but when interactive children (edit buttons) were added inside it, the nesting became invalid. **Takeaway:** when a card needs both a clickable expand area AND interactive child elements (buttons, links), use a `<div role="button">` for the outer container instead of a `<button>`. Always validate that interactive elements are not nested inside other interactive elements.

**Files:** `app/backend/climbers_journal/routers/climbing.py`, `app/backend/climbers_journal/services/climbing.py`, `app/frontend/src/components/SessionEditModal.tsx` (new), `app/frontend/src/components/AscentEditModal.tsx` (new), `app/frontend/src/components/CragCombobox.tsx` (new), `app/frontend/src/app/log/page.tsx`, `app/frontend/src/lib/api.ts`

### Step 3: Dashboard overhaul — weekly chart with filter buttons

Upgrade the weekly activity chart with sport category filter buttons using the new icons.

- [ ] Add filter buttons row above the chart: All, Running, Climbing, Cycling, Fitness
  - Each button shows the corresponding `<ActivityIcon>` + label
  - Active button has highlighted border/background
  - "All" shows stacked bars (existing behavior)
  - Category filter shows only that category's bars
- [ ] Update `fetchWeekly()` or add client-side filtering (data already has per-category counts)
- [ ] Update chart legend to use `<ActivityIcon>` instead of colored squares
- [ ] Keep day accordion below chart, filtered to match selected category

**Files:** `app/frontend/src/components/WeeklyActivity.tsx`, `app/frontend/src/lib/constants.ts`

### Step 4: Dashboard overhaul — quarterly trend + activity stats panel

Add a quarterly activity trend line graph and per-sport stats panel.

- [ ] **Backend: `GET /stats/quarterly`** endpoint:
  - Params: `months=3` (default)
  - Returns: `[{ week_start: "2026-01-06", climbing: 3, run: 2, ride: 1, fitness: 1, total: 7 }, ...]`
  - SQL: aggregate activities by ISO week, grouped by sport category
  - Uses existing date indexes
- [ ] **Backend: `GET /stats/activity-stats`** endpoint:
  - Returns per-category stats for configurable period (default: this year):
  - Climbing: max grade climbed, max grade attempted, avg routes per session, avg grade per session
  - Running: km this week, km this year
  - Cycling: km this week, km this year
  - Fitness: total training time this week, this year
  - Guard against division by zero (0 sessions → return "—" / null)
- [ ] **Frontend: `QuarterlyTrend` component**:
  - Line graph (Recharts `LineChart`) with one dot per week
  - X-axis: week labels, Y-axis: activity count
  - Shows 12 weeks by default
  - Colored line per category (or single "total" line with option to split)
- [ ] **Frontend: `ActivityStatsPanel` component**:
  - 4-column grid (or 2×2 on mobile): Running, Climbing, Cycling, Fitness
  - Each panel shows `<ActivityIcon>` + key stats
  - Climbing: max grade (send), max grade (attempt), avg routes/session, avg grade/session
  - Running: km/week, km this year
  - Cycling: km/week, km this year
  - Fitness: time this week, time this year
- [ ] Add both components to dashboard layout, below weekly chart

**Files:** `app/backend/climbers_journal/routers/stats.py`, `app/frontend/src/components/QuarterlyTrend.tsx` (new), `app/frontend/src/components/ActivityStatsPanel.tsx` (new), `app/frontend/src/app/page.tsx`, `app/frontend/src/lib/api.ts`

### Step 5: Dashboard overhaul — climbing progression + PR badges

Add climbing grade progression graph and personal record detection with badges.

- [ ] **Backend: `GET /stats/climbing-progress`** endpoint:
  - Returns: `[{ date: "2026-01-15", max_grade: "6c+", avg_grade: "6a", session_count: 1 }, ...]`
  - Grouped by session date, shows progression of max and avg grade over time
  - Only includes successful sends (not attempts)
- [ ] **Backend: `GET /stats/personal-records`** endpoint:
  - Returns: `[{ type: "hardest_flash", grade: "7a", date: "2026-03-10", route_name: "Moonlight", crag_name: "Kletterhalle Wien", is_new: true }, ...]`
  - PR types: hardest_send (any send), hardest_flash, hardest_onsight
  - `is_new` = true if achieved in the last 7 days
  - SQL: `MAX(grade)` per tick_type category, compare to historical max
- [ ] **Frontend: `ClimbingProgress` component**:
  - Line graph with two lines: max grade + avg grade over time
  - X-axis: session dates, Y-axis: grade (needs grade-to-numeric mapping for chart)
  - Dot on each data point, hoverable tooltip with session details
- [ ] **Frontend: `PRBadges` component**:
  - Shown at top of dashboard when `is_new = true` on any PR
  - Celebratory badge: "New PR! First 7a+ flash at Kletterhalle Wien"
  - Dismissable (localStorage flag)
  - Subtle animation on first render
- [ ] **Grade-to-numeric mapping utility (shared, from eng review):**
  - Backend: `GRADE_ORDER` dict in a shared module (e.g., `climbers_journal/grades.py`) mapping French grades to integers: `{"3a": 1, "3a+": 2, "3b": 3, ..., "9c": 60}`. Use in SQL `ORDER BY` via `CASE WHEN` or post-query sort for correct "hardest grade" results.
  - Frontend: matching `GRADE_ORDER` in `constants.ts` for chart Y-axis numeric mapping.
  - Fixes existing bug: `ORDER BY grade DESC` is lexicographic, which breaks at grade boundaries (e.g., "10a" vs "9b").
  - Apply to: `GET /stats/climbing-progress`, `GET /stats/personal-records`, `_build_climbing_stats` (hardest send), `get_crag_stats` (hardest send).

**Files:** `app/backend/climbers_journal/grades.py` (new), `app/backend/climbers_journal/routers/stats.py`, `app/backend/climbers_journal/services/climbing.py`, `app/frontend/src/components/ClimbingProgress.tsx` (new), `app/frontend/src/components/PRBadges.tsx` (new), `app/frontend/src/app/page.tsx`, `app/frontend/src/lib/api.ts`, `app/frontend/src/lib/constants.ts`

### Step 6: Vitals dashboard — wellness sync + display

Connect to intervals.icu wellness data and display sleep, resting HR, and HRV.

- [ ] **Backend: `WellnessEntry` model** (`models/wellness.py`):
  - `id`, `date` (unique), `resting_hr`, `hrv`, `sleep_quality`, `sleep_seconds`, `raw_data` (JSONB)
  - Index on `date`
  - UNIQUE constraint on `date` for upsert
- [ ] **Alembic migration:** create `wellness_entry` table
- [ ] **Backend: `POST /wellness/sync`** endpoint:
  - Params: `oldest`, `newest` (dates, default last 30 days)
  - Calls existing `get_wellness()` from `intervals.py`
  - Upserts entries by date
  - Per-entry try/except: skip malformed entries with `logger.warning`
  - Retry on 429 (reuse existing exponential backoff pattern from sync.py)
  - Catch `httpx.TimeoutException` — retry 2x then raise
  - Returns: `{ synced: N, skipped: N }`
- [ ] **Backend: `GET /vitals`** endpoint:
  - Params: `days=7` (default)
  - Returns: `[{ date: "2026-03-17", resting_hr: 52, hrv: 65, sleep_quality: 3, sleep_hours: 7.5 }, ...]`
  - Ordered by date ascending for chart rendering
- [ ] **Frontend: `VitalsPanel` component**:
  - 3 line graphs (Recharts `LineChart`): resting HR, HRV, sleep quality
  - 7-day window with date labels on X-axis
  - Each graph is small (sparkline-style) with current value highlighted
  - Empty state: "Sync your wellness data" CTA button → triggers wellness sync
  - After sync: auto-refresh graphs
- [ ] Add wellness sync button to Import page alongside existing intervals.icu sync
- [ ] Add `syncWellness`, `fetchVitals` to `api.ts`

**Files:** `app/backend/climbers_journal/models/wellness.py` (new), `app/backend/climbers_journal/routers/wellness.py` (new), `app/backend/climbers_journal/services/sync.py`, `app/backend/alembic/versions/` (new migration), `app/frontend/src/components/VitalsPanel.tsx` (new), `app/frontend/src/app/page.tsx`, `app/frontend/src/lib/api.ts`

### Step 7: Tech debt — session_id NOT NULL

- [ ] **Pre-check:** Run `GET /stats/health` — verify `orphaned_ascents = 0`
  - If > 0: run backfill script first (group orphans by date+crag, create sessions, link)
  - Do NOT proceed with migration until orphan count = 0
- [ ] **Alembic migration:** `ALTER TABLE ascent ALTER COLUMN session_id SET NOT NULL`
- [ ] **Update Ascent model:** remove `| None` from `session_id` field type
- [ ] **Verify:** run backend tests, check `GET /stats/health` post-migration
- [ ] Remove the "Make session_id NOT NULL" item from TODOS.md

**Files:** `app/backend/climbers_journal/models/climbing.py`, `app/backend/alembic/versions/` (new migration), `TODOS.md`

### Step 8: Photo attachments

Attach photos to ascents and sessions. Local disk storage with DB link.

- [ ] **Backend: `Photo` model** (`models/photo.py`):
  - `id`, `ascent_id` (nullable FK), `session_id` (nullable FK), `filename` (UUID-based), `original_name`, `content_type`, `size_bytes`, `created_at`
  - CHECK constraint: `ascent_id IS NOT NULL OR session_id IS NOT NULL`
  - Index on `ascent_id`, index on `session_id`
- [ ] **Alembic migration:** create `photo` table
- [ ] **Backend: `POST /photos/upload`** endpoint:
  - Multipart form: `file` (UploadFile) + `ascent_id` (optional) + `session_id` (optional)
  - Validate: at least one of ascent_id/session_id provided
  - Validate: file extension in `.jpg`, `.jpeg`, `.png`, `.webp`
  - Validate: Content-Type is image/*
  - Validate: file size ≤ 10MB
  - Generate UUID filename: `{uuid}.{ext}`
  - Save to `{MEDIA_DIR}/photos/{uuid}.{ext}`
  - Create `Photo` DB record
  - Catch `OSError` (disk full) → 500 with log
  - Log: `"Photo uploaded: {uuid} for ascent/session {id}, {size_kb}KB"`
  - Return `PhotoResponse` with id, URL
- [ ] **Backend: `GET /photos/{photo_id}/file`** endpoint:
  - Serve file via `FileResponse`
  - Set `Cache-Control: public, max-age=31536000, immutable`
  - 404 if file missing from disk
- [ ] **Backend: `GET /photos`** endpoint:
  - Filter by `ascent_id` or `session_id`
  - Returns list of `PhotoResponse`
- [ ] **Backend: `DELETE /photos/{photo_id}`** endpoint:
  - Delete DB record + file from disk
  - 404 if not found
- [ ] **Config:** add `MEDIA_DIR` to settings (default: `./media`)
- [ ] **Frontend: photo upload component**:
  - Drag-and-drop or click-to-upload
  - Preview before upload
  - Progress indicator for large files
  - Max 5 photos per upload action
- [ ] **Frontend: photo gallery on session/ascent cards**:
  - Thumbnail strip below card content (when expanded)
  - Click to enlarge (lightbox-style)
  - Delete button on each photo
- [ ] Add `uploadPhoto`, `fetchPhotos`, `deletePhoto` to `api.ts`

**Files:** `app/backend/climbers_journal/models/photo.py` (new), `app/backend/climbers_journal/routers/photos.py` (new), `app/backend/alembic/versions/` (new migration), `app/backend/climbers_journal/config.py`, `app/frontend/src/components/PhotoUpload.tsx` (new), `app/frontend/src/components/PhotoGallery.tsx` (new), `app/frontend/src/app/log/page.tsx`, `app/frontend/src/lib/api.ts`

## Edge Cases & Risks

- **Edit cascade confirmation** — crag change on a session cascades to all ascents. Requires user confirmation dialog ("Move N routes to {crag}?"). Bulk SQL update, not N+1.
- **UNIQUE conflict on session crag edit** — if target (date, crag_id) already has a session → 409 with clear message. Frontend shows toast.
- **Photo upload: path traversal** — UUID-based filenames, never use user-provided filename for storage path.
- **Photo upload: malicious file** — validate MIME type + extension whitelist, reject non-image.
- **Photo upload: disk full** — catch `OSError`, return 500 with user-friendly message, log.
- **Wellness sync: malformed data** — per-entry try/except, skip bad entries with `logger.warning`.
- **Wellness sync: rate limit** — reuse existing exponential backoff pattern from activity sync.
- **Wellness sync: timeout** — retry 2x then raise with user-visible error.
- **Stats division by zero** — guard all averages with `if count > 0`, return null otherwise.
- **session_id NOT NULL migration** — MUST verify orphan count = 0 via `/stats/health` before running. Migration fails if orphans exist.
- **Icon missing** — `<ActivityIcon>` falls back to `default.png` for unmapped categories.
- **Searchable combobox with 100+ crags** — virtualized dropdown or debounced filter for performance.
- **Grade-to-numeric mapping** — needed for climbing progress chart Y-axis. Grades like "6a", "6a+", "6b" need consistent ordering. Use UIAA/French grade scale.

## Testing

- **Edit cascade:** create session with 5 ascents at Crag A, edit to Crag B, verify all ascents updated. Test UNIQUE conflict → 409.
- **Edit ascent expanded fields:** update grade, route_id, crag_id individually and in combination.
- **Photo upload:** valid image → saved + DB record. Invalid MIME → 422. Oversized → 413. Path traversal filename → UUID rename. Disk full → 500.
- **Photo serve:** valid ID → file response with cache headers. Missing file → 404.
- **Wellness sync:** valid data → entries created. Malformed entry → skipped with log. 429 → retry. Timeout → retry 2x then error. Duplicate date → upsert.
- **Vitals endpoint:** 7 days data → correct array. No data → empty array. Partial data (3 of 7 days) → returns available days.
- **Quarterly stats:** 12 weeks of data → correct weekly aggregates. Empty DB → empty array. 1 week only → single entry.
- **Activity stats:** all categories populated. 0 sessions → no division by zero. Single category only → others show null.
- **Climbing progress:** grade timeline correct. No ascents → empty. All same grade → flat line.
- **PR detection:** new grade achieved → `is_new=true`. No new PR → `is_new=false`. First-ever ascent → all PRs are new.
- **session_id NOT NULL:** migration succeeds when 0 orphans. Migration fails when orphans exist.
- **Icon rendering:** all sport types render correct PNG. Unknown type → default.png. No console warnings for known types.
- **Searchable combobox:** type to filter. Select crag. Empty state. 100+ crags renders without lag.

## Out of Scope

- Training load analytics (CTL/ATL/TSB) — Phase 2, needs more wellness data accumulation
- Garmin/GPX import — Phase 2, separate integration
- Interactive crag maps — Phase 2, needs coordinates on crag model
- Multi-user auth — Phase 3, architectural change
- Docker/CI/CD — orthogonal to this plan
- CSV export — orthogonal, tracked in TODOS.md
- Inline editing (click-to-edit fields) — future polish, modals ship first
- S3 photo storage — follow-up if local disk becomes insufficient
- Smart empty states — polish during QA
- Insights endpoint (`GET /stats/insights`) — tracked in TODOS.md as follow-up
