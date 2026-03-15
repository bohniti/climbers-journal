# Climbers Journal

A local-first training journal with an LLM assistant that connects to your [intervals.icu](https://intervals.icu) data. Query your training conversationally — the LLM fetches the data and responds.

## Prerequisites

- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- Node.js 22+ with [pnpm](https://pnpm.io/)
- An [intervals.icu](https://intervals.icu) account with an API key
- At least one LLM provider API key (Nvidia NIM for Kimi K2.5, or Google AI for Gemini)

## Setup

```bash
# Clone and configure
cp .env.example .env
# Edit .env with your API keys

# Install backend dependencies
cd app/backend
uv sync

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

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `NVIDIA_API_KEY` | One of these | Kimi K2.5 via Nvidia NIM |
| `GOOGLE_API_KEY` | One of these | Gemini via Google AI |
| `DEFAULT_LLM_PROVIDER` | No | `kimi` or `gemini` (default: `kimi`) |
| `INTERVALS_API_KEY` | Yes | intervals.icu API key |
| `INTERVALS_ATHLETE_ID` | Yes | intervals.icu athlete ID (e.g. `i12345`) |
| `CORS_ORIGINS` | No | JSON array (default: `["http://localhost:3000"]`) |
