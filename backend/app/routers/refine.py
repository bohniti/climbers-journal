"""AI refinement endpoint for activities."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.models.activity import Activity
from app.models.photo import ActivityPhoto
from app.models.route import SessionRoute
from app.services.refine import refine_activity

router = APIRouter(tags=["refine"])


class RefineSuggestionOut(BaseModel):
    field: str
    current_value: Any = None
    suggested_value: Any = None


class RefineResponse(BaseModel):
    suggestions: list[RefineSuggestionOut]
    explanation: str


@router.post("/activities/{activity_id}/refine", response_model=RefineResponse)
async def refine_activity_endpoint(
    activity_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Use AI to suggest improvements to an activity's data."""
    activity = await session.get(Activity, activity_id)
    if not activity:
        raise HTTPException(404, "Activity not found")

    # Load routes
    routes_result = await session.execute(
        select(SessionRoute)
        .where(SessionRoute.activity_id == activity_id)
        .order_by(SessionRoute.sort_order)
    )
    routes = list(routes_result.scalars().all())

    # Load photos
    photos_result = await session.execute(
        select(ActivityPhoto)
        .where(ActivityPhoto.activity_id == activity_id)
        .order_by(ActivityPhoto.created_at)
    )
    photos = list(photos_result.scalars().all())

    result = await refine_activity(activity, routes, photos)

    return RefineResponse(
        suggestions=[
            RefineSuggestionOut(
                field=s.field,
                current_value=s.current_value,
                suggested_value=s.suggested_value,
            )
            for s in result.suggestions
        ],
        explanation=result.explanation,
    )
