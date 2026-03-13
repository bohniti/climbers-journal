# 0000 — Climbers Journal: MVP

## Vision

A local-first training journal with an LLM assistant that can talk to your intervals.icu data. Ask it about your latest activity, training load, or trends — it fetches the data from intervals.icu and responds intelligently.

---

## Scope (MVP only)

1. **Backend** — FastAPI, serves the LLM chat endpoint and proxies intervals.icu API calls as LLM tools
2. **Frontend** — Next.js 15 chat UI to talk to the LLM
3. **LLM tools** — intervals.icu tools registered via a generic tool registry, starting with `get_latest_activity`, `get_activities`, `get_wellness`
4. **Dev container** — reproducible local dev environment
5. Run fully locally, no Docker Compose orchestration yet

Out of scope: auth, database, deployment, GPS maps, climbing-specific data model.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.12+, managed with `uv` |
| Frontend | Next.js 15 App Router, TypeScript, Tailwind CSS, managed with `pnpm` |
| LLM | Kimi K2.5 via Nvidia NIM (OpenAI-compatible, `openai` Python SDK) |
| Dev environment | Dev Container (Python + Node) |

---

## Monorepo Structure

```
climbers-journal/
├── .devcontainer/
│   └── devcontainer.json
├── app/
│   ├── backend/
│   │   ├── climbers_journal/     # Python package
│   │   │   ├── __init__.py
│   │   │   ├── main.py           # FastAPI app + CORS
│   │   │   ├── routers/
│   │   │   │   └── chat.py       # POST /chat
│   │   │   ├── services/
│   │   │   │   ├── llm.py        # LLM client + generic tool loop
│   │   │   │   └── intervals.py  # intervals.icu API client
│   │   │   └── tools/
│   │   │       ├── registry.py   # Tool registry (discover + dispatch)
│   │   │       └── intervals.py  # intervals.icu tool definitions + handlers
│   │   ├── tests/
│   │   │   └── __init__.py
│   │   └── pyproject.toml
│   └── frontend/
│       ├── src/
│       │   ├── app/
│       │   │   ├── layout.tsx
│       │   │   └── page.tsx      # Chat UI
│       │   └── lib/
│       │       └── api.ts        # Typed backend client
│       ├── package.json
│       └── tsconfig.json
├── .env.example
└── plans/
```

---

## Key Design Decisions

### Tool Registry Pattern

Tools are registered via a central registry, not hardcoded in the LLM service. Each tool module exports:
- `definitions` — list of OpenAI-format tool schemas
- `handle(tool_name, arguments)` — executes the tool and returns a result string

The LLM service collects all definitions at startup and dispatches tool calls by name. Adding a new tool source = add a new module in `tools/`, register it — zero changes to LLM service.

### Chat API with Conversation Context

```
POST /chat
{
  "conversation_id": "uuid-or-null",   // null = new conversation
  "message": "What was my last run?"
}
→ {
  "conversation_id": "abc-123",
  "reply": "Your last activity was..."
}
```

Conversations stored in-memory (dict of message lists) for now. When we add a database, we persist instead — API contract stays the same.

### Non-streaming first, SSE-ready

MVP returns a complete JSON response. The endpoint path and frontend are designed so we can add `POST /chat/stream` (SSE) alongside without breaking the existing contract.

### intervals.icu Integration

Authenticated via HTTP Basic Auth: `API_KEY` as username, the key as password.

| Tool name | Description | intervals.icu endpoint |
|---|---|---|
| `get_latest_activity` | Most recent activity with details | `GET /api/v1/athlete/{id}/activities?limit=1` |
| `get_activities` | Recent N activities (default 10) | `GET /api/v1/athlete/{id}/activities` |
| `get_wellness` | Wellness data (CTL, ATL, ramp rate) | `GET /api/v1/athlete/{id}/wellness` |

Tool call flow:
```
User message
  → Backend POST /chat
    → LLM (with all registered tool definitions)
      → LLM emits tool_call(s)
        → Registry dispatches to correct handler
          → Handler calls intervals.icu API
            → Result injected as tool message
              → LLM generates final answer
                → JSON response to frontend
```

---

## Environment Variables

```env
# .env.example
NVIDIA_API_KEY=...            # Kimi K2.5 via Nvidia NIM
INTERVALS_API_KEY=...         # intervals.icu API key
INTERVALS_ATHLETE_ID=...      # intervals.icu athlete ID (e.g. i12345)
CORS_ORIGINS=["http://localhost:3000"]
```

---

## Todo

### Step 1 — Dev container + repo scaffold
- [x] Create `.devcontainer/devcontainer.json` — Python 3.12, Node 22, uv, pnpm
- [x] Create `app/backend/pyproject.toml` — fastapi, uvicorn, httpx, openai, python-dotenv
- [x] Create `app/backend/climbers_journal/__init__.py`
- [x] Create `app/backend/climbers_journal/main.py` — minimal FastAPI app with CORS + health endpoint
- [x] Create `app/backend/tests/__init__.py`
- [x] Scaffold `app/frontend/` — `pnpm create next-app` with TypeScript + Tailwind + App Router
- [x] Add `.env.example`
- [x] Commit: `feat(PROJ-1): scaffold monorepo with backend, frontend, and devcontainer`

### Step 2 — intervals.icu client + tool registry
- [ ] Implement `app/backend/climbers_journal/services/intervals.py` — async httpx client with Basic Auth, methods: `get_activities(limit)`, `get_latest_activity()`, `get_wellness(oldest, newest)`
- [ ] Implement `app/backend/climbers_journal/tools/registry.py` — collects tool definitions, dispatches by name
- [ ] Implement `app/backend/climbers_journal/tools/intervals.py` — tool schemas + handler functions
- [ ] Commit: `feat(PROJ-1): intervals.icu client and tool registry`

### Step 3 — LLM chat endpoint
- [ ] Implement `app/backend/climbers_journal/services/llm.py` — Kimi K2.5 via openai SDK, tool call loop (call → tool_call → dispatch → re-submit → repeat until text)
- [ ] Implement `app/backend/climbers_journal/routers/chat.py` — `POST /chat` with `conversation_id` + in-memory conversation store
- [ ] Wire router in `main.py`
- [ ] Commit: `feat(PROJ-1): LLM chat endpoint with tool use loop`

### Step 4 — Frontend chat UI
- [ ] Build `app/frontend/src/app/page.tsx` — chat interface (message list + input, auto-scroll, loading state)
- [ ] Build `app/frontend/src/lib/api.ts` — typed `POST /chat` client
- [ ] Commit: `feat(PROJ-1): chat UI connected to backend`

### Step 5 — Smoke test + polish
- [ ] Verify end-to-end: "What was my last activity?" returns intervals.icu data
- [ ] Add run instructions to root `README.md`
- [ ] Commit: `docs(PROJ-1): add run instructions and verify e2e`
