"""Endpoints for syncing and listing endurance activities."""

import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from climbers_journal.db import get_session
from climbers_journal.models.endurance import ActivitySource
from climbers_journal.services import sync as sync_svc

router = APIRouter(tags=["sync"])


# ── Request/Response Schemas ───────────────────────────────────────────


class SyncRequest(BaseModel):
    oldest: datetime.date
    newest: datetime.date


class SyncFailure(BaseModel):
    month: str
    error: str


class SyncResponse(BaseModel):
    synced: list[str]
    failed: list[SyncFailure]
    total_created: int
    total_updated: int


class ActivityResponse(BaseModel):
    id: int
    intervals_id: str
    date: datetime.date
    type: str
    name: str | None
    duration_s: int
    distance_m: float | None
    elevation_gain_m: float | None
    avg_hr: int | None
    max_hr: int | None
    training_load: float | None
    intensity: float | None
    source: ActivitySource


# ── Endpoints ──────────────────────────────────────────────────────────


@router.post("/sync/intervals", response_model=SyncResponse)
async def trigger_sync(
    body: SyncRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await sync_svc.sync_activities(
        session,
        oldest=body.oldest,
        newest=body.newest,
    )
    return result


class ActivityUpdate(BaseModel):
    name: str | None = None


@router.put("/activities/{activity_id}", response_model=ActivityResponse)
async def update_activity(
    activity_id: int,
    body: ActivityUpdate,
    session: AsyncSession = Depends(get_session),
):
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    try:
        return await sync_svc.update_activity(session, activity_id, data)
    except ValueError:
        raise HTTPException(status_code=404, detail="Activity not found")


@router.get("/activities", response_model=list[ActivityResponse])
async def list_activities(
    activity_type: str | None = None,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    return await sync_svc.list_activities(
        session,
        activity_type=activity_type,
        date_from=date_from,
        date_to=date_to,
        offset=offset,
        limit=limit,
    )
