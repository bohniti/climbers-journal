# 0006: Dashboard Overhaul, Vitals, Tech Debt & Photos

> Rich dashboard with filtered charts + vitals + climbing progression + PR badges, photo attachments, and activity_id NOT NULL migration. Deferred from plan 0004 until the unified activity model (plan 0005) is stable.

## Context

These steps were originally plan 0004 Steps 3–8. They were deferred to prioritize the unified activity model (plan 0005), which changes the underlying data model these features depend on.

**Prerequisites:** Plan 0005 (Unified Activity Model) must be fully implemented before starting these steps. Key changes from 0005 that affect this plan:
- `ClimbingSession` → `Activity` (type="climbing")
- `EnduranceActivity` → `Activity` (type=run/ride/etc.)
- `session_id` → `activity_id` on Ascent
- `linked_activity_id` removed — endurance metrics live directly on the Activity
- Feed is a single `Activity[]` query, no more union + dedup

**Re-evaluate before starting:** Some steps may simplify significantly after the unified model ships (e.g., feed queries, stats queries, chart data). Review each step against the new model before implementing.

## Steps

### Step 1: Dashboard overhaul — weekly chart with filter buttons

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

### Step 2: Dashboard overhaul — quarterly trend + activity stats panel

Add a quarterly activity trend line graph and per-sport stats panel.

- [ ] **Backend: `GET /stats/quarterly`** endpoint:
  - Params: `months=3` (default)
  - Returns: `[{ week_start: "2026-01-06", climbing: 3, run: 2, ride: 1, fitness: 1, total: 7 }, ...]`
  - SQL: aggregate `Activity` by ISO week, grouped by `type`
  - Uses existing date indexes
- [ ] **Backend: `GET /stats/activity-stats`** endpoint:
  - Returns per-category stats for configurable period (default: this year):
  - Climbing: max grade climbed, max grade attempted, avg routes per activity, avg grade per activity
  - Running: km this week, km this year
  - Cycling: km this week, km this year
  - Fitness: total training time this week, this year
  - Guard against division by zero (0 activities → return null)
- [ ] **Frontend: `QuarterlyTrend` component**:
  - Line graph (Recharts `LineChart`) with one dot per week
  - X-axis: week labels, Y-axis: activity count
  - Shows 12 weeks by default
  - Colored line per category (or single "total" line with option to split)
- [ ] **Frontend: `ActivityStatsPanel` component**:
  - 4-column grid (or 2x2 on mobile): Running, Climbing, Cycling, Fitness
  - Each panel shows `<ActivityIcon>` + key stats
  - Climbing: max grade (send), max grade (attempt), avg routes/activity, avg grade/activity
  - Running: km/week, km this year
  - Cycling: km/week, km this year
  - Fitness: time this week, time this year
- [ ] Add both components to dashboard layout, below weekly chart

**Files:** `app/backend/climbers_journal/routers/stats.py`, `app/frontend/src/components/QuarterlyTrend.tsx` (new), `app/frontend/src/components/ActivityStatsPanel.tsx` (new), `app/frontend/src/app/page.tsx`, `app/frontend/src/lib/api.ts`

### Step 3: Dashboard overhaul — climbing progression + PR badges

Add climbing grade progression graph and personal record detection with badges.

- [ ] **Backend: `GET /stats/climbing-progress`** endpoint:
  - Returns: `[{ date: "2026-01-15", max_grade: "6c+", avg_grade: "6a", activity_count: 1 }, ...]`
  - Grouped by activity date, shows progression of max and avg grade over time
  - Only includes successful sends (not attempts)
- [ ] **Backend: `GET /stats/personal-records`** endpoint:
  - Returns: `[{ type: "hardest_flash", grade: "7a", date: "2026-03-10", route_name: "Moonlight", crag_name: "Kletterhalle Wien", is_new: true }, ...]`
  - PR types: hardest_send (any send), hardest_flash, hardest_onsight
  - `is_new` = true if achieved in the last 7 days
  - SQL: `MAX(grade)` per tick_type category, compare to historical max
- [ ] **Frontend: `ClimbingProgress` component**:
  - Line graph with two lines: max grade + avg grade over time
  - X-axis: activity dates, Y-axis: grade (needs grade-to-numeric mapping for chart)
  - Dot on each data point, hoverable tooltip with activity details
- [ ] **Frontend: `PRBadges` component**:
  - Shown at top of dashboard when `is_new = true` on any PR
  - Celebratory badge: "New PR! First 7a+ flash at Kletterhalle Wien"
  - Dismissable (localStorage flag)
  - Subtle animation on first render
- [ ] **Grade-to-numeric mapping utility (shared):**
  - Backend: `GRADE_ORDER` dict in a shared module (e.g., `climbers_journal/grades.py`) mapping French grades to integers: `{"3a": 1, "3a+": 2, "3b": 3, ..., "9c": 60}`. Use in SQL `ORDER BY` via `CASE WHEN` or post-query sort for correct "hardest grade" results.
  - Frontend: matching `GRADE_ORDER` in `constants.ts` for chart Y-axis numeric mapping.
  - Fixes existing bug: `ORDER BY grade DESC` is lexicographic, which breaks at grade boundaries (e.g., "10a" vs "9b").
  - Apply to: `GET /stats/climbing-progress`, `GET /stats/personal-records`, `get_crag_stats` (hardest send).

**Files:** `app/backend/climbers_journal/grades.py` (new), `app/backend/climbers_journal/routers/stats.py`, `app/backend/climbers_journal/services/climbing.py`, `app/frontend/src/components/ClimbingProgress.tsx` (new), `app/frontend/src/components/PRBadges.tsx` (new), `app/frontend/src/app/page.tsx`, `app/frontend/src/lib/api.ts`, `app/frontend/src/lib/constants.ts`

### Step 4: Vitals dashboard — wellness sync + display

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

### Step 5: Tech debt — activity_id NOT NULL

- [ ] **Pre-check:** Run `GET /stats/health` — verify `orphaned_ascents = 0` (ascents with NULL `activity_id`)
  - If > 0: run backfill script first (group orphans by date+crag, create activities, link)
  - Do NOT proceed with migration until orphan count = 0
- [ ] **Alembic migration:** `ALTER TABLE ascent ALTER COLUMN activity_id SET NOT NULL`
- [ ] **Update Ascent model:** remove `| None` from `activity_id` field type
- [ ] **Verify:** run backend tests, check `GET /stats/health` post-migration
- [ ] Remove the "Make session_id NOT NULL" item from TODOS.md (now activity_id)

**Files:** `app/backend/climbers_journal/models/climbing.py`, `app/backend/alembic/versions/` (new migration), `TODOS.md`

### Step 6: Photo attachments

Attach photos to ascents and activities. Local disk storage with DB link.

- [ ] **Backend: `Photo` model** (`models/photo.py`):
  - `id`, `ascent_id` (nullable FK), `activity_id` (nullable FK), `filename` (UUID-based), `original_name`, `content_type`, `size_bytes`, `created_at`
  - CHECK constraint: `ascent_id IS NOT NULL OR activity_id IS NOT NULL`
  - Index on `ascent_id`, index on `activity_id`
- [ ] **Alembic migration:** create `photo` table
- [ ] **Backend: `POST /photos/upload`** endpoint:
  - Multipart form: `file` (UploadFile) + `ascent_id` (optional) + `activity_id` (optional)
  - Validate: at least one of ascent_id/activity_id provided
  - Validate: file extension in `.jpg`, `.jpeg`, `.png`, `.webp`
  - Validate: Content-Type is image/*
  - Validate: file size <= 10MB
  - Generate UUID filename: `{uuid}.{ext}`
  - Save to `{MEDIA_DIR}/photos/{uuid}.{ext}`
  - Create `Photo` DB record
  - Catch `OSError` (disk full) → 500 with log
  - Log: `"Photo uploaded: {uuid} for ascent/activity {id}, {size_kb}KB"`
  - Return `PhotoResponse` with id, URL
- [ ] **Backend: `GET /photos/{photo_id}/file`** endpoint:
  - Serve file via `FileResponse`
  - Set `Cache-Control: public, max-age=31536000, immutable`
  - 404 if file missing from disk
- [ ] **Backend: `GET /photos`** endpoint:
  - Filter by `ascent_id` or `activity_id`
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
- [ ] **Frontend: photo gallery on activity/ascent cards**:
  - Thumbnail strip below card content (when expanded)
  - Click to enlarge (lightbox-style)
  - Delete button on each photo
- [ ] Add `uploadPhoto`, `fetchPhotos`, `deletePhoto` to `api.ts`

**Files:** `app/backend/climbers_journal/models/photo.py` (new), `app/backend/climbers_journal/routers/photos.py` (new), `app/backend/alembic/versions/` (new migration), `app/backend/climbers_journal/config.py`, `app/frontend/src/components/PhotoUpload.tsx` (new), `app/frontend/src/components/PhotoGallery.tsx` (new), `app/frontend/src/app/log/page.tsx`, `app/frontend/src/lib/api.ts`

## Edge Cases & Risks

- **Stats division by zero** — guard all averages with `if count > 0`, return null otherwise.
- **activity_id NOT NULL migration** — MUST verify orphan count = 0 via `/stats/health` before running.
- **Photo upload: path traversal** — UUID-based filenames, never use user-provided filename for storage path.
- **Photo upload: malicious file** — validate MIME type + extension whitelist, reject non-image.
- **Photo upload: disk full** — catch `OSError`, return 500 with user-friendly message, log.
- **Wellness sync: malformed data** — per-entry try/except, skip bad entries with `logger.warning`.
- **Wellness sync: rate limit** — reuse existing exponential backoff pattern from activity sync.
- **Wellness sync: timeout** — retry 2x then raise with user-visible error.
- **Grade-to-numeric mapping** — needed for climbing progress chart Y-axis. Use UIAA/French grade scale.

## Testing

- **Quarterly stats:** 12 weeks of data → correct weekly aggregates. Empty DB → empty array. 1 week only → single entry.
- **Activity stats:** all categories populated. 0 activities → no division by zero. Single category only → others show null.
- **Climbing progress:** grade timeline correct. No ascents → empty. All same grade → flat line.
- **PR detection:** new grade achieved → `is_new=true`. No new PR → `is_new=false`. First-ever ascent → all PRs are new.
- **Wellness sync:** valid data → entries created. Malformed entry → skipped with log. 429 → retry. Timeout → retry 2x then error. Duplicate date → upsert.
- **Vitals endpoint:** 7 days data → correct array. No data → empty array.
- **activity_id NOT NULL:** migration succeeds when 0 orphans. Migration fails when orphans exist.
- **Photo upload:** valid image → saved + DB record. Invalid MIME → 422. Oversized → 413. Path traversal filename → UUID rename. Disk full → 500.
- **Photo serve:** valid ID → file response with cache headers. Missing file → 404.

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
