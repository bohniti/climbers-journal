# 0002 — Polish & Onboarding: Config, Design, Data, Dashboard, First-Run

## Context

Plan 0001 delivered the full core product (PROJ-1 through PROJ-10). All features are done. Now we address five issues discovered during use: hardcoded model config, outdated frontend design, empty database on first launch, missing weekly activity chart, and no guidance for new users.

### What changed since 0001

- All 10 steps complete — DB, climbing CRUD, sync, CSV import, copilot, log view, forms, dashboard, calendar
- LLM provider changed: Nvidia NIM (Kimi K2.5) → **Google AI (Gemini 2.5 Flash Lite)**
- Rate limits: 10 RPM, 250K tokens/minute — low but sufficient for single-user
- Old repo (`climbers-journal-copy`) has a dark slate + emerald design and weekly activity chart we want to adopt
- Blog repo (`bohniti.github.io`) has 3 CSV files with real climbing data ready to import

---

## Review Decisions (from CEO review, 2026-03-16)

| # | Decision | Choice |
|---|----------|--------|
| 1 | Review mode | HOLD SCOPE |
| 2 | Dark mode strategy | Dark-only (strip all `dark:` variants, single dark slate+emerald theme) |
| 3 | Config loader | pydantic-settings with YAML support (`pydantic-settings[yaml]`) |
| 4 | Rate limit handling | Retry with backoff: catch `RateLimitError`, sleep 6s, retry up to 2x |
| 5 | Config file safety | `.gitignore` + `config.yaml.example` (same pattern as `.env`) |
| 6 | Config status endpoint | Add `GET /config/status` returning `{intervals_configured: bool, llm_configured: bool}` |
| 7 | Naming: data import page | Route is `/import` (not `/onboarding`) — "onboarding" reserved for tutorial |
| 8 | Test coverage | Add ~8 backend unit tests (config 4, rate limit 1, weekly 2, config status 1) |
| 9 | Session streak counter | Bump existing TODO from P3 to P2 (natural fit during PROJ-13) |
| 10 | Tour step anchoring | Build `data-tour-step` attributes into Issue #2 (not deferred) |

## Review Decisions (from eng review, 2026-03-16)

| # | Decision | Choice |
|---|----------|--------|
| 1 | Route prefix for weekly endpoint | `GET /stats/weekly` in existing `stats.py` (consistent with `/stats/dashboard`, `/stats/calendar`) |
| 2 | Rate limit retry scope | `_call_with_retry()` async helper in `llm.py` wrapping only `client.chat.completions.create()` — not the full tool loop |
| 3 | Config access pattern | `@lru_cache` on `get_settings()` — standard pydantic-settings pattern, testable via `cache_clear()` |
| 4 | `/config/status` placement | Inline in `main.py` next to `/health` (system status endpoint, not a new router) |
| 5 | Client cache invalidation | `_get_client()` reads from `get_settings()`, keeps cache; add `clear_clients()` helper for tests |
| 6 | DRY color constants | Migrate existing `TICK_COLORS`, `PYRAMID_COLORS`, `ACTIVITY_ICONS` from `page.tsx` into `constants.ts` |
| 7 | Missing config.yaml behavior | Fall back to sensible defaults (current hardcoded values), log warning — app works on first clone without setup |
| 8 | Tour step attributes | Explicit attribute name table in Issue #2 — single reference for producer and consumer |
| 9 | Test count | Expand to ~11 backend tests (add: retry exhaustion, weekly climbing-only day, config/status both missing) |
| 10 | Ascent date index | Add `ix_ascent_date` via Alembic migration in PROJ-13 (prerequisite for weekly endpoint) |
| 11 | Session streak counter | Absorb into PROJ-13 as subtask — remove from TODOS.md |

### Implementation notes from eng review

**Critical implementation detail:** `/config/status` must check for **non-empty** env vars, not just presence. Use `os.getenv("KEY", "") != ""` — an empty string should report `configured: false`.

```
Config data flow:

  config.yaml ──→ pydantic-settings ──→ get_settings() [@lru_cache]
       │                                      │
       │         .env (secrets)               ├──→ llm.py (_get_client via config)
       │              │                       ├──→ intervals.py (base_url from config)
       │              ▼                       ├──→ main.py (CORS from config)
       └──→ AppSettings ◄── os.getenv()      └──→ main.py /config/status

Rate limit retry (wraps only the API call, not the tool loop):

  chat() tool loop:
    for _ in range(MAX_TOOL_ROUNDS):
      response = await _call_with_retry(client, model, messages, tools)
      ─── _call_with_retry ───
      │ try: create()          │
      │ except RateLimitError: │
      │   sleep 6s, retry ×2  │
      ──────────────────────────
      ...process tool calls...
```

---

## Bugfix: Copilot route creation fails with null grade
**Hotfix — inserted before PROJ-12**

**Problem:** When the copilot creates a climbing session and the LLM omits or sends `null` for the route grade, the backend crashes with `NotNullViolationError` on `route.grade`. Root cause: `item.get("grade", "?")` returns `None` when the key exists with a `None` value — the default `"?"` only applies when the key is missing entirely.

**Fix:** Changed `item.get("grade", "?")` → `item.get("grade") or "?"` in `services/climbing.py:402`. This ensures `None` and empty string both fall back to `"?"`.

- [x] Fix `create_climbing_session` in `services/climbing.py` — use `or` fallback for grade

---

## Issue #1: App Config File
**Feature:** PROJ-11

**Problem:** Model endpoints, defaults, and non-secret config are either hardcoded in `llm.py` or mixed into `.env` alongside secrets. Can't change the model without editing source code.

**Solution:** Introduce a `config.yaml` loaded via `pydantic-settings[yaml]` at startup. `.env` keeps only secrets (API keys, DB URL). Config file holds everything else.

### Current state
- `.env`: `NVIDIA_API_KEY`, `GOOGLE_API_KEY`, `DEFAULT_LLM_PROVIDER=kimi`, `INTERVALS_API_KEY`, `INTERVALS_ATHLETE_ID`, `DATABASE_URL`, `CORS_ORIGINS`
- `llm.py`: `PROVIDERS` dict hardcoded with model names, base URLs, `MAX_TOOL_ROUNDS=10`

### Target state
```yaml
# config.yaml
llm:
  default_provider: gemini
  providers:
    gemini:
      model: gemini-2.5-flash-lite
      base_url: https://generativelanguage.googleapis.com/v1beta/openai/
      api_key_env: GOOGLE_API_KEY   # points to .env var name
      rpm_limit: 10
      tpm_limit: 250000
    kimi:
      model: moonshotai/kimi-k2.5
      base_url: https://integrate.api.nvidia.com/v1
      api_key_env: NVIDIA_API_KEY

intervals:
  base_url: https://intervals.icu/api/v1
  api_key_env: INTERVALS_API_KEY
  athlete_id_env: INTERVALS_ATHLETE_ID

cors:
  origins:
    - http://localhost:3000
```

```env
# .env — secrets only
GOOGLE_API_KEY=...
NVIDIA_API_KEY=...
INTERVALS_API_KEY=...
INTERVALS_ATHLETE_ID=...
DATABASE_URL=postgresql+asyncpg://localhost:5432/climbers_journal
```

### Tasks
- [x] Add `pydantic-settings[yaml]` to `pyproject.toml`
- [x] Create `app/backend/climbers_journal/config.py` — pydantic-settings model with `get_settings()` cached via `@lru_cache`. If `config.yaml` is missing, fall back to sensible defaults (current hardcoded values) and log warning. Malformed YAML or missing required fields still fail fast.
- [x] Create `config.yaml` with Gemini 2.5 Flash Lite as default provider
- [x] Create `config.yaml.example` (tracked in git)
- [x] Add `config.yaml` to `.gitignore`
- [x] Refactor `llm.py` to read provider config from `get_settings()` instead of hardcoded `PROVIDERS` dict. Add `clear_clients()` helper to reset cached `AsyncOpenAI` instances (for tests).
- [x] Add `_call_with_retry()` async helper in `llm.py` — wraps only `client.chat.completions.create()` (not the tool loop). Catches `openai.RateLimitError`, sleeps 6s, retries up to 2x, then re-raises.
- [x] Refactor `intervals.py` service to read base URL / env var names from `get_settings()`
- [x] Strip non-secret values from `.env` (keep only API keys + DB URL)
- [x] Update `.env.example` to reflect secrets-only approach
- [x] Add `GET /config/status` in `main.py` (next to `/health`) — returns `{intervals_configured: bool, llm_configured: bool}`. Check for **non-empty** env vars (`os.getenv("KEY", "") != ""`), not just presence.
- [x] Log config file path and selected provider at startup
- [x] Log rate limit retries with backoff duration
- [x] Tests (6 total): config loading happy path, missing file (defaults fallback), malformed YAML, missing required field, rate limit retry success on 2nd attempt, rate limit retry exhaustion (all retries fail → raises)

---

## Issue #2: Frontend Design Refresh
**Feature:** PROJ-12

**Problem:** The current frontend doesn't match the dark slate + emerald design from the earlier version that the user preferred.

**Solution:** Switch to dark-only theme. Strip all `dark:` variants, replace zinc palette with slate+emerald. No architecture changes — only visual styling.

### Design tokens (dark-only, no light mode)

**Color palette:**
- Background: `--background: #0a0f1e` / `bg-slate-950`
- Foreground: `--foreground: #e8eaf6` / `text-slate-100`
- Cards: `bg-slate-900`, `border border-slate-700`
- Text secondary: `text-slate-400`
- Accent/CTA: `emerald-600` / `emerald-700`
- Focus ring: `ring-emerald-600`
- Inputs: `bg-slate-800 border-slate-700`
- Error: `border-red-800 bg-red-950/40 text-red-400`
- Warning: `border-yellow-700 bg-yellow-950/30 text-yellow-400`
- Success: `border-emerald-700 bg-emerald-950/40 text-emerald-300`

**Activity type colors (single source of truth in `constants.ts`):**
| Type | Hex (charts) | Badge (UI) |
|------|-------------|------------|
| bouldering | `#9333ea` | `bg-purple-100 text-purple-800` |
| sport_climb | `#3b82f6` | `bg-blue-100 text-blue-800` |
| multi_pitch | `#f59e0b` | `bg-amber-100 text-amber-800` |
| cycling | `#22c55e` | `bg-green-100 text-green-800` |
| hiking | `#14b8a6` | `bg-teal-100 text-teal-800` |
| fitness | `#f97316` | `bg-orange-100 text-orange-800` |
| other | `#9ca3af` | `bg-gray-100 text-gray-700` |

**Icons:** Unicode/emoji only (no icon library) — `⛰` mountain, `📋` activities, `🔄` sync, `★` rating, `✓`/`✕` confirm/cancel, `▼`/`▲` expand/collapse

**Component patterns:**
- Buttons: primary `bg-emerald-700 hover:bg-emerald-600`, secondary `bg-slate-700 hover:bg-slate-600`
- Inputs: `bg-slate-800 border-slate-700 focus:ring-2 focus:ring-emerald-600 text-slate-100 placeholder-slate-500`
- Chat: user `bg-emerald-700 rounded-2xl rounded-br-sm`, assistant `bg-slate-800 rounded-2xl rounded-bl-sm`

### `data-tour-step` attribute reference

These exact values are consumed by the `OnboardingTour` component in Issue #5. Add them during the design sweep.

| Attribute value | Target element | Location |
|---|---|---|
| `import` | "Import Data" nav link or button | Nav.tsx |
| `log-session` | "+ Log session" button | page.tsx (dashboard) |
| `copilot` | "Ask Copilot" button or nav link | page.tsx (dashboard) or Nav.tsx |
| `dashboard` | Stats cards / weekly chart section | page.tsx (dashboard) |
| `calendar` | Calendar nav link | Nav.tsx |

### Tasks
- [x] Create `src/lib/constants.ts` — single source of truth for activity type hex colors, badge classes, tick type colors
- [x] Migrate existing `TICK_COLORS`, `PYRAMID_COLORS`, `ACTIVITY_ICONS` from `page.tsx` into `constants.ts` and import from there (DRY)
- [x] Update `globals.css` — set `--background: #0a0f1e`, `--foreground: #e8eaf6`, remove `prefers-color-scheme` media query
- [x] Update `layout.tsx` — `bg-slate-950 text-slate-100`, remove `dark:` variants, nav bar: emerald-400 logo, slate-400 links
- [x] Sweep all pages (`/`, `/log`, `/log/add`, `/chat`, `/calendar`) — strip all `dark:` variants, replace zinc classes with slate/emerald
- [x] Update card components — `bg-slate-900 border-slate-700 rounded-xl`
- [x] Update button styles — emerald primary, slate secondary
- [x] Update input/form styles — slate-800 bg, emerald focus ring
- [x] Update chat bubbles — emerald user messages, slate assistant messages
- [x] Add `data-tour-step` attributes per the table above
- [ ] Verify dark-on-dark readability across all pages

---

## Issue #3: Data Import Page
**Feature:** PROJ-14

**Problem:** New installs start with an empty database. The user has real climbing data in CSV files and endurance data in intervals.icu, but there's no guided way to import them.

**Solution:** Build a data import page at `/import` — accessible anytime via nav/button, imports climbing CSV + triggers intervals.icu sync. Purely frontend — wires up existing backend endpoints.

### Available data sources

**Climbing CSV** (user uploads their own file):
- Expected schema: `date, tick_type, crag_name, route_name, grade, area_name, tries, rating, notes, partner, style`
- Calls existing `POST /import/climbing-csv` (from PROJ-5)

**Endurance activities:**
- Calls existing `POST /sync/intervals` (from PROJ-4)
- Date range required

### Prerequisites (done in PROJ-12)
- [x] Add "Import Data" link to nav bar (`Nav.tsx` — route `/import`, `data-tour-step="import"`)
- [x] `GET /config/status` endpoint exists (PROJ-11) — returns `{intervals_configured, llm_configured}`

### Tasks
- [x] Create `/import` page (`app/frontend/src/app/import/page.tsx`) with two import cards:
  1. **Climbing History** — file upload (CSV), calls existing `POST /import/climbing-csv`
  2. **Endurance Activities** — date range picker + "Sync from intervals.icu" button, calls existing `POST /sync/intervals`
- [x] On mount, call `GET /config/status` — if `intervals_configured: false`, gray out the sync card with "intervals.icu not configured" message
- [x] Disable buttons during upload/sync (prevent double-click), show spinner
- [x] Show import results inline: rows imported, skipped, errors (climbing); activities synced (endurance)
- [x] Style with slate/emerald theme (consistent with PROJ-12 design tokens)
- [x] Backend: no new endpoints needed — existing endpoints handle both imports

---

## Issue #4: Weekly Activity Chart on Dashboard
**Feature:** PROJ-13

**Problem:** The dashboard (`/`) shows stats cards and grade pyramid but lacks a unified view of "how active was I this past week."

**Solution:** Port the weekly activity stacked bar chart from `climbers-journal-copy` into the current dashboard.

### Chart spec

- **Library:** Recharts
- **Type:** Stacked bar chart — one bar per day (Mon–Sun), stacked by activity type
- **Y-axis:** Activity count
- **Colors:** Activity type hex colors from `constants.ts`
- **Tooltip:** `bg-slate-800 border-slate-700 rounded-lg`
- **Height:** 220px responsive container
- **Week navigation:** Prev/Next buttons with date range label
- **Empty state:** Shows 7 empty bars with "No activity this week" message

### Day accordion
Below the chart, expandable day rows listing activities for that day with type badge, title, duration.

### Tasks
- [x] Alembic migration: add `ix_ascent_date` index on `ascent.date` (prerequisite for weekly endpoint; `EnduranceActivity` already has `ix_endurance_activity_date`)
- [x] Add `recharts` to frontend dependencies (`pnpm add recharts`)
- [x] Create `WeeklyActivityChart` component with stacked bars by activity type
- [x] Create `WeekNavigator` component (prev/next week, date range display)
- [x] Create `DayAccordion` component (expandable day rows with activity details)
- [x] Add `GET /stats/weekly` endpoint in `stats.py` — returns 7-day activity summary:
  - Input: `week_start` (ISO date, defaults to current week's Monday)
  - Output: `{ days: [{ date, climbing_count, endurance_activities: [{type, name, duration_s}], ascents: [{route_name, grade, tick_type}] }] }`
  - Queries both `ascent` and `endurance_activity` tables filtered by date range
- [x] Add session streak widget to dashboard: "You've logged N sessions this month" (COUNT ascents WHERE date >= month_start). Include in `/stats/weekly` response or existing `/stats/dashboard`.
- [x] Integrate chart + accordion + streak widget into dashboard page (`/`) above existing grade pyramid
- [x] Style chart with slate/emerald theme tokens
- [x] Tests (4 total): `/stats/weekly` with empty week, with mixed climbing+endurance data, with climbing-only day (no endurance), session streak count correctness

---

## Issue #5: User Onboarding Tutorial
**Feature:** PROJ-15

**Problem:** New users don't know what the product can do. There's no guidance after first launch.

**Solution:** A lightweight first-run tooltip tour on the dashboard that highlights core capabilities.

### Design

**Approach:** Step-through overlay/tooltip tour on first visit. Uses localStorage `onboarding_complete` flag. Targets elements via `data-tour-step` attributes (added in Issue #2).

**Steps:**
1. **Welcome** — "Climbers Journal is your unified training log for climbing + endurance."
2. **Import your data** — Points to `[data-tour-step="import"]`. "Start by importing your climbing history and syncing endurance activities."
3. **Log a session** — Points to `[data-tour-step="log-session"]`. "Log climbing sessions via the form or ask the copilot."
4. **Ask the copilot** — Points to `[data-tour-step="copilot"]`. "Ask about your training: 'What did I climb last week?' or 'Show my grade pyramid.'"
5. **Track your progress** — Points to `[data-tour-step="dashboard"]`. "See your training at a glance."

**Implementation:** Simple component with fixed positioning, backdrop, and a highlight box around the target element. No external tour library. Scroll to target if not visible.

### Tasks
- [ ] Create `OnboardingTour` component — step-through overlay with highlight + description
- [ ] Target elements via `data-tour-step` attributes (placed in Issue #2)
- [ ] Scroll to target element if not visible in viewport
- [ ] Track completion in localStorage (`onboarding_complete: true`)
- [ ] Show tour on first dashboard visit if not completed
- [ ] Add "Show tutorial" button in nav to replay tour (resets localStorage flag)
- [ ] Style overlay with slate/emerald theme (semi-transparent backdrop, emerald highlight border)

---

## Implementation Order

| Step | Issue | Feature ID | Dependencies |
|------|-------|-----------|--------------|
| 1 | #1 Config file | PROJ-11 | None — unblocks model switch |
| 2 | #2 Design refresh | PROJ-12 | None — pure CSS/classes |
| 3 | #4 Weekly chart | PROJ-13 | #2 (needs design tokens + constants.ts) |
| 4 | #3 Data import UI | PROJ-14 | #2 (needs design), #1 (config/status endpoint) |
| 5 | #5 Onboarding tour | PROJ-15 | #2 (data-tour-step attrs), #3, #4 (needs final UI) |

Steps 1 and 2 can be done in parallel. Steps 3 and 4 can also be parallelized after step 2.

---

## Out of Scope

- Light mode / theme toggle (dark-only confirmed)
- Rate limiting middleware / client-side rate limiter (retry-with-backoff sufficient)
- Mobile-specific layouts (responsive web is fine)
- Automated data sync scheduling (manual trigger is enough)
- External tour libraries (custom component is simpler)
- Docker/CI/CD (separate TODO)
- Frontend unit tests / Jest setup (no existing test infrastructure; 11 backend tests sufficient for this plan)
- New `/dashboard/` route prefix (weekly endpoint goes under existing `/stats/` for consistency)
