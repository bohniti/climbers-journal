"""Dashboard stats and feed endpoints."""

import calendar as cal
import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import case, func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from climbers_journal.db import get_session
from climbers_journal.models.activity import Activity
from climbers_journal.models.climbing import (
    Ascent,
    Crag,
    TickType,
    VenueType,
)
from climbers_journal.services import activity as svc

router = APIRouter(prefix="/stats", tags=["stats"])

SEND_TICK_TYPES = {
    TickType.onsight,
    TickType.flash,
    TickType.redpoint,
    TickType.pinkpoint,
    TickType.repeat,
}
SEND_VALUES = [t.value for t in SEND_TICK_TYPES]


# ── Response Schemas ──────────────────────────────────────────────────


class GradePyramidEntry(BaseModel):
    grade: str
    onsight: int = 0
    flash: int = 0
    redpoint: int = 0
    pinkpoint: int = 0
    repeat: int = 0
    total: int = 0


class HardestSend(BaseModel):
    route_name: str | None
    grade: str
    tick_type: str
    crag_name: str | None
    date: datetime.date


class ClimbingStats(BaseModel):
    total_sends_week: int
    total_sends_month: int
    hardest_send: HardestSend | None


class EnduranceStats(BaseModel):
    activities_week: int
    total_duration_min_week: int
    total_distance_km_week: float
    total_training_load_week: float


class RecentClimbingItem(BaseModel):
    id: int
    date: datetime.date
    route_name: str | None
    grade: str | None
    tick_type: str
    crag_name: str | None


class RecentEnduranceItem(BaseModel):
    id: int
    date: datetime.date
    type: str
    name: str | None
    duration_s: int | None
    distance_m: float | None
    training_load: float | None


class DashboardResponse(BaseModel):
    grade_pyramid: list[GradePyramidEntry]
    climbing_stats: ClimbingStats
    endurance_stats: EnduranceStats
    recent_climbing: list[RecentClimbingItem]
    recent_endurance: list[RecentEnduranceItem]


# ── Grade Pyramid ─────────────────────────────────────────────────────


@router.get("/grade-pyramid", response_model=list[GradePyramidEntry])
async def get_grade_pyramid(
    venue_type: str | None = Query(None, description="outdoor_crag or indoor_gym"),
    period: str | None = Query(None, description="all_time, this_year, this_month"),
    session: AsyncSession = Depends(get_session),
):
    return await _build_grade_pyramid(session, venue_type=venue_type, period=period)


# ── Dashboard (all-in-one) ────────────────────────────────────────────


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    session: AsyncSession = Depends(get_session),
):
    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=7)
    month_ago = today - datetime.timedelta(days=30)

    # Grade pyramid (all time, all venues)
    pyramid = await _build_grade_pyramid(session)

    # Climbing stats
    climbing_stats = await _build_climbing_stats(session, week_ago, month_ago, today)

    # Endurance stats
    endurance_stats = await _build_endurance_stats(session, week_ago, today)

    # Recent activity (last 7 days)
    recent_climbing = await _recent_climbing(session, week_ago, today)
    recent_endurance = await _recent_endurance(session, week_ago, today)

    return DashboardResponse(
        grade_pyramid=pyramid,
        climbing_stats=climbing_stats,
        endurance_stats=endurance_stats,
        recent_climbing=recent_climbing,
        recent_endurance=recent_endurance,
    )


# ── Helpers ───────────────────────────────────────────────────────────


async def _build_grade_pyramid(
    session: AsyncSession,
    venue_type: str | None = None,
    period: str | None = None,
) -> list[GradePyramidEntry]:
    stmt = (
        select(Ascent.grade, Ascent.tick_type, func.count().label("count"))
        .where(Ascent.tick_type.in_(SEND_VALUES))
        .where(Ascent.grade.isnot(None))
        .group_by(Ascent.grade, Ascent.tick_type)
        .order_by(Ascent.grade)
    )

    if venue_type:
        venue_crag_ids = select(Crag.id).where(Crag.venue_type == VenueType(venue_type))
        stmt = stmt.where(Ascent.crag_id.in_(venue_crag_ids))

    if period == "this_year":
        stmt = stmt.where(Ascent.date >= datetime.date(datetime.date.today().year, 1, 1))
    elif period == "this_month":
        today = datetime.date.today()
        stmt = stmt.where(Ascent.date >= datetime.date(today.year, today.month, 1))

    result = await session.exec(stmt)
    rows = result.all()

    grades: dict[str, GradePyramidEntry] = {}
    for grade_val, tick_type_val, count in rows:
        if grade_val not in grades:
            grades[grade_val] = GradePyramidEntry(grade=grade_val)
        entry = grades[grade_val]
        setattr(entry, tick_type_val, count)
        entry.total += count

    return list(grades.values())


async def _build_climbing_stats(
    session: AsyncSession,
    week_ago: datetime.date,
    month_ago: datetime.date,
    today: datetime.date,
) -> ClimbingStats:
    # Sends this week
    week_stmt = (
        select(func.count())
        .select_from(Ascent)
        .where(Ascent.date >= week_ago, Ascent.date <= today)
        .where(Ascent.tick_type.in_(SEND_VALUES))
    )
    result = await session.exec(week_stmt)
    sends_week = result.one()

    # Sends this month
    month_stmt = (
        select(func.count())
        .select_from(Ascent)
        .where(Ascent.date >= month_ago, Ascent.date <= today)
        .where(Ascent.tick_type.in_(SEND_VALUES))
    )
    result = await session.exec(month_stmt)
    sends_month = result.one()

    # Hardest send (all time)
    hardest_stmt = (
        select(Ascent)
        .where(Ascent.tick_type.in_(SEND_VALUES))
        .where(Ascent.grade.isnot(None))
        .order_by(Ascent.grade.desc())
        .limit(1)
    )
    result = await session.exec(hardest_stmt)
    hardest = result.first()

    hardest_send = None
    if hardest:
        hardest_send = HardestSend(
            route_name=hardest.route_name,
            grade=hardest.grade,
            tick_type=hardest.tick_type.value,
            crag_name=hardest.crag_name,
            date=hardest.date,
        )

    return ClimbingStats(
        total_sends_week=sends_week,
        total_sends_month=sends_month,
        hardest_send=hardest_send,
    )


async def _build_endurance_stats(
    session: AsyncSession,
    week_ago: datetime.date,
    today: datetime.date,
) -> EnduranceStats:
    stmt = (
        select(
            func.count().label("count"),
            func.coalesce(func.sum(Activity.duration_s), 0).label("duration"),
            func.coalesce(func.sum(Activity.distance_m), 0).label("distance"),
            func.coalesce(func.sum(Activity.training_load), 0).label("load"),
        )
        .select_from(Activity)
        .where(
            Activity.type != "climbing",
            Activity.date >= week_ago,
            Activity.date <= today,
        )
    )
    result = await session.exec(stmt)
    row = result.one()

    return EnduranceStats(
        activities_week=row[0],
        total_duration_min_week=round(row[1] / 60),
        total_distance_km_week=round(row[2] / 1000, 1),
        total_training_load_week=round(row[3], 1),
    )


async def _recent_climbing(
    session: AsyncSession,
    date_from: datetime.date,
    date_to: datetime.date,
) -> list[RecentClimbingItem]:
    stmt = (
        select(Ascent)
        .where(Ascent.date >= date_from, Ascent.date <= date_to)
        .order_by(Ascent.date.desc())
        .limit(20)
    )
    result = await session.exec(stmt)
    return [
        RecentClimbingItem(
            id=a.id,
            date=a.date,
            route_name=a.route_name,
            grade=a.grade,
            tick_type=a.tick_type.value,
            crag_name=a.crag_name,
        )
        for a in result.all()
    ]


async def _recent_endurance(
    session: AsyncSession,
    date_from: datetime.date,
    date_to: datetime.date,
) -> list[RecentEnduranceItem]:
    stmt = (
        select(Activity)
        .where(
            Activity.type != "climbing",
            Activity.date >= date_from,
            Activity.date <= date_to,
        )
        .order_by(Activity.date.desc())
        .limit(20)
    )
    result = await session.exec(stmt)
    return [
        RecentEnduranceItem(
            id=a.id,
            date=a.date,
            type=a.subtype or a.type,
            name=a.name,
            duration_s=a.duration_s,
            distance_m=a.distance_m,
            training_load=a.training_load,
        )
        for a in result.all()
    ]


# ── Calendar ─────────────────────────────────────────────────────────


class CalendarClimbingDay(BaseModel):
    route_count: int
    hardest_grade: str | None
    venue_type: str  # "outdoor_crag", "indoor_gym", or "mixed"


class CalendarEnduranceDay(BaseModel):
    activities: list[dict]  # [{type, duration_s}]


class CalendarDayEntry(BaseModel):
    date: str  # YYYY-MM-DD
    climbing: CalendarClimbingDay | None = None
    endurance: CalendarEnduranceDay | None = None


class CalendarResponse(BaseModel):
    month: str  # YYYY-MM
    days: list[CalendarDayEntry]


@router.get("/calendar", response_model=CalendarResponse)
async def get_calendar(
    month: str = Query(..., description="Month in YYYY-MM format", pattern=r"^\d{4}-\d{2}$"),
    session: AsyncSession = Depends(get_session),
):
    year, mon = int(month[:4]), int(month[5:7])
    first_day = datetime.date(year, mon, 1)
    last_day = datetime.date(year, mon, cal.monthrange(year, mon)[1])

    # Climbing: count routes + hardest grade per day
    climbing_stmt = (
        select(
            Ascent.date,
            func.count().label("route_count"),
            func.max(Ascent.grade).label("hardest_grade"),
        )
        .where(Ascent.date >= first_day, Ascent.date <= last_day)
        .group_by(Ascent.date)
    )
    climbing_result = await session.exec(climbing_stmt)
    climbing_by_date: dict[datetime.date, dict] = {}
    for row_date, route_count, hardest_grade in climbing_result.all():
        climbing_by_date[row_date] = {
            "route_count": route_count,
            "hardest_grade": hardest_grade,
        }

    # Climbing: venue type per day (check if mixed)
    venue_stmt = (
        select(Ascent.date, Crag.venue_type)
        .join(Crag, Ascent.crag_id == Crag.id)
        .where(Ascent.date >= first_day, Ascent.date <= last_day)
        .group_by(Ascent.date, Crag.venue_type)
    )
    venue_result = await session.exec(venue_stmt)
    venue_types_by_date: dict[datetime.date, set[str]] = {}
    for row_date, venue_type in venue_result.all():
        venue_types_by_date.setdefault(row_date, set()).add(venue_type.value if hasattr(venue_type, 'value') else venue_type)

    # Endurance: non-climbing activities per day
    endurance_stmt = (
        select(Activity.date, Activity.subtype, Activity.duration_s)
        .where(
            Activity.type != "climbing",
            Activity.date >= first_day,
            Activity.date <= last_day,
        )
        .order_by(Activity.date)
    )
    endurance_result = await session.exec(endurance_stmt)
    endurance_by_date: dict[datetime.date, list[dict]] = {}
    for row_date, act_subtype, duration_s in endurance_result.all():
        endurance_by_date.setdefault(row_date, []).append(
            {"type": act_subtype, "duration_s": duration_s}
        )

    # Build response
    all_dates = sorted(set(list(climbing_by_date.keys()) + list(endurance_by_date.keys())))
    days: list[CalendarDayEntry] = []
    for d in all_dates:
        climbing_day = None
        if d in climbing_by_date:
            venues = venue_types_by_date.get(d, set())
            if len(venues) > 1:
                venue_str = "mixed"
            else:
                venue_str = next(iter(venues)) if venues else "outdoor_crag"
            climbing_day = CalendarClimbingDay(
                route_count=climbing_by_date[d]["route_count"],
                hardest_grade=climbing_by_date[d]["hardest_grade"],
                venue_type=venue_str,
            )

        endurance_day = None
        if d in endurance_by_date:
            endurance_day = CalendarEnduranceDay(activities=endurance_by_date[d])

        days.append(CalendarDayEntry(
            date=d.isoformat(),
            climbing=climbing_day,
            endurance=endurance_day,
        ))

    return CalendarResponse(month=month, days=days)


# ── Weekly Activity ──────────────────────────────────────────────────


class WeeklyAscentItem(BaseModel):
    route_name: str | None
    grade: str | None
    tick_type: str


class WeeklyEnduranceItem(BaseModel):
    type: str
    name: str | None
    duration_s: int | None


class WeeklyDayEntry(BaseModel):
    date: str  # YYYY-MM-DD
    climbing_count: int = 0
    ascents: list[WeeklyAscentItem] = []
    endurance_activities: list[WeeklyEnduranceItem] = []


class WeeklyResponse(BaseModel):
    week_start: str  # YYYY-MM-DD (Monday)
    days: list[WeeklyDayEntry]
    session_streak: int  # climbing days logged this month


@router.get("/weekly", response_model=WeeklyResponse)
async def get_weekly(
    week_start: str | None = Query(
        None,
        description="ISO date of Monday (defaults to current week)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    session: AsyncSession = Depends(get_session),
):
    if week_start:
        monday = datetime.date.fromisoformat(week_start)
    else:
        today = datetime.date.today()
        monday = today - datetime.timedelta(days=today.weekday())

    sunday = monday + datetime.timedelta(days=6)

    # Ascents for the week
    ascent_stmt = (
        select(Ascent)
        .where(Ascent.date >= monday, Ascent.date <= sunday)
        .order_by(Ascent.date)
    )
    ascent_result = await session.exec(ascent_stmt)
    ascents_by_date: dict[datetime.date, list] = {}
    for a in ascent_result.all():
        ascents_by_date.setdefault(a.date, []).append(a)

    # Non-climbing activities for the week
    endurance_stmt = (
        select(Activity)
        .where(
            Activity.type != "climbing",
            Activity.date >= monday,
            Activity.date <= sunday,
        )
        .order_by(Activity.date)
    )
    endurance_result = await session.exec(endurance_stmt)
    endurance_by_date: dict[datetime.date, list[Activity]] = {}
    for e in endurance_result.all():
        endurance_by_date.setdefault(e.date, []).append(e)

    # Build 7-day response
    days: list[WeeklyDayEntry] = []
    for i in range(7):
        d = monday + datetime.timedelta(days=i)
        day_ascents = ascents_by_date.get(d, [])
        day_endurance = endurance_by_date.get(d, [])
        days.append(WeeklyDayEntry(
            date=d.isoformat(),
            climbing_count=len(day_ascents),
            ascents=[
                WeeklyAscentItem(
                    route_name=a.route_name,
                    grade=a.grade,
                    tick_type=a.tick_type.value,
                )
                for a in day_ascents
            ],
            endurance_activities=[
                WeeklyEnduranceItem(
                    type=e.subtype or e.type,
                    name=e.name,
                    duration_s=e.duration_s,
                )
                for e in day_endurance
            ],
        ))

    # Session streak: count of distinct climbing days this month
    today = datetime.date.today()
    month_start = datetime.date(today.year, today.month, 1)
    streak_stmt = (
        select(func.count(func.distinct(Ascent.date)))
        .select_from(Ascent)
        .where(Ascent.date >= month_start)
    )
    streak_result = await session.exec(streak_stmt)
    session_streak = streak_result.one()

    return WeeklyResponse(
        week_start=monday.isoformat(),
        days=days,
        session_streak=session_streak,
    )


# ── Unified Feed ─────────────────────────────────────────────────────


@router.get("/feed")
async def get_feed(
    type: str = Query("all", description="all, climbing, or endurance"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    return await svc.get_activity_feed(
        session, feed_type=type, offset=offset, limit=limit
    )


# ── Data Health ──────────────────────────────────────────────────────


class DataHealthResponse(BaseModel):
    total_activities: int
    climbing_activities: int
    total_ascents: int
    orphaned_ascents: int


@router.get("/health", response_model=DataHealthResponse)
async def get_data_health(
    session: AsyncSession = Depends(get_session),
):
    return await svc.get_data_health(session)
