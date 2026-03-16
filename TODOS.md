# TODOS

Deferred work from plan reviews. Each item has context so it can be picked up independently.

---

## P2 — Should Do

### Make session_id NOT NULL
**What:** Follow-up migration to add NOT NULL constraint on `ascent.session_id` after verifying all ascents have been backfilled.
**Why:** Nullable FK is a migration compromise. Once verified, making it NOT NULL prevents orphan ascents from being created.
**Effort:** S
**Depends on:** Plan 0003 fully implemented + migration verified via `/stats/health` showing 0 orphans
**Context:** From eng review of plan 0003. The backfill migration groups existing ascents by (date, crag_id). After running and verifying, a follow-up Alembic migration adds the NOT NULL constraint.

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

## P3 — Nice to Have

### Photo Attachments on Ascents
**What:** Attach beta photos or summit pics to ascent records.
**Why:** Visual memory of climbs. Common feature in Mountain Project / The Crag.
**Effort:** M
**Depends on:** Ascent model (PROJ-3)
**Context:** Store on local disk (`media/` folder). Migrate to object storage only if scaling to multi-user or CDN is needed. Hostinger VPS has sufficient disk for single-user.
