"""Endurance activity model — synced from intervals.icu."""

import enum
from datetime import UTC, date, datetime

from sqlalchemy import Column, Index
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class ActivitySource(str, enum.Enum):
    intervals_icu = "intervals_icu"
    manual = "manual"


class EnduranceActivity(SQLModel, table=True):
    __tablename__ = "endurance_activity"
    __table_args__ = (
        Index("ix_endurance_activity_date", "date"),
        Index("ix_endurance_activity_intervals_id", "intervals_id", unique=True),
    )

    id: int | None = Field(default=None, primary_key=True)
    intervals_id: str = Field(index=False)  # unique ID from intervals.icu (index via __table_args__)
    date: date
    type: str  # e.g. "Run", "Ride", "Hike", "TrailRun"
    name: str | None = None
    duration_s: int
    distance_m: float | None = None
    elevation_gain_m: float | None = None
    avg_hr: int | None = None
    max_hr: int | None = None
    training_load: float | None = None  # icu_training_load
    intensity: float | None = None  # icu_intensity
    source: ActivitySource = Field(
        sa_column=Column(
            SAEnum(ActivitySource, name="activitysource"),
            nullable=False,
            default=ActivitySource.intervals_icu,
        )
    )
    raw_data: dict | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))
