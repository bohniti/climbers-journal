# TODOS

Deferred work from plan reviews. Each item has context so it can be picked up independently.

---

## P2 — Should Do

### Name Propagation on Rename
**What:** When a crag or route is renamed (PUT /crags/{id}, PUT /routes/{id}), update all denormalized `crag_name`/`route_name` fields on related Ascent records.
**Why:** Decision 14B denormalized route/crag names onto Ascent for read performance. Without propagation, renames leave stale names on ascent records.
**Effort:** S
**Depends on:** Climbing model (PROJ-3) with denormalized names
**Context:** From eng review Issue 14. Not needed until a rename/edit UI exists, but the climbing service's update methods should propagate name changes. Simple `UPDATE ascent SET crag_name = X WHERE crag_id = Y`.

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

### Session Streak Counter
**What:** Dashboard widget showing "You've logged N sessions this month."
**Why:** Motivational nudge. Trivial query (COUNT ascents WHERE date >= month_start).
**Effort:** S
**Depends on:** Dashboard (PROJ-9)
**Context:** Quick polish item for post-launch.

### Photo Attachments on Ascents
**What:** Attach beta photos or summit pics to ascent records.
**Why:** Visual memory of climbs. Common feature in Mountain Project / The Crag.
**Effort:** M
**Depends on:** Ascent model (PROJ-3)
**Context:** Store on local disk (`media/` folder). Migrate to object storage only if scaling to multi-user or CDN is needed. Hostinger VPS has sufficient disk for single-user.
