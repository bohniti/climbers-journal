# Changelog

All notable changes to this project will be documented in this file.

## [0.15.1.0] - 2026-03-16

### Added
- Strava-aligned sport type taxonomy (`SPORT_TYPES`) covering all ~50 Strava SportTypes with icons, labels, and categories
- Climbing sub-type icons (`CLIMBING_STYLE_ICONS`) for sport, boulder, multi-pitch, trad, alpine
- `CATEGORY_COLORS` for 8 sport categories (run, ride, swim, winter, climbing, water, fitness, other) replacing old ad-hoc color map
- Helper functions: `getSportType()`, `sportIcon()`, `sportCategory()` with console.warn fallback for unknown types
- Activities overhaul plan (0003) for session grouping, unified feed, and crag browser

### Changed
- Weekly activity chart now uses Strava sport categories instead of ad-hoc type mapping
- All activity icons across dashboard, log, and calendar pages use new taxonomy
- Replaced `mapEnduranceType()` with proper `sportCategory()` lookup
- Chart legend and tooltip display category labels from `CATEGORY_COLORS`

### Removed
- `ACTIVITY_ICONS` constant (replaced by `SPORT_TYPES`)
- `activityIcon()` helper (replaced by `sportIcon()`)
- `mapEnduranceType()` helper in WeeklyActivity (replaced by `sportCategory()`)

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
