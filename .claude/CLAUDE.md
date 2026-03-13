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

# Frontend
cd app/frontend && pnpm dev
```

## Product Context

@docs/PRD.md

## Feature Overview

@features/INDEX.md
