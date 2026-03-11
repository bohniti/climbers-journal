from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from datetime import datetime

from app.database import get_session
from app.models.activity import Activity, ActivityCreate, ActivityUpdate, ActivityOut, ActivityType
from app.models.route import SessionRoute, SessionRouteCreate

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("/regions", response_model=list[str])
async def list_regions(session: AsyncSession = Depends(get_session)):
    """Return all distinct non-null region values, sorted alphabetically."""
    result = await session.execute(
        select(Activity.region)
        .where(Activity.region.isnot(None))
        .distinct()
        .order_by(Activity.region)
    )
    return [row[0] for row in result.all()]


@router.get("/", response_model=list[ActivityOut])
async def list_activities(
    activity_type: Optional[ActivityType] = Query(None),
    region: Optional[str] = Query(None, description="Filter by region, e.g. 'Fränkische Schweiz'"),
    limit: int = Query(50, le=2000),
    offset: int = Query(0),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Activity).order_by(Activity.date.desc()).limit(limit).offset(offset)
    if activity_type:
        stmt = stmt.where(Activity.activity_type == activity_type)
    if region:
        stmt = stmt.where(Activity.region == region)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=ActivityOut, status_code=201)
async def create_activity(
    body: ActivityCreate,
    session: AsyncSession = Depends(get_session),
):
    """
    Create an activity.  If `routes` is included in the body it is accepted but
    ignored here — the caller should use POST /activities/{id}/routes instead, OR
    pass a special `_routes` field (handled below for the chat confirmation flow).
    """
    # Separate routes from activity fields
    data = body.model_dump()
    routes_data: list[dict] = data.pop("routes", None) or []

    activity = Activity(**data)
    session.add(activity)
    await session.commit()
    await session.refresh(activity)

    # Save routes if provided (chat flow passes them together)
    for i, route_dict in enumerate(routes_data):
        route_dict.setdefault("sort_order", i)
        route = SessionRoute(activity_id=activity.id, **route_dict)
        session.add(route)
    if routes_data:
        await session.commit()

    return activity


@router.get("/{activity_id}", response_model=ActivityOut)
async def get_activity(
    activity_id: int,
    session: AsyncSession = Depends(get_session),
):
    activity = await session.get(Activity, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.put("/{activity_id}", response_model=ActivityOut)
async def update_activity(
    activity_id: int,
    body: ActivityUpdate,
    session: AsyncSession = Depends(get_session),
):
    activity = await session.get(Activity, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(activity, key, value)
    activity.updated_at = datetime.utcnow()
    session.add(activity)
    await session.commit()
    await session.refresh(activity)
    return activity


@router.delete("/{activity_id}", status_code=204)
async def delete_activity(
    activity_id: int,
    session: AsyncSession = Depends(get_session),
):
    activity = await session.get(Activity, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    await session.delete(activity)
    await session.commit()
