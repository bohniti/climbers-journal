# Changelog

All notable changes to this project will be documented in this file.

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
