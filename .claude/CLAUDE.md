# Climbers Journal

> A local-first training journal with an LLM assistant that connects to your intervals.icu data. Query your training conversationally — the LLM fetches the data and responds.

## Tech Stack

- **Backend:** FastAPI, Python 3.12+, managed with `uv`
- **Frontend:** Next.js 15 App Router, TypeScript, Tailwind CSS, managed with `pnpm`
- **LLM:** Kimi K2.5 via Nvidia NIM (OpenAI-compatible, `openai` Python SDK)
- **Package Managers:** `uv` (Python), `pnpm` (Node)
- **Integrations:** intervals.icu REST API

## Project Structure

```
app/
  backend/          # FastAPI service
    climbers_journal/   # Python package
      main.py           # App + CORS
      routers/          # API endpoints
      services/         # Business logic
      tools/            # LLM tool registry + tool modules
    tests/
    pyproject.toml
  frontend/         # Next.js 15 app
    src/app/        # App Router pages
    src/lib/        # API client, types
plans/              # Solution plans (XXXX-name.md)
features/           # Feature specs + INDEX.md
docs/               # PRD and product docs
```

## Development Workflow

1. `/plan` - Create feature spec from idea
2. `/implement` - Implement next step from latest plan

## Feature Tracking

All features tracked in `features/INDEX.md`. Every skill reads it at start and updates it when done. Feature specs live in `features/PROJ-X-name.md`.

## Key Conventions

- **Feature IDs:** PROJ-1, PROJ-2, etc. (sequential)
- **Commits:** `feat(PROJ-X): description`, `fix(PROJ-X): description`
- **Single Responsibility:** One feature per spec file
- **Human-in-the-loop:** All workflows have user approval checkpoints

## Build, Test and Run Commands

```bash
# Backend
cd app/backend && uv run fastapi dev climbers_journal/main.py

# Backend tests
cd app/backend && uv run pytest

# Alembic migrations
cd app/backend && uv run alembic upgrade head

# Frontend
cd app/frontend && pnpm dev
```

## gstack

Use `/browse` from gstack for all web browsing. **Never use `mcp__claude-in-chrome__*` tools** — they are slow and unreliable.

Available gstack skills:
- `/browse` — Headless browser for QA testing and site dogfooding
- `/qa` — QA testing workflows
- `/review` — Pre-landing PR review (diff analysis against main)
- `/ship` — Ship workflow (tests, review, version bump, PR creation)
- `/plan-eng-review` — Engineering manager-mode plan review
- `/plan-ceo-review` — CEO/founder-mode plan review (10-star product thinking)
- `/setup-browser-cookies` — Import browser cookies for authenticated testing
- `/retro` — Retrospective

**Note:** gstack's `/review` and `/ship` skills are Rails-oriented by default. This project uses FastAPI + Next.js. Adapt test commands accordingly:
- Backend tests: `cd app/backend && uv run pytest`
- Frontend tests: `cd app/frontend && pnpm test` (if configured)

**Plans folder:** This project keeps plans in `plans/` as numbered files (`XXXX-name.md`). The project's `/plan` skill creates plans; gstack's `/plan-eng-review` and `/plan-ceo-review` review them. Both coexist — use `/plan` to create, then optionally `/plan-eng-review` or `/plan-ceo-review` to review.

## Product Context

@docs/PRD.md

## Feature Overview

@features/INDEX.md
