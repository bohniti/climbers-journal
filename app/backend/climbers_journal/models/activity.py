"""Unified Activity model — replaces EnduranceActivity + ClimbingSession."""

import enum
import logging
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, Index
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from climbers_journal.models.climbing import Ascent, Crag

logger = logging.getLogger(__name__)

# ── Subtype → category mapping (mirrors frontend sportCategory()) ────

_SUBTYPE_CATEGORY: dict[str, str] = {
    # Running
    "Run": "run",
    "TrailRun": "run",
    "VirtualRun": "run",
    # Cycling
    "Ride": "ride",
    "GravelRide": "ride",
    "MountainBikeRide": "ride",
    "EBikeRide": "ride",
    "EMountainBikeRide": "ride",
    "VirtualRide": "ride",
    "Velomobile": "ride",
    "Handcycle": "ride",
    # Swimming
    "Swim": "swim",
    # Winter
    "AlpineSki": "winter",
    "BackcountrySki": "winter",
    "NordicSki": "winter",
    "Snowboard": "winter",
    "Snowshoe": "winter",
    "IceSkate": "winter",
    # Climbing
    "RockClimbing": "climbing",
    # Water
    "Canoeing": "water",
    "Kayaking": "water",
    "Rowing": "water",
    "VirtualRow": "water",
    "StandUpPaddling": "water",
    "Surfing": "water",
    "Kitesurf": "water",
    "Windsurf": "water",
    "Sail": "water",
    # Fitness
    "Hike": "fitness",
    "Walk": "fitness",
    "Yoga": "fitness",
    "Pilates": "fitness",
    "WeightTraining": "fitness",
    "Crossfit": "fitness",
    "HighIntensityIntervalTraining": "fitness",
    "Elliptical": "fitness",
    "StairStepper": "fitness",
    "Workout": "fitness",
    # Other
    "Badminton": "other",
    "Golf": "other",
    "InlineSkate": "other",
    "Pickleball": "other",
    "Racquetball": "other",
    "RollerSki": "other",
    "Skateboard": "other",
    "Soccer": "other",
    "Squash": "other",
    "TableTennis": "other",
    "Tennis": "other",
    "Wheelchair": "other",
}


def sport_category(subtype: str) -> str:
    """Map a Strava subtype string to its type category.

    Mirrors the frontend ``sportCategory()`` in constants.ts.
    Returns ``"other"`` for unknown subtypes.
    """
    cat = _SUBTYPE_CATEGORY.get(subtype)
    if cat is None:
        logger.warning("Unknown sport subtype: %r, mapping to 'other'", subtype)
        return "other"
    return cat


# ── Enums ─────────────────────────────────────────────────────────────


class ActivitySource(str, enum.Enum):
    intervals_icu = "intervals_icu"
    manual = "manual"
    csv_import = "csv_import"


# ── Model ─────────────────────────────────────────────────────────────


class Activity(SQLModel, table=True):
    __table_args__ = (
        Index("ix_activity_date", "date"),
        Index("ix_activity_type", "type"),
        Index("ix_activity_intervals_id", "intervals_id", unique=True),
        Index("ix_activity_crag_id", "crag_id"),
        Index("uq_activity_date_crag", "date", "crag_id", unique=True),
    )

    id: int | None = Field(default=None, primary_key=True)
    date: date
    type: str  # category: "climbing", "run", "ride", "fitness", etc.
    subtype: str | None = None  # Strava type: "RockClimbing", "TrailRun", etc.
    name: str | None = None
    notes: str | None = None
    source: ActivitySource = Field(
        sa_column=Column(
            SAEnum(ActivitySource, name="activitysource"),
            nullable=False,
            default=ActivitySource.manual,
        )
    )
    intervals_id: str | None = Field(default=None)  # unique via index
    duration_s: int | None = None
    distance_m: float | None = None
    elevation_gain_m: float | None = None
    avg_hr: int | None = None
    max_hr: int | None = None
    training_load: float | None = None
    intensity: float | None = None
    crag_id: int | None = Field(default=None, foreign_key="crag.id")
    crag_name: str | None = None  # denormalized
    raw_data: dict | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )

    # Relationships
    ascents: list["Ascent"] = Relationship(back_populates="activity")
    crag: Optional["Crag"] = Relationship(back_populates="activities")
