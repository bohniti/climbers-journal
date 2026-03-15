from datetime import date

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from climbers_journal.models.climbing import (
    Area,
    Ascent,
    Crag,
    GradeSystem,
    Route,
    RouteStyle,
    TickType,
    VenueType,
    normalize_name,
    suggest_grade_system,
)


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
    session: AsyncSession, *, offset: int = 0, limit: int = 50
) -> list[Crag]:
    result = await session.exec(
        select(Crag).order_by(Crag.name).offset(offset).limit(limit)
    )
    return list(result.all())


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
                grade=item.get("grade", "?"),
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
            skip_dedup=True,  # already checked above
        )
        created_ascents.append(ascent)

    await session.flush()

    return {
        "crag_id": crag.id,
        "crag_name": crag.name,
        "crag_created": crag_created,
        "ascents_created": len(created_ascents),
        "ascents_skipped": skipped,
    }
