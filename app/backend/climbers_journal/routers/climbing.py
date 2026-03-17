import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel.ext.asyncio.session import AsyncSession

from climbers_journal.db import get_session
from climbers_journal.models.climbing import (
    GradeSystem,
    RouteStyle,
    TickType,
    VenueType,
)
from climbers_journal.services import climbing as svc

router = APIRouter(tags=["climbing"])


# ── Request/Response Schemas ───────────────────────────────────────────


class AscentInput(BaseModel):
    route_name: str | None = None
    area_name: str | None = None
    grade: str | None = None
    tick_type: TickType
    date: datetime.date
    tries: int | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = None
    partner: str | None = None
    style: RouteStyle | None = None


class ClimbingSessionRequest(BaseModel):
    crag_name: str
    crag_country: str | None = None
    crag_region: str | None = None
    venue_type: VenueType = VenueType.outdoor_crag
    default_grade_sys: GradeSystem | None = None
    ascents: list[AscentInput]
    notes: str | None = None  # session-level notes


class ClimbingSessionResponse(BaseModel):
    session_id: int | None = None
    crag_id: int
    crag_name: str
    crag_created: bool
    ascents_created: int
    ascents_skipped: int


class AscentUpdate(BaseModel):
    date: datetime.date | None = None
    tick_type: TickType | None = None
    tries: int | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = None
    partner: str | None = None


class CragResponse(BaseModel):
    id: int
    name: str
    country: str | None
    region: str | None
    venue_type: VenueType
    default_grade_sys: GradeSystem


class RouteResponse(BaseModel):
    id: int
    name: str
    grade: str
    grade_system: GradeSystem
    style: RouteStyle
    pitches: int
    crag_id: int
    area_id: int | None


class AreaResponse(BaseModel):
    id: int
    name: str
    crag_id: int


class AscentResponse(BaseModel):
    id: int
    date: datetime.date
    tick_type: TickType
    tries: int | None
    rating: int | None
    notes: str | None
    partner: str | None
    route_id: int | None
    crag_id: int
    crag_name: str | None
    route_name: str | None
    grade: str | None
    session_id: int | None = None


class LinkedActivityData(BaseModel):
    id: int
    duration_s: int
    avg_hr: int | None
    max_hr: int | None


class SessionAscentResponse(BaseModel):
    id: int
    date: datetime.date
    route_name: str | None
    grade: str | None
    tick_type: str
    tries: int | None
    rating: int | None
    notes: str | None
    partner: str | None
    route_id: int | None
    crag_id: int


class SessionDetailResponse(BaseModel):
    id: int
    date: datetime.date
    crag_id: int
    crag_name: str | None
    notes: str | None
    linked_activity: LinkedActivityData | None
    ascents: list[SessionAscentResponse]
    ascent_count: int


# ── Bulk Session Create ────────────────────────────────────────────────


@router.post("/sessions/climbing", response_model=ClimbingSessionResponse)
async def create_climbing_session(
    body: ClimbingSessionRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await svc.create_climbing_session(
        session,
        crag_name=body.crag_name,
        crag_country=body.crag_country,
        crag_region=body.crag_region,
        venue_type=body.venue_type,
        default_grade_sys=body.default_grade_sys,
        ascents_data=[a.model_dump() for a in body.ascents],
        session_notes=body.notes,
    )
    await session.commit()
    return result


# ── Climbing Sessions ─────────────────────────────────────────────────


@router.get("/sessions/climbing", response_model=list[SessionDetailResponse])
async def list_climbing_sessions(
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
    crag_id: int | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    sessions = await svc.list_climbing_sessions(
        session,
        date_from=date_from,
        date_to=date_to,
        crag_id=crag_id,
        offset=offset,
        limit=limit,
    )
    return [_serialize_session(cs) for cs in sessions]


@router.get("/sessions/climbing/{session_id}", response_model=SessionDetailResponse)
async def get_climbing_session(
    session_id: int,
    session: AsyncSession = Depends(get_session),
):
    cs = await svc.get_climbing_session(session, session_id)
    if cs is None:
        raise HTTPException(status_code=404, detail="Climbing session not found.")
    return _serialize_session(cs)


def _serialize_session(cs) -> dict:
    linked = None
    if cs.linked_activity:
        linked = {
            "id": cs.linked_activity.id,
            "duration_s": cs.linked_activity.duration_s,
            "avg_hr": cs.linked_activity.avg_hr,
            "max_hr": cs.linked_activity.max_hr,
        }
    return {
        "id": cs.id,
        "date": cs.date,
        "crag_id": cs.crag_id,
        "crag_name": cs.crag_name,
        "notes": cs.notes,
        "linked_activity": linked,
        "ascents": [
            {
                "id": a.id,
                "date": a.date,
                "route_name": a.route_name,
                "grade": a.grade,
                "tick_type": a.tick_type.value,
                "tries": a.tries,
                "rating": a.rating,
                "notes": a.notes,
                "partner": a.partner,
                "route_id": a.route_id,
                "crag_id": a.crag_id,
            }
            for a in (cs.ascents or [])
        ],
        "ascent_count": len(cs.ascents or []),
    }


# ── Crags ──────────────────────────────────────────────────────────────


class CragWithStatsResponse(BaseModel):
    id: int
    name: str
    country: str | None
    region: str | None
    venue_type: VenueType
    default_grade_sys: GradeSystem
    session_count: int
    last_visited: datetime.date | None


class CragStatsResponse(BaseModel):
    session_count: int
    route_count: int
    ascent_count: int
    last_visited: datetime.date | None
    hardest_send: dict | None


@router.get("/crags", response_model=list[CragWithStatsResponse])
async def list_crags(
    search: str | None = None,
    sort: str = Query("last_visited", pattern="^(last_visited|name|session_count)$"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    return await svc.list_crags_with_stats(
        session, search=search, sort=sort, offset=offset, limit=limit
    )


@router.get("/crags/{crag_id}", response_model=CragResponse)
async def get_crag(
    crag_id: int,
    session: AsyncSession = Depends(get_session),
):
    crag = await svc.get_crag(session, crag_id)
    if crag is None:
        raise HTTPException(status_code=404, detail="Crag not found.")
    return crag


@router.get("/crags/{crag_id}/stats", response_model=CragStatsResponse)
async def get_crag_stats(
    crag_id: int,
    session: AsyncSession = Depends(get_session),
):
    crag = await svc.get_crag(session, crag_id)
    if crag is None:
        raise HTTPException(status_code=404, detail="Crag not found.")
    return await svc.get_crag_stats(session, crag_id)


@router.get("/crags/{crag_id}/sessions", response_model=list[SessionDetailResponse])
async def list_crag_sessions(
    crag_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    crag = await svc.get_crag(session, crag_id)
    if crag is None:
        raise HTTPException(status_code=404, detail="Crag not found.")
    sessions = await svc.list_climbing_sessions(
        session, crag_id=crag_id, offset=offset, limit=limit
    )
    return [_serialize_session(cs) for cs in sessions]


# ── Areas ──────────────────────────────────────────────────────────────


@router.get("/crags/{crag_id}/areas", response_model=list[AreaResponse])
async def list_areas(
    crag_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    return await svc.list_areas(session, crag_id=crag_id, offset=offset, limit=limit)


# ── Routes ─────────────────────────────────────────────────────────────


@router.get("/crags/{crag_id}/routes", response_model=list[RouteResponse])
async def list_routes(
    crag_id: int,
    area_id: int | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    return await svc.list_routes(
        session, crag_id=crag_id, area_id=area_id, offset=offset, limit=limit
    )


# ── Ascents ────────────────────────────────────────────────────────────


@router.get("/ascents", response_model=list[AscentResponse])
async def list_ascents(
    crag_id: int | None = None,
    tick_type: TickType | None = None,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    return await svc.list_ascents(
        session,
        crag_id=crag_id,
        tick_type=tick_type,
        date_from=date_from,
        date_to=date_to,
        offset=offset,
        limit=limit,
    )


@router.get("/ascents/{ascent_id}", response_model=AscentResponse)
async def get_ascent(
    ascent_id: int,
    session: AsyncSession = Depends(get_session),
):
    ascent = await svc.get_ascent(session, ascent_id)
    if ascent is None:
        raise HTTPException(status_code=404, detail="Ascent not found.")
    return ascent


@router.put("/ascents/{ascent_id}", response_model=AscentResponse)
async def update_ascent(
    ascent_id: int,
    body: AscentUpdate,
    session: AsyncSession = Depends(get_session),
):
    updates = body.model_dump(exclude_none=True)
    ascent = await svc.update_ascent(session, ascent_id, **updates)
    await session.commit()
    return ascent


@router.delete("/ascents/{ascent_id}", status_code=204)
async def delete_ascent(
    ascent_id: int,
    session: AsyncSession = Depends(get_session),
):
    await svc.delete_ascent(session, ascent_id)
    await session.commit()
