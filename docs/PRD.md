# Climbers Journal — Product Requirements

## Problem

Athletes who climb use generic training platforms (Strava, Garmin, intervals.icu) that don't understand climbing-specific training. Logging climbing sessions, tracking projects, and understanding how climbing fits into overall training load requires manual effort across multiple tools.

## Solution

A local-first training journal with an LLM assistant that connects to your existing training data (intervals.icu) and lets you query it conversationally. Log climbing sessions, import history, sync endurance activities, and ask the copilot about your training — it fetches the data and responds.

## Current Capabilities

- **Chat copilot** — conversational LLM assistant with tool use (record sessions, query data)
- **Climbing CRUD** — log sessions with routes, grades, tick types; grade auto-suggest
- **Endurance sync** — import activities from intervals.icu with retry
- **CSV import** — bulk import climbing history from CSV files
- **Dashboard** — stats cards, grade pyramid, weekly activity chart with day accordion
- **Training calendar** — month/week views of all activities
- **Activity log** — filterable, paginated view of all sessions
- **Data import page** — guided import for climbing CSV + intervals.icu sync
- **Onboarding tour** — first-run tooltip walkthrough of core features
- **Configurable LLM** — YAML config file supporting multiple providers (Gemini default, Kimi K2.5)
- **PostgreSQL persistence** — SQLModel + Alembic migrations

## Tech Stack

- **Backend:** FastAPI, Python 3.12+, PostgreSQL, SQLModel, Alembic
- **Frontend:** Next.js 15 App Router, TypeScript, Tailwind CSS, Recharts
- **LLM:** Configurable via `config.yaml` — Gemini 2.5 Flash Lite (default), Kimi K2.5 via Nvidia NIM
- **Integrations:** intervals.icu REST API

## Future Direction

- Training load analytics (CTL/ATL/TSB) with climbing-aware metrics
- User auth and multi-user support
- Deployment (Docker, CI/CD)
- Garmin/GPX import, interactive crag maps
