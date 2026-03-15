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


class ClimbingSessionResponse(BaseModel):
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
    )
    await session.commit()
    return result


# ── Crags ──────────────────────────────────────────────────────────────


@router.get("/crags", response_model=list[CragResponse])
async def list_crags(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    return await svc.list_crags(session, offset=offset, limit=limit)


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
