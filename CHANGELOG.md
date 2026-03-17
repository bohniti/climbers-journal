# Changelog

All notable changes to this project will be documented in this file.

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
