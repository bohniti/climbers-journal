"""Dashboard stats endpoints."""

import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import case, func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from climbers_journal.db import get_session
from climbers_journal.models.climbing import (
    Ascent,
    Crag,
    TickType,
    VenueType,
)
from climbers_journal.models.endurance import EnduranceActivity

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
    duration_s: int
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
            func.coalesce(func.sum(EnduranceActivity.duration_s), 0).label("duration"),
            func.coalesce(func.sum(EnduranceActivity.distance_m), 0).label("distance"),
            func.coalesce(func.sum(EnduranceActivity.training_load), 0).label("load"),
        )
        .select_from(EnduranceActivity)
        .where(EnduranceActivity.date >= week_ago, EnduranceActivity.date <= today)
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
        select(EnduranceActivity)
        .where(EnduranceActivity.date >= date_from, EnduranceActivity.date <= date_to)
        .order_by(EnduranceActivity.date.desc())
        .limit(20)
    )
    result = await session.exec(stmt)
    return [
        RecentEnduranceItem(
            id=a.id,
            date=a.date,
            type=a.type,
            name=a.name,
            duration_s=a.duration_s,
            distance_m=a.distance_m,
            training_load=a.training_load,
        )
        for a in result.all()
    ]
