import logging
from datetime import date

from fastapi import HTTPException
from sqlalchemy import func, text, union_all
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from climbers_journal.models.climbing import (
    Area,
    Ascent,
    ClimbingSession,
    Crag,
    GradeSystem,
    Route,
    RouteStyle,
    TickType,
    VenueType,
    normalize_name,
    suggest_grade_system,
)
from climbers_journal.models.endurance import EnduranceActivity

logger = logging.getLogger(__name__)


# ── Crag ───────────────────────────────────────────────────────────────


async def find_crag_by_name(session: AsyncSession, name: str) -> Crag | None:
    normalized = normalize_name(name)
    result = await session.exec(
        select(Crag).where(Crag.name_normalized == normalized)
    )
    return result.first()


async def create_or_find_crag(
    session: AsyncSession,
    *,
    name: str,
    country: str | None = None,
    region: str | None = None,
    venue_type: VenueType = VenueType.outdoor_crag,
    default_grade_sys: GradeSystem | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    description: str | None = None,
) -> tuple[Crag, bool]:
    """Find existing crag by normalized name, or create a new one.

    Returns (crag, created) where created is True if a new crag was made.
    """
    existing = await find_crag_by_name(session, name)
    if existing:
        return existing, False

    grade_sys = default_grade_sys or suggest_grade_system(country)
    crag = Crag(
        name=name,
        name_normalized=normalize_name(name),
        country=country,
        region=region,
        venue_type=venue_type,
        default_grade_sys=grade_sys,
        latitude=latitude,
        longitude=longitude,
        description=description,
    )
    session.add(crag)
    await session.flush()
    return crag, True


async def list_crags(
    session: AsyncSession,
    *,
    search: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[Crag]:
    stmt = select(Crag)
    if search:
        normalized = normalize_name(search)
        stmt = stmt.where(Crag.name_normalized.contains(normalized))  # type: ignore[union-attr]
    result = await session.exec(
        stmt.order_by(Crag.name).offset(offset).limit(limit)
    )
    return list(result.all())


async def get_crag(session: AsyncSession, crag_id: int) -> Crag | None:
    return await session.get(Crag, crag_id)


async def get_crag_stats(session: AsyncSession, crag_id: int) -> dict:
    """Compute stats for a crag: session count, route count, hardest send, last visited."""
    session_count_r = await session.exec(
        select(func.count()).select_from(ClimbingSession).where(
            ClimbingSession.crag_id == crag_id
        )
    )
    session_count = session_count_r.one()

    route_count_r = await session.exec(
        select(func.count()).select_from(Route).where(Route.crag_id == crag_id)
    )
    route_count = route_count_r.one()

    ascent_count_r = await session.exec(
        select(func.count()).select_from(Ascent).where(Ascent.crag_id == crag_id)
    )
    ascent_count = ascent_count_r.one()

    # Last visited date
    last_visited_r = await session.exec(
        select(func.max(ClimbingSession.date)).where(
            ClimbingSession.crag_id == crag_id
        )
    )
    last_visited = last_visited_r.one()

    # Hardest send (exclude attempts/hangs)
    send_types = [
        TickType.onsight, TickType.flash, TickType.redpoint,
        TickType.pinkpoint, TickType.repeat,
    ]
    hardest_r = await session.exec(
        select(Ascent)
        .where(
            Ascent.crag_id == crag_id,
            Ascent.tick_type.in_(send_types),  # type: ignore[union-attr]
            Ascent.grade.isnot(None),  # type: ignore[union-attr]
        )
        .order_by(Ascent.grade.desc())  # type: ignore[union-attr]
        .limit(1)
    )
    hardest_ascent = hardest_r.first()
    hardest_send = None
    if hardest_ascent:
        hardest_send = {
            "grade": hardest_ascent.grade,
            "route_name": hardest_ascent.route_name,
            "tick_type": hardest_ascent.tick_type.value,
            "date": hardest_ascent.date.isoformat(),
        }

    return {
        "session_count": session_count,
        "route_count": route_count,
        "ascent_count": ascent_count,
        "last_visited": last_visited.isoformat() if last_visited else None,
        "hardest_send": hardest_send,
    }


async def list_crags_with_stats(
    session: AsyncSession,
    *,
    search: str | None = None,
    sort: str = "last_visited",
    offset: int = 0,
    limit: int = 50,
) -> list[dict]:
    """List crags with session count and last visited date for the browser page."""
    # Subquery for session count and last visited
    session_stats = (
        select(
            ClimbingSession.crag_id,
            func.count(ClimbingSession.id).label("session_count"),
            func.max(ClimbingSession.date).label("last_visited"),
        )
        .group_by(ClimbingSession.crag_id)
        .subquery()
    )

    stmt = (
        select(
            Crag,
            func.coalesce(session_stats.c.session_count, 0).label("session_count"),
            session_stats.c.last_visited,
        )
        .outerjoin(session_stats, Crag.id == session_stats.c.crag_id)
    )

    if search:
        normalized = normalize_name(search)
        stmt = stmt.where(Crag.name_normalized.contains(normalized))  # type: ignore[union-attr]

    if sort == "name":
        stmt = stmt.order_by(Crag.name)
    elif sort == "session_count":
        stmt = stmt.order_by(
            func.coalesce(session_stats.c.session_count, 0).desc(),
            Crag.name,
        )
    else:  # last_visited (default)
        stmt = stmt.order_by(
            func.coalesce(session_stats.c.last_visited, date(1970, 1, 1)).desc(),
            Crag.name,
        )

    result = await session.execute(stmt.offset(offset).limit(limit))
    rows = result.all()

    return [
        {
            "id": crag.id,
            "name": crag.name,
            "country": crag.country,
            "region": crag.region,
            "venue_type": crag.venue_type.value,
            "default_grade_sys": crag.default_grade_sys.value,
            "session_count": sc,
            "last_visited": lv.isoformat() if lv else None,
        }
        for crag, sc, lv in rows
    ]


# ── Area ───────────────────────────────────────────────────────────────


async def create_or_find_area(
    session: AsyncSession,
    *,
    name: str,
    crag_id: int,
    description: str | None = None,
) -> tuple[Area, bool]:
    normalized = normalize_name(name)
    result = await session.exec(
        select(Area).where(
            Area.crag_id == crag_id,
            Area.name_normalized == normalized,
        )
    )
    existing = result.first()
    if existing:
        return existing, False

    area = Area(
        name=name,
        name_normalized=normalized,
        crag_id=crag_id,
        description=description,
    )
    session.add(area)
    await session.flush()
    return area, True


async def list_areas(
    session: AsyncSession, *, crag_id: int, offset: int = 0, limit: int = 50
) -> list[Area]:
    result = await session.exec(
        select(Area)
        .where(Area.crag_id == crag_id)
        .order_by(Area.name)
        .offset(offset)
        .limit(limit)
    )
    return list(result.all())


# ── Route ──────────────────────────────────────────────────────────────


async def create_or_find_route(
    session: AsyncSession,
    *,
    name: str,
    grade: str,
    crag_id: int,
    area_id: int | None = None,
    grade_system: GradeSystem | None = None,
    style: RouteStyle = RouteStyle.sport,
    pitches: int = 1,
    height_m: int | None = None,
    description: str | None = None,
) -> tuple[Route, bool]:
    normalized = normalize_name(name)
    stmt = select(Route).where(
        Route.crag_id == crag_id,
        Route.name_normalized == normalized,
    )
    if area_id is not None:
        stmt = stmt.where(Route.area_id == area_id)
    result = await session.exec(stmt)
    existing = result.first()
    if existing:
        return existing, False

    # Inherit grade system from crag if not specified
    if grade_system is None:
        crag = await session.get(Crag, crag_id)
        grade_system = crag.default_grade_sys if crag else GradeSystem.french

    route = Route(
        name=name,
        name_normalized=normalized,
        grade=grade,
        grade_system=grade_system,
        style=style,
        pitches=pitches,
        height_m=height_m,
        description=description,
        crag_id=crag_id,
        area_id=area_id,
    )
    session.add(route)
    await session.flush()
    return route, True


async def list_routes(
    session: AsyncSession,
    *,
    crag_id: int,
    area_id: int | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[Route]:
    stmt = select(Route).where(Route.crag_id == crag_id)
    if area_id is not None:
        stmt = stmt.where(Route.area_id == area_id)
    result = await session.exec(stmt.order_by(Route.name).offset(offset).limit(limit))
    return list(result.all())


# ── Ascent ─────────────────────────────────────────────────────────────


async def is_duplicate_ascent(
    session: AsyncSession,
    *,
    route_id: int | None,
    crag_id: int,
    tick_type: TickType,
    ascent_date: date,
    grade: str | None = None,
) -> bool:
    """Check for duplicate: same route + date + tick_type."""
    stmt = select(func.count()).select_from(Ascent).where(
        Ascent.crag_id == crag_id,
        Ascent.date == ascent_date,
        Ascent.tick_type == tick_type,
    )
    if route_id is not None:
        stmt = stmt.where(Ascent.route_id == route_id)
    else:
        # Gym ascent without route — match on grade too
        stmt = stmt.where(Ascent.route_id.is_(None))  # type: ignore[union-attr]
        if grade is not None:
            stmt = stmt.where(Ascent.grade == grade)
    result = await session.exec(stmt)
    return result.one() > 0


async def create_ascent(
    session: AsyncSession,
    *,
    ascent_date: date,
    tick_type: TickType,
    crag_id: int,
    route_id: int | None = None,
    tries: int | None = None,
    rating: int | None = None,
    notes: str | None = None,
    partner: str | None = None,
    grade: str | None = None,
    session_id: int | None = None,
    skip_dedup: bool = False,
) -> Ascent:
    """Create an ascent. Validates constraints and checks for duplicates."""
    # Validate date not in future
    if ascent_date > date.today():
        raise HTTPException(
            status_code=422,
            detail="Ascent date cannot be in the future.",
        )

    # Validate outdoor ascents require route_id
    crag = await session.get(Crag, crag_id)
    if crag is None:
        raise HTTPException(status_code=404, detail="Crag not found.")
    if crag.venue_type == VenueType.outdoor_crag and route_id is None:
        raise HTTPException(
            status_code=422,
            detail="Outdoor ascents require a route.",
        )

    # Validate rating range
    if rating is not None and not (1 <= rating <= 5):
        raise HTTPException(
            status_code=422,
            detail="Rating must be between 1 and 5.",
        )

    # Dedup check
    if not skip_dedup and await is_duplicate_ascent(
        session,
        route_id=route_id,
        crag_id=crag_id,
        tick_type=tick_type,
        ascent_date=ascent_date,
        grade=grade,
    ):
        raise HTTPException(
            status_code=409,
            detail="Duplicate ascent: same route, date, and tick type.",
        )

    # Denormalize names
    crag_name = crag.name
    route_name = None
    if route_id is not None:
        route = await session.get(Route, route_id)
        if route is None:
            raise HTTPException(status_code=404, detail="Route not found.")
        route_name = route.name
        if grade is None:
            grade = route.grade

    ascent = Ascent(
        date=ascent_date,
        tick_type=tick_type,
        tries=tries,
        rating=rating,
        notes=notes,
        partner=partner,
        route_id=route_id,
        crag_id=crag_id,
        session_id=session_id,
        crag_name=crag_name,
        route_name=route_name,
        grade=grade,
    )
    session.add(ascent)
    await session.flush()
    return ascent


async def get_ascent(session: AsyncSession, ascent_id: int) -> Ascent | None:
    return await session.get(Ascent, ascent_id)


async def update_ascent(
    session: AsyncSession,
    ascent_id: int,
    **updates: object,
) -> Ascent:
    ascent = await session.get(Ascent, ascent_id)
    if ascent is None:
        raise HTTPException(status_code=404, detail="Ascent not found.")

    for key, value in updates.items():
        if value is not None:
            setattr(ascent, key, value)

    session.add(ascent)
    await session.flush()
    return ascent


async def delete_ascent(session: AsyncSession, ascent_id: int) -> None:
    ascent = await session.get(Ascent, ascent_id)
    if ascent is None:
        raise HTTPException(status_code=404, detail="Ascent not found.")
    await session.delete(ascent)
    await session.flush()


async def list_ascents(
    session: AsyncSession,
    *,
    crag_id: int | None = None,
    tick_type: TickType | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[Ascent]:
    stmt = select(Ascent)
    if crag_id is not None:
        stmt = stmt.where(Ascent.crag_id == crag_id)
    if tick_type is not None:
        stmt = stmt.where(Ascent.tick_type == tick_type)
    if date_from is not None:
        stmt = stmt.where(Ascent.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Ascent.date <= date_to)
    result = await session.exec(
        stmt.order_by(Ascent.date.desc()).offset(offset).limit(limit)  # type: ignore[union-attr]
    )
    return list(result.all())


# ── Climbing Session ──────────────────────────────────────────────────


async def get_or_create_session(
    session: AsyncSession,
    *,
    session_date: date,
    crag_id: int,
    crag_name: str | None = None,
    notes: str | None = None,
) -> tuple[ClimbingSession, bool]:
    """Get existing session for (date, crag_id) or create new one.

    Returns (climbing_session, created).
    """
    result = await session.exec(
        select(ClimbingSession).where(
            ClimbingSession.date == session_date,
            ClimbingSession.crag_id == crag_id,
        )
    )
    existing = result.first()
    if existing:
        return existing, False

    cs = ClimbingSession(
        date=session_date,
        crag_id=crag_id,
        crag_name=crag_name,
        notes=notes,
    )
    session.add(cs)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        # Concurrent insert won the race — re-query
        result = await session.exec(
            select(ClimbingSession).where(
                ClimbingSession.date == session_date,
                ClimbingSession.crag_id == crag_id,
            )
        )
        existing = result.first()
        if existing:
            return existing, False
        raise  # unexpected — unique constraint wasn't the cause

    # Auto-link RockClimbing endurance activity
    await _try_link_activity(session, cs)

    return cs, True


async def _try_link_activity(
    session: AsyncSession, cs: ClimbingSession
) -> None:
    """Try to auto-link a RockClimbing endurance activity to this session."""
    result = await session.exec(
        select(EnduranceActivity).where(
            EnduranceActivity.date == cs.date,
            EnduranceActivity.type == "RockClimbing",
        )
    )
    candidates = list(result.all())
    if len(candidates) == 1:
        cs.linked_activity_id = candidates[0].id
        session.add(cs)
    elif len(candidates) > 1:
        logger.warning(
            "Multiple RockClimbing activities on %s — skipping auto-link for session %s",
            cs.date, cs.id,
        )


async def auto_link_activity_to_session(
    session: AsyncSession, activity: EnduranceActivity
) -> None:
    """On endurance sync, check if a RockClimbing activity matches a session."""
    if activity.type != "RockClimbing":
        return

    result = await session.exec(
        select(ClimbingSession).where(
            ClimbingSession.date == activity.date,
            ClimbingSession.linked_activity_id.is_(None),  # type: ignore[union-attr]
        )
    )
    sessions = list(result.all())
    if len(sessions) == 1:
        sessions[0].linked_activity_id = activity.id
        session.add(sessions[0])
    elif len(sessions) > 1:
        # Pick session with most ascents
        best = None
        best_count = -1
        for cs in sessions:
            count_result = await session.exec(
                select(func.count()).select_from(Ascent).where(
                    Ascent.session_id == cs.id
                )
            )
            count = count_result.one()
            if count > best_count:
                best = cs
                best_count = count
        if best:
            best.linked_activity_id = activity.id
            session.add(best)
            logger.warning(
                "Ambiguous session match on %s — linked to session %s (%d ascents)",
                activity.date, best.id, best_count,
            )


async def list_climbing_sessions(
    session: AsyncSession,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    crag_id: int | None = None,
    offset: int = 0,
    limit: int = 20,
) -> list[ClimbingSession]:
    stmt = (
        select(ClimbingSession)
        .options(
            selectinload(ClimbingSession.ascents),  # type: ignore[arg-type]
            selectinload(ClimbingSession.linked_activity),  # type: ignore[arg-type]
        )
    )
    if date_from is not None:
        stmt = stmt.where(ClimbingSession.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(ClimbingSession.date <= date_to)
    if crag_id is not None:
        stmt = stmt.where(ClimbingSession.crag_id == crag_id)
    stmt = stmt.order_by(ClimbingSession.date.desc()).offset(offset).limit(limit)
    result = await session.exec(stmt)
    return list(result.unique().all())


async def get_climbing_session(
    session: AsyncSession, session_id: int
) -> ClimbingSession | None:
    stmt = (
        select(ClimbingSession)
        .options(
            selectinload(ClimbingSession.ascents),  # type: ignore[arg-type]
            selectinload(ClimbingSession.linked_activity),  # type: ignore[arg-type]
        )
        .where(ClimbingSession.id == session_id)
    )
    result = await session.exec(stmt)
    return result.first()


# ── Bulk Session Create ────────────────────────────────────────────────


async def create_climbing_session(
    session: AsyncSession,
    *,
    crag_name: str,
    crag_country: str | None = None,
    crag_region: str | None = None,
    venue_type: VenueType = VenueType.outdoor_crag,
    default_grade_sys: GradeSystem | None = None,
    ascents_data: list[dict],
    session_notes: str | None = None,
) -> dict:
    """Bulk create a climbing session: crag + routes + ascents in one transaction.

    ascents_data is a list of dicts, each with:
        route_name, grade, tick_type, date, tries?, rating?, notes?, partner?,
        area_name?, style?
    """
    crag, crag_created = await create_or_find_crag(
        session,
        name=crag_name,
        country=crag_country,
        region=crag_region,
        venue_type=venue_type,
        default_grade_sys=default_grade_sys,
    )

    # Determine session date from first ascent
    first_date = None
    for item in ascents_data:
        d = item["date"] if isinstance(item["date"], date) else date.fromisoformat(item["date"])
        if first_date is None or d < first_date:
            first_date = d
    if first_date is None:
        first_date = date.today()

    # Get or create the ClimbingSession record
    cs, _ = await get_or_create_session(
        session,
        session_date=first_date,
        crag_id=crag.id,  # type: ignore[arg-type]
        crag_name=crag.name,
        notes=session_notes,
    )

    created_ascents = []
    skipped = 0

    for item in ascents_data:
        route_id = None
        area_id = None

        # Handle area if provided
        if item.get("area_name"):
            area, _ = await create_or_find_area(
                session, name=item["area_name"], crag_id=crag.id  # type: ignore[arg-type]
            )
            area_id = area.id

        # Handle route if provided (not required for gym sessions)
        if item.get("route_name"):
            route, _ = await create_or_find_route(
                session,
                name=item["route_name"],
                grade=item.get("grade") or "?",
                crag_id=crag.id,  # type: ignore[arg-type]
                area_id=area_id,
                style=RouteStyle(item["style"]) if item.get("style") else RouteStyle.sport,
            )
            route_id = route.id

        tick_type = TickType(item["tick_type"])
        ascent_date = (
            item["date"] if isinstance(item["date"], date) else date.fromisoformat(item["date"])
        )

        # Check for duplicate before creating
        if await is_duplicate_ascent(
            session,
            route_id=route_id,
            crag_id=crag.id,  # type: ignore[arg-type]
            tick_type=tick_type,
            ascent_date=ascent_date,
            grade=item.get("grade"),
        ):
            skipped += 1
            continue

        ascent = await create_ascent(
            session,
            ascent_date=ascent_date,
            tick_type=tick_type,
            crag_id=crag.id,  # type: ignore[arg-type]
            route_id=route_id,
            tries=item.get("tries"),
            rating=item.get("rating"),
            notes=item.get("notes"),
            partner=item.get("partner"),
            grade=item.get("grade"),
            session_id=cs.id,
            skip_dedup=True,  # already checked above
        )
        created_ascents.append(ascent)

    await session.flush()

    return {
        "session_id": cs.id,
        "crag_id": crag.id,
        "crag_name": crag.name,
        "crag_created": crag_created,
        "ascents_created": len(created_ascents),
        "ascents_skipped": skipped,
    }


# ── Unified Feed ──────────────────────────────────────────────────────


async def get_activity_feed(
    session: AsyncSession,
    *,
    feed_type: str = "all",
    offset: int = 0,
    limit: int = 20,
) -> list[dict]:
    """Unified activity feed: sessions + endurance activities ordered by date desc.

    Returns list of dicts with 'kind' discriminator.
    """
    items: list[dict] = []

    if feed_type in ("all", "climbing"):
        sessions = await list_climbing_sessions(
            session, offset=0, limit=offset + limit
        )
        for cs in sessions:
            items.append({
                "kind": "session",
                "date": cs.date.isoformat(),
                "data": _session_to_dict(cs),
            })

    if feed_type in ("all", "endurance"):
        stmt = (
            select(EnduranceActivity)
            .order_by(EnduranceActivity.date.desc())
            .offset(0)
            .limit(offset + limit)
        )
        # Exclude RockClimbing activities that are linked to sessions
        if feed_type == "all":
            linked_ids = select(ClimbingSession.linked_activity_id).where(
                ClimbingSession.linked_activity_id.isnot(None)  # type: ignore[union-attr]
            )
            stmt = stmt.where(EnduranceActivity.id.notin_(linked_ids))  # type: ignore[union-attr]
        result = await session.exec(stmt)
        for ea in result.all():
            items.append({
                "kind": "endurance",
                "date": ea.date.isoformat(),
                "data": {
                    "id": ea.id,
                    "date": ea.date.isoformat(),
                    "type": ea.type,
                    "name": ea.name,
                    "duration_s": ea.duration_s,
                    "distance_m": ea.distance_m,
                    "elevation_gain_m": ea.elevation_gain_m,
                    "avg_hr": ea.avg_hr,
                    "max_hr": ea.max_hr,
                    "training_load": ea.training_load,
                },
            })

    # Sort by date descending, then apply offset/limit
    items.sort(key=lambda x: x["date"], reverse=True)
    return items[offset : offset + limit]


def _session_to_dict(cs: ClimbingSession) -> dict:
    """Serialize a ClimbingSession with nested ascents and linked activity."""
    linked = None
    if cs.linked_activity:
        linked = {
            "id": cs.linked_activity.id,
            "duration_s": cs.linked_activity.duration_s,
            "avg_hr": cs.linked_activity.avg_hr,
            "max_hr": cs.linked_activity.max_hr,
        }

    ascents = []
    for a in (cs.ascents or []):
        ascents.append({
            "id": a.id,
            "date": a.date.isoformat(),
            "route_name": a.route_name,
            "grade": a.grade,
            "tick_type": a.tick_type.value,
            "tries": a.tries,
            "rating": a.rating,
            "notes": a.notes,
            "partner": a.partner,
            "route_id": a.route_id,
            "crag_id": a.crag_id,
        })

    return {
        "id": cs.id,
        "date": cs.date.isoformat(),
        "crag_id": cs.crag_id,
        "crag_name": cs.crag_name,
        "notes": cs.notes,
        "linked_activity": linked,
        "ascents": ascents,
        "ascent_count": len(ascents),
    }


# ── Health Check ──────────────────────────────────────────────────────


async def get_data_health(session: AsyncSession) -> dict:
    """Return health stats for migration verification."""
    total_sessions_r = await session.exec(
        select(func.count()).select_from(ClimbingSession)
    )
    total_ascents_r = await session.exec(
        select(func.count()).select_from(Ascent)
    )
    orphaned_r = await session.exec(
        select(func.count()).select_from(Ascent).where(Ascent.session_id.is_(None))  # type: ignore[union-attr]
    )
    endurance_r = await session.exec(
        select(func.count()).select_from(EnduranceActivity)
    )

    return {
        "total_sessions": total_sessions_r.one(),
        "total_ascents": total_ascents_r.one(),
        "orphaned_ascents": orphaned_r.one(),
        "total_endurance_activities": endurance_r.one(),
    }


# ── Name Propagation ─────────────────────────────────────────────────


async def propagate_crag_name(
    session: AsyncSession, crag_id: int, new_name: str
) -> int:
    """Update denormalized crag_name on all Ascent and ClimbingSession records for a crag.

    Returns the total number of rows updated.
    """
    ascent_result = await session.execute(
        text("UPDATE ascent SET crag_name = :name WHERE crag_id = :cid"),
        {"name": new_name, "cid": crag_id},
    )
    session_result = await session.execute(
        text("UPDATE climbing_session SET crag_name = :name WHERE crag_id = :cid"),
        {"name": new_name, "cid": crag_id},
    )
    total = (ascent_result.rowcount or 0) + (session_result.rowcount or 0)
    return total
