"""
Bulk imports:
  POST /import/intervals?days_back=365   — Garmin via intervals.icu
  POST /import/blog-csv                  — historical CSV from Vertical Life / Mountain Project
"""
import csv
import io
from collections import defaultdict
from datetime import datetime
from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.models.activity import Activity, ActivityType, ActivitySource, GradeSystem, ClimbStyle
from app.models.route import SessionRoute

router = APIRouter(tags=["import"])

# ─── Blog CSV: region mapping ──────────────────────────────────────────────────
# Maps crag/gym name (location column) → human-readable region for filtering

_LOCATION_REGION: dict[str, str] = {
    # ── Vienna gyms — all grouped under "Wien" ───────────────────────────────
    "Kletterhalle Wien":        "Wien",
    "Kletteranlage Flakturm":   "Wien",
    "Edelweiss Südstadt":       "Wien",
    "Edelweiß Südstadt":        "Wien",
    "Blockfabrik":              "Wien",
    "Cube Kletterzentrum":      "Wien",
    # ── Austria — Hohe Wand / Niederösterreich ───────────────────────────────
    "Hohe Wand":                "Hohe Wand",
    "Johannesbachklamm":        "Hohe Wand",
    "Ewige Jagdgründe":         "Niederösterreich",
    "Höllental":                "Niederösterreich",
    "Thalhofergrat":            "Niederösterreich",
    "Engelswand":               "Niederösterreich",
    "Adlitzgräben":             "Niederösterreich",
    "Schrattenbach":            "Niederösterreich",
    "Graischenstein":           "Niederösterreich",
    # ── Austria — Tirol ──────────────────────────────────────────────────────
    "Oetz":                     "Tirol",
    "Zemmschlucht":             "Tirol",
    # ── Austria — Styria / other ─────────────────────────────────────────────
    "Höllental":                "Niederösterreich",
    # ── Cala Gonone, Sardinia ────────────────────────────────────────────────
    "Baunei":                   "Cala Gonone",
    "Cala Gonone -  Chorro":    "Cala Gonone",
    "Cala Gonone - Biddiriscottai": "Cala Gonone",
    "Su Casteddu":              "Cala Gonone",
    "Pedra Longa":              "Cala Gonone",
    # ── Kalymnos, Greece ─────────────────────────────────────────────────────
    "Sabaton":                  "Kalymnos",
    "Hospital":                 "Kalymnos",
    "Giggerl":                  "Kalymnos",
    "Theós":                    "Kalymnos",
    "Kokkinovrachos":           "Kalymnos",
    # ── Istria / Croatia ─────────────────────────────────────────────────────
    "Buzetski kanjon":          "Istria",
    "Kompanj":                  "Istria",
    "Kamena vrata":             "Istria",
    "Čiritež":                  "Istria",
    # ── North America ────────────────────────────────────────────────────────
    "Squamish":                 "Squamish",
    "Royal Arches":             "Yosemite",
}
_FRANKEN_DEFAULT = "Fränkische Schweiz"  # fallback for unlisted outdoor locations


def _resolve_region(location: str, route_type: str) -> str:
    if location in _LOCATION_REGION:
        return _LOCATION_REGION[location]
    if "GYM" in route_type.upper():
        return "Wien"  # unknown gym → assume Vienna (all known gyms in data are Vienna)
    return _FRANKEN_DEFAULT


# ─── Blog CSV: type / style mapping ───────────────────────────────────────────

_ROUTE_TYPE_MAP: dict[str, tuple[ActivityType, list[str]]] = {
    "ROUTE":       (ActivityType.sport_climb, ["outdoor"]),
    "GYM_ROUTE":   (ActivityType.sport_climb, ["indoor"]),
    "GYM_BOULDER": (ActivityType.bouldering,  ["indoor"]),
    "BOULDER":     (ActivityType.bouldering,  ["outdoor"]),
    "Trad":        (ActivityType.sport_climb, ["outdoor", "trad"]),
    "Sport":       (ActivityType.sport_climb, ["outdoor"]),
    "Aid":         (ActivityType.sport_climb, ["outdoor", "aid"]),
    "Sport, Aid":  (ActivityType.sport_climb, ["outdoor", "aid"]),
}

_STYLE_MAP: dict[str, ClimbStyle] = {
    "rp": ClimbStyle.redpoint, "Redpoint": ClimbStyle.redpoint,
    "os": ClimbStyle.onsight,  "Onsight":  ClimbStyle.onsight,
    "f":  ClimbStyle.flash,    "Flash":    ClimbStyle.flash,
    "tr": ClimbStyle.top_rope,
    "go": ClimbStyle.redpoint,   # ground-up treated as redpoint
    "fh": ClimbStyle.attempt, "Fell/Hung": ClimbStyle.attempt,
}


class BlogCsvImportResult(BaseModel):
    imported_sessions: int
    imported_routes: int
    skipped_sessions: int
    errors: list[str]

router = APIRouter(tags=["import"])


# ─── Type mapping ─────────────────────────────────────────────────────────────
# intervals.icu / Garmin activity type strings → our ActivityType + tags

_TYPE_MAP: dict[str, tuple[ActivityType, list[str]]] = {
    # Cycling
    "Ride":        (ActivityType.cycling, []),
    "VirtualRide": (ActivityType.cycling, ["indoor"]),
    "EBikeRide":   (ActivityType.cycling, ["e_bike"]),
    "MountainBikeRide": (ActivityType.cycling, ["mtb"]),
    "GravelRide":  (ActivityType.cycling, ["gravel_bike"]),
    "Handcycle":   (ActivityType.cycling, []),
    # Hiking / walking
    "Hike":        (ActivityType.hiking, []),
    "Walk":        (ActivityType.hiking, []),
    "Snowshoe":    (ActivityType.hiking, []),
    "Backpacking": (ActivityType.hiking, []),
    # Running / fitness
    "Run":         (ActivityType.fitness, ["run"]),
    "VirtualRun":  (ActivityType.fitness, ["run", "indoor"]),
    "TrailRun":    (ActivityType.fitness, ["trail_run"]),
    "Swim":        (ActivityType.fitness, ["swim"]),
    "OpenWaterSwim": (ActivityType.fitness, ["swim"]),
    "WeightTraining": (ActivityType.fitness, ["gym"]),
    "Workout":     (ActivityType.fitness, []),
    "Yoga":        (ActivityType.fitness, ["yoga"]),
    "Crossfit":    (ActivityType.fitness, ["gym"]),
    "HIIT":        (ActivityType.fitness, ["gym"]),
    "Pilates":     (ActivityType.fitness, []),
    "Elliptical":  (ActivityType.fitness, ["gym"]),
    "StairStepper": (ActivityType.fitness, ["gym"]),
    # Climbing
    "RockClimbing":  (ActivityType.sport_climb, []),
    "Climb":         (ActivityType.sport_climb, []),
    "Bouldering":    (ActivityType.bouldering, []),
    # Alpine / ski
    "AlpineSki":       (ActivityType.other, ["alpine_ski"]),
    "BackcountrySki":  (ActivityType.other, ["backcountry_ski"]),
    "NordicSki":       (ActivityType.other, ["nordic_ski"]),
    "Snowboard":       (ActivityType.other, ["snowboard"]),
    # Other
    "Kayaking":      (ActivityType.other, ["kayak"]),
    "Canoeing":      (ActivityType.other, ["canoe"]),
    "Rowing":        (ActivityType.other, ["row"]),
    "StandUpPaddling": (ActivityType.other, ["sup"]),
    "Soccer":        (ActivityType.fitness, ["team_sport"]),
    "Tennis":        (ActivityType.fitness, ["tennis"]),
    "Golf":          (ActivityType.other, ["golf"]),
}

_DEFAULT = (ActivityType.other, [])


def _map_type(raw_type: str) -> tuple[ActivityType, list[str]]:
    return _TYPE_MAP.get(raw_type, _DEFAULT)


# ─── Response model ───────────────────────────────────────────────────────────

class ImportResult(BaseModel):
    total_fetched: int
    imported: int
    skipped: int
    errors: list[str]


# ─── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/import/intervals", response_model=ImportResult)
async def import_from_intervals(
    days_back: int = Query(default=365, ge=1, le=3650,
                           description="How many days back to import"),
    session: AsyncSession = Depends(get_session),
) -> ImportResult:
    """
    Bulk-import all activities from intervals.icu (Garmin sync) for the last
    `days_back` days. Already-imported activities (matched by intervals_activity_id)
    are skipped so the endpoint is safe to call repeatedly.
    """
    from app.services.intervals import fetch_all_activities

    errors: list[str] = []

    # 1. Fetch from intervals.icu
    try:
        raw_activities = await fetch_all_activities(days_back=days_back)
    except Exception as exc:
        return ImportResult(
            total_fetched=0, imported=0, skipped=0,
            errors=[f"intervals.icu fetch failed: {exc}"],
        )

    if not raw_activities:
        return ImportResult(
            total_fetched=0, imported=0, skipped=0,
            errors=["No activities returned — check INTERVALS_ICU_API_KEY and INTERVALS_ICU_ATHLETE_ID"],
        )

    # 2. Load the set of already-imported intervals IDs
    existing_result = await session.execute(
        select(Activity.intervals_activity_id)
        .where(Activity.intervals_activity_id.isnot(None))
    )
    existing_ids: set[str] = {str(r[0]) for r in existing_result.all()}

    # 3. Import new activities
    imported = 0
    skipped = 0

    for raw in raw_activities:
        if raw.id in existing_ids:
            skipped += 1
            continue

        activity_type, tags = _map_type(raw.activity_type)

        # Parse date
        try:
            date = datetime.fromisoformat(raw.start_date_local)
        except (ValueError, TypeError):
            date = datetime.utcnow()

        activity = Activity(
            activity_type=activity_type,
            title=raw.name,
            date=date,
            duration_minutes=round(raw.duration_seconds / 60) if raw.duration_seconds else None,
            distance_km=round(raw.distance_m / 1000, 2) if raw.distance_m else None,
            elevation_gain_m=round(raw.elevation_gain_m) if raw.elevation_gain_m is not None else None,
            lat=raw.start_lat,
            lon=raw.start_lon,
            tags=tags,
            source=ActivitySource.intervals_icu,
            intervals_activity_id=raw.id,
        )
        session.add(activity)
        imported += 1

    if imported > 0:
        try:
            await session.commit()
        except Exception as exc:
            await session.rollback()
            errors.append(f"DB commit failed: {exc}")
            imported = 0

    return ImportResult(
        total_fetched=len(raw_activities),
        imported=imported,
        skipped=skipped,
        errors=errors,
    )


# ─── Blog CSV import ───────────────────────────────────────────────────────────

@router.post("/import/blog-csv", response_model=BlogCsvImportResult)
async def import_blog_csv(
    file: UploadFile = File(..., description="CSV export from Vertical Life / Mountain Project"),
    db: AsyncSession = Depends(get_session),
) -> BlogCsvImportResult:
    """
    Import historical climbing routes from the blog CSV (Vertical Life / Mountain Project export).
    Groups rows by (date, location, route_type) into sessions (Activities) with individual
    SessionRoutes. Already-imported sessions (matched by raw_json import_key) are skipped.
    """
    errors: list[str] = []

    # 1. Parse CSV
    content = await file.read()
    try:
        rows = list(csv.DictReader(io.StringIO(content.decode("utf-8"))))
    except Exception as exc:
        return BlogCsvImportResult(
            imported_sessions=0, imported_routes=0, skipped_sessions=0,
            errors=[f"CSV parse failed: {exc}"],
        )

    # 2. Group rows → sessions keyed by (date_str, location, route_type)
    sessions: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        raw_date = row.get("date", "")
        location = (row.get("location") or "").strip()
        route_type = (row.get("route_type") or "ROUTE").strip()
        try:
            date_key = datetime.fromisoformat(raw_date.replace("Z", "+00:00")).date().isoformat()
        except (ValueError, TypeError):
            errors.append(f"Bad date '{raw_date}' for route '{row.get('route_name')}' — skipped")
            continue
        sessions[(date_key, location, route_type)].append(row)

    # 3. Load existing import keys to enable idempotency
    existing_result = await db.execute(
        select(Activity.raw_json).where(Activity.raw_json.isnot(None))
    )
    existing_keys: set[str] = set()
    for (rj,) in existing_result.all():
        if isinstance(rj, dict) and "import_key" in rj:
            existing_keys.add(rj["import_key"])

    # 4. Import sessions
    imported_sessions = 0
    imported_routes = 0
    skipped_sessions = 0

    for (date_key, location, route_type), route_rows in sessions.items():
        import_key = f"blog_csv::{date_key}::{location}::{route_type}"
        if import_key in existing_keys:
            skipped_sessions += 1
            continue

        activity_type, tags = _ROUTE_TYPE_MAP.get(route_type, (ActivityType.sport_climb, ["outdoor"]))
        region = _resolve_region(location, route_type)

        # Use GPS coords from first route that has them
        lat, lon = None, None
        for r in route_rows:
            try:
                lat = float(r["latitude"]) if r.get("latitude") else None
                lon = float(r["longitude"]) if r.get("longitude") else None
                if lat and lon:
                    break
            except (ValueError, TypeError):
                pass

        try:
            session_date = datetime.fromisoformat(
                route_rows[0]["date"].replace("Z", "+00:00")
            ).replace(tzinfo=None)
        except (ValueError, TypeError, KeyError):
            session_date = datetime.utcnow()

        activity = Activity(
            activity_type=activity_type,
            title=f"Climbing at {location}",
            date=session_date,
            source=ActivitySource.manual,
            area=location,
            region=region,
            tags=tags,
            lat=lat,
            lon=lon,
            raw_json={"import_key": import_key, "csv_source": route_rows[0].get("source", "")},
        )
        db.add(activity)
        await db.flush()  # get activity.id

        for i, r in enumerate(route_rows):
            try:
                raw_stars = r.get("stars") or ""
                stars = round(float(raw_stars)) if raw_stars and raw_stars != "null" else None
                # Normalize 0-5 scale to 0-3
                if stars is not None:
                    stars = min(3, max(0, round(stars * 3 / 5)))
            except (ValueError, TypeError):
                stars = None

            try:
                tries = int(r["tries"]) if r.get("tries") else None
            except (ValueError, TypeError):
                tries = None

            raw_height = r.get("height") or ""
            try:
                height_m = float(raw_height) if raw_height else None
            except (ValueError, TypeError):
                height_m = None

            route = SessionRoute(
                activity_id=activity.id,
                route_name=r.get("route_name") or None,
                grade=r.get("grade") or None,
                grade_system=GradeSystem.french if r.get("grade") else None,
                style=_STYLE_MAP.get(r.get("style", ""), None),
                sector=r.get("sector") or None,
                height_m=height_m,
                notes=r.get("comment") or None,
                stars=stars,
                tries=tries,
                url=r.get("url") or None,
                sort_order=i,
            )
            db.add(route)
            imported_routes += 1

        imported_sessions += 1

    if imported_sessions > 0:
        try:
            await db.commit()
        except Exception as exc:
            await db.rollback()
            errors.append(f"DB commit failed: {exc}")
            imported_sessions = 0
            imported_routes = 0

    return BlogCsvImportResult(
        imported_sessions=imported_sessions,
        imported_routes=imported_routes,
        skipped_sessions=skipped_sessions,
        errors=errors,
    )
