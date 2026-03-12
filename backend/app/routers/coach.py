"""Unified coach endpoint — handles logging, find/edit, and weekly summaries."""

from __future__ import annotations

from datetime import date as date_type, datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, or_

from app.database import get_session
from app.models.activity import Activity
from app.services.coach import run_coach

router = APIRouter(prefix="/coach", tags=["coach"])


# ─── Request / Response models ────────────────────────────────────────────────


class CoachImageData(BaseModel):
    content_type: str  # e.g. "image/jpeg"
    data: str          # base64-encoded bytes


class CoachMessage(BaseModel):
    role: str   # "user" | "assistant"
    content: str


class PendingUpdateOut(BaseModel):
    activity_id: int
    changes: dict[str, Any]
    current_values: dict[str, Any]


class CoachResponse(BaseModel):
    reply: str
    pending_activity: Optional[dict] = None
    needs_confirmation: bool = False
    pending_update: Optional[PendingUpdateOut] = None
    found_activities: Optional[list[dict]] = None


class CoachRequest(BaseModel):
    messages: list[CoachMessage]
    images: list[CoachImageData] = []
    location_context: Optional[str] = None


# ─── DB helper functions ──────────────────────────────────────────────────────


async def _search_activities(
    session: AsyncSession,
    query: Optional[str],
    activity_type: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
    limit: int,
) -> list[dict]:
    """Search activities in the DB and return list of dicts for the LLM."""
    stmt = select(Activity).order_by(Activity.date.desc())

    if activity_type:
        stmt = stmt.where(Activity.activity_type == activity_type)

    if date_from:
        try:
            df = datetime.combine(date_type.fromisoformat(date_from), datetime.min.time())
            stmt = stmt.where(Activity.date >= df)
        except ValueError:
            pass

    if date_to:
        try:
            dt = datetime.combine(date_type.fromisoformat(date_to), datetime.max.time())
            stmt = stmt.where(Activity.date <= dt)
        except ValueError:
            pass

    if query:
        q = f"%{query}%"
        stmt = stmt.where(
            or_(
                Activity.title.ilike(q),
                Activity.area.ilike(q),
                Activity.region.ilike(q),
                Activity.notes.ilike(q),
                Activity.partner.ilike(q),
                Activity.location_name.ilike(q),
            )
        )

    stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    activities = result.scalars().all()

    return [
        {
            "id": a.id,
            "title": a.title,
            "activity_type": a.activity_type.value if hasattr(a.activity_type, "value") else a.activity_type,
            "date": a.date.isoformat() if a.date else None,
            "area": a.area,
            "region": a.region,
            "duration_minutes": a.duration_minutes,
            "distance_km": a.distance_km,
            "elevation_gain_m": a.elevation_gain_m,
            "tags": a.tags or [],
            "partner": a.partner,
        }
        for a in activities
    ]


async def _get_weekly_summary(
    session: AsyncSession,
    week_start: Optional[str],
) -> dict:
    """Fetch weekly stats for the coach."""
    if week_start and week_start.lower() == "last":
        start_date = date_type.today() - timedelta(days=date_type.today().weekday() + 7)
    elif week_start:
        try:
            start_date = date_type.fromisoformat(week_start)
            # Snap to Monday
            start_date = start_date - timedelta(days=start_date.weekday())
        except ValueError:
            start_date = date_type.today() - timedelta(days=date_type.today().weekday())
    else:
        start_date = date_type.today() - timedelta(days=date_type.today().weekday())

    end_date = start_date + timedelta(days=6)
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    stmt = (
        select(Activity)
        .where(Activity.date >= start_dt)
        .where(Activity.date <= end_dt)
        .order_by(Activity.date)
    )
    result = await session.execute(stmt)
    activities = result.scalars().all()

    total_hours = 0.0
    total_elev = 0.0
    by_type: dict[str, int] = {}
    by_day: dict[str, list[dict]] = {}

    for i in range(7):
        d = (start_date + timedelta(days=i)).isoformat()
        by_day[d] = []

    for act in activities:
        act_type = act.activity_type.value if hasattr(act.activity_type, "value") else act.activity_type
        by_type[act_type] = by_type.get(act_type, 0) + 1
        if act.duration_minutes:
            total_hours += act.duration_minutes / 60
        if act.elevation_gain_m:
            total_elev += act.elevation_gain_m
        day_key = act.date.date().isoformat()
        if day_key in by_day:
            by_day[day_key].append({
                "id": act.id,
                "title": act.title,
                "activity_type": act_type,
                "duration_minutes": act.duration_minutes,
                "elevation_gain_m": act.elevation_gain_m,
                "distance_km": act.distance_km,
                "area": act.area,
                "partner": act.partner,
                "tags": act.tags or [],
            })

    return {
        "week_start": start_date.isoformat(),
        "week_end": end_date.isoformat(),
        "total_activities": len(activities),
        "total_hours": round(total_hours, 1),
        "total_elevation_m": round(total_elev),
        "by_type": by_type,
        "by_day": [{"date": d, "activities": acts} for d, acts in sorted(by_day.items())],
    }


async def _get_activity(session: AsyncSession, activity_id: int) -> dict:
    """Fetch a single activity as a dict."""
    act = await session.get(Activity, activity_id)
    if not act:
        raise ValueError(f"Activity {activity_id} not found")
    return {
        "id": act.id,
        "title": act.title,
        "activity_type": act.activity_type.value if hasattr(act.activity_type, "value") else act.activity_type,
        "date": act.date.isoformat() if act.date else None,
        "area": act.area,
        "region": act.region,
        "duration_minutes": act.duration_minutes,
        "distance_km": act.distance_km,
        "elevation_gain_m": act.elevation_gain_m,
        "tags": act.tags or [],
        "partner": act.partner,
        "notes": act.notes,
        "location_name": act.location_name,
        "avg_heart_rate": act.avg_heart_rate,
        "calories": act.calories,
    }


# ─── Endpoint ─────────────────────────────────────────────────────────────────


@router.post("/", response_model=CoachResponse)
async def coach(
    body: CoachRequest,
    session: AsyncSession = Depends(get_session),
):
    """Unified coach endpoint for logging, finding/editing, and summarising activities."""
    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    images = [{"content_type": img.content_type, "data": img.data} for img in body.images]

    async def db_search(query, activity_type, date_from, date_to, limit):
        return await _search_activities(session, query, activity_type, date_from, date_to, limit)

    async def db_weekly_summary(week_start):
        return await _get_weekly_summary(session, week_start)

    async def db_get_activity(activity_id):
        return await _get_activity(session, activity_id)

    result = await run_coach(
        messages=messages,
        images=images,
        location_context=body.location_context,
        db_search=db_search,
        db_weekly_summary=db_weekly_summary,
        db_get_activity=db_get_activity,
    )

    return CoachResponse(
        reply=result.reply,
        pending_activity=result.pending_activity,
        needs_confirmation=result.needs_confirmation,
        pending_update=PendingUpdateOut(
            activity_id=result.pending_update.activity_id,
            changes=result.pending_update.changes,
            current_values=result.pending_update.current_values,
        ) if result.pending_update else None,
        found_activities=result.found_activities,
    )
