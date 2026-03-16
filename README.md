# Climbers Journal

A local-first training journal with an LLM assistant that connects to your [intervals.icu](https://intervals.icu) data. Query your training conversationally — the LLM fetches the data and responds.

## Prerequisites

- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- Node.js 22+ with [pnpm](https://pnpm.io/)
- PostgreSQL 16+ (`brew install postgresql@16`)
- An [intervals.icu](https://intervals.icu) account with an API key
- At least one LLM provider API key (Google AI for Gemini recommended, or Nvidia NIM for Kimi K2.5)

## Setup

```bash
# Start PostgreSQL and create the database (one-time)
brew services start postgresql@16
createdb climbers_journal

# Install backend dependencies and run migrations
cd app/backend
uv sync
uv run alembic upgrade head

# Copy config templates and fill in your values
cp config.yaml.example config.yaml  # non-secret app config (LLM provider, intervals.icu settings)
cp ../../.env.example ../../.env     # secrets only (API keys, DB URL)

# Install frontend dependencies
cd ../frontend
pnpm install
```

## Running

Start both services in separate terminals:

```bash
# Terminal 1 — Backend (port 8000)
cd app/backend
uv run fastapi dev climbers_journal/main.py

# Terminal 2 — Frontend (port 3000)
cd app/frontend
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) and start chatting.

## Dev Reset

To stop all processes, wipe the database, and re-run migrations:

```bash
./scripts/dev-reset.sh
```

## Claude Code (gstack)

This project includes [gstack](https://github.com/garrytan/gstack) skills for Claude Code. After cloning, run the one-time setup:

```bash
cd .claude/skills/gstack && ./setup
```

Requires [bun](https://bun.sh/). This gives you these slash commands in Claude Code:

| Command | Description |
|---|---|
| `/browse` | Headless browser for QA testing and dogfooding |
| `/qa` | Systematic QA testing with structured reports |
| `/review` | Pre-landing PR review (diff analysis) |
| `/ship` | Ship workflow (tests, review, version bump, PR) |
| `/plan-eng-review` | Engineering plan review |
| `/plan-ceo-review` | CEO/founder-mode plan review |
| `/setup-browser-cookies` | Import browser cookies for authenticated testing |
| `/retro` | Weekly engineering retrospective |

## Configuration

Non-secret config lives in `app/backend/config.yaml` (LLM provider, model, intervals.icu base URL, CORS origins). See `config.yaml.example` for the full schema. If missing, sensible defaults are used.

Secrets live in `.env` at the project root:

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | No | PostgreSQL connection (default: `postgresql+asyncpg://localhost:5432/climbers_journal`) |
| `GOOGLE_API_KEY` | One of these | Gemini via Google AI (default provider) |
| `NVIDIA_API_KEY` | One of these | Kimi K2.5 via Nvidia NIM |
| `INTERVALS_API_KEY` | Yes | intervals.icu API key |
| `INTERVALS_ATHLETE_ID` | Yes | intervals.icu athlete ID (e.g. `i12345`) |
