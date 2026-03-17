# TODOS

Deferred work from plan reviews. Each item has context so it can be picked up independently.

---

## P2 — Should Do

### Docker Compose + CI/CD + Deployment
**What:** Dockerfiles for backend + frontend, docker-compose.yml (dev + prod), GitHub Actions pipeline, Hostinger VPS deployment.
**Why:** No deployment infrastructure exists yet. Currently running locally only.
**Effort:** M
**Depends on:** Core features stable enough to deploy (after PROJ-3 or PROJ-5)
**Context:** From eng review. Hostinger VPS is available but unconfigured. Previous project iteration had Docker + GH Actions but was scrapped for greenfield restart. Step 1 uses local PostgreSQL (`brew install`) — Docker Compose replaces this for prod.

### CSV Export
**What:** "Download my data" button exporting ascents + endurance activities as CSV.
**Why:** Builds user trust (data portability), useful for blog posts and analysis.
**Effort:** S
**Depends on:** DB layer (PROJ-2) + climbing model (PROJ-3)
**Context:** User has previously created blog articles from climbing CSV data. Export closes the loop — import CSV in, do stuff, export CSV out.

### Training Insights Endpoint
**What:** `GET /stats/insights` — compute period-over-period deltas, return 2-3 text insights for dashboard (e.g., "Your climbing volume is up 30% vs last month").
**Why:** Transforms dashboard from passive stats display to active training coach. High impact for low effort.
**Effort:** S-M
**Depends on:** Activity stats + climbing progress endpoints from plan 0004
**Context:** From CEO review of plan 0004. Builds on the stats endpoints being created. Natural follow-up once dashboard data is flowing.

### Period Comparison Toggle
**What:** "vs last month" toggle on weekly activity chart — overlays previous period's data as faded ghost bars behind current data.
**Why:** Lets users instantly see if they're training more or less than before.
**Effort:** S (frontend only, fetch two periods, overlay in Recharts)
**Depends on:** Weekly chart filter buttons from plan 0004 Step 3
**Context:** From CEO review of plan 0004. Deferred to avoid over-complicating the chart in v1.

## P3 — Nice to Have

### Training Consistency Heatmap
**What:** GitHub-style contribution graph on dashboard — 90-day grid, one cell per day, colored by activity type.
**Why:** Instant visual motivation — users can see training streaks and gaps at a glance.
**Effort:** S (frontend only, uses existing activity data from quarterly endpoint)
**Depends on:** Dashboard component extraction from plan 0004
**Context:** From CEO review of plan 0004. Pure delight feature, no backend work needed.

### Micro-Animations on Dashboard
**What:** Chart bars animate on load (Recharts `isAnimationActive`), stats numbers count up, smooth fade transitions between dashboard sections.
**Why:** Makes the dashboard feel premium and polished. Zero new dependencies — Recharts + Tailwind `animate-` classes.
**Effort:** S (~20 min)
**Depends on:** Dashboard overhaul from plan 0004
**Context:** From CEO review of plan 0004. Pure polish, best done after dashboard is feature-complete.
