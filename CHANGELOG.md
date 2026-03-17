# Changelog

All notable changes to this project will be documented in this file.

## [0.15.5.0] - 2026-03-17

### Added
- `PUT /sessions/climbing/{id}` endpoint for editing climbing sessions (crag change with cascade, notes)
- `PUT /ascents/{id}` expanded with `route_id` and `grade` fields, with route name denormalization
- `SessionEditModal` component with searchable crag combobox and crag change confirmation dialog
- `AscentEditModal` component for editing grade, tick type, tries, rating, notes, and partner
- `CragCombobox` reusable searchable dropdown component
- Edit buttons (pencil icon) on session cards and ascent rows in the activity log
- `updateSession()` and `updateAscent()` API client functions

### Changed
- Consolidated session serialization into single `serialize_session()` in climbing service (was duplicated in router and service)
- `update_ascent()` now uses `exclude_unset=True` to support clearing fields (setting to null)
- Session crag updates cascade to all ascents via bulk SQL update (single query, not N+1)
- `IntegrityError` on session crag update returns 409 with clear message

## [0.15.4.0] - 2026-03-17

### Added
- PNG icon system replacing all emoji icons across the app
- `ActivityIcon` component with category-based PNG mapping (climber, runner, cycling, skiing, gym, default)
- `VenueIcon` component for crag/gym venue display (home.png, gym.png)
- 8 custom PNG icons in `public/icons/`

### Changed
- `SPORT_TYPES` icon field now stores PNG filenames instead of emoji strings
- All UI components (dashboard, log, calendar, crags) use `ActivityIcon` instead of emoji rendering
- Session streak indicator uses styled dot instead of fire emoji

### Removed
- `sportIcon()` helper function (replaced by `ActivityIcon` component)
- `CLIMBING_STYLE_ICONS` constant (unused after icon migration)

## [0.15.3.0] - 2026-03-17

### Added
- Crag browser page (`/crags`) with search, sort (last visited/name/session count), venue badges, and relative dates
- Crag detail page (`/crags/[id]`) with quick-stats header (sessions, routes logged, best send, last visited) and paginated session history
- Backend endpoints: `GET /crags/{id}`, `GET /crags/{id}/stats`, `GET /crags/{id}/sessions`
- Enhanced `GET /crags` with search, sort, and inline stats (session count, last visited)
- Crag name links on session cards in log page and dashboard recent activity
- Nav link to crag browser

### Fixed
- PostgreSQL COALESCE type mismatch with asyncpg (date vs varchar)

## [0.15.2.0] - 2026-03-17

### Added
- ClimbingSession model grouping ascents by (date, crag) with unique constraint
- Alembic migrations for `climbing_session` table and backfill from existing ascents
- Session CRUD API: `GET /sessions/climbing`, `GET /sessions/climbing/{id}`
- Unified activity feed endpoint (`GET /stats/feed`) merging sessions and endurance activities
- Data health endpoint (`GET /stats/health`) for migration verification
- `get_sessions` copilot tool for session-grouped queries
- Auto-link RockClimbing endurance activities to climbing sessions on sync
- Race condition guard (IntegrityError catch) on session creation
- Name propagation helper for crag renames
- Strava-aligned sport type taxonomy with icons, categories, and chart colors
- Frontend feed-based log page replacing separate ascent/activity queries

### Changed
- Weekly activity chart uses Strava sport categories instead of ad-hoc type mapping
- All activity icons across dashboard, log, and calendar pages use new taxonomy
- LLM system prompt updated with session-aware tool guidance
- Configurable LLM provider documented (Gemini default, Kimi K2.5 alternative)

### Removed
- `ACTIVITY_ICONS` and `ACTIVITY_TYPE_COLORS` constants (replaced by `SPORT_TYPES` and `CATEGORY_COLORS`)
- `activityIcon()` and `mapEnduranceType()` helpers (replaced by `sportIcon()` and `sportCategory()`)

## [0.15.0.0] - 2026-03-16

### Added
- Weekly activity chart on dashboard with stacked bar chart (climbing, cycling, hiking, fitness)
- Week navigator with prev/next controls
- Day accordion with detailed ascent and endurance activity breakdowns
- Session streak counter showing climbing sessions this month
- `/stats/weekly` API endpoint with ascent and endurance data per day
- Database index on `ascent.date` for faster weekly queries
- `recharts` charting library for frontend visualizations
- `dev-reset.sh` script for resetting local development environment

### Changed
- Updated feature index: PROJ-13 (Weekly activity chart) marked as done
- Removed completed "Session Streak Counter" from TODOS.md
- Updated plan 0002 progress notes
- Updated README with current project status
