from typing import Optional
from datetime import datetime
from enum import Enum
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import JSON


class ActivityType(str, Enum):
    bouldering = "bouldering"
    sport_climb = "sport_climb"
    multi_pitch = "multi_pitch"
    cycling = "cycling"
    hiking = "hiking"
    fitness = "fitness"
    other = "other"


class ActivitySource(str, Enum):
    manual = "manual"
    chat_cli = "chat_cli"
    garmin = "garmin"
    intervals_icu = "intervals_icu"


class GradeSystem(str, Enum):
    yds = "yds"
    french = "french"
    font = "font"
    uiaa = "uiaa"
    ice_wis = "ice_wis"
    alpine = "alpine"
    vscale = "vscale"


class ClimbStyle(str, Enum):
    onsight = "onsight"
    flash = "flash"
    redpoint = "redpoint"
    top_rope = "top_rope"
    attempt = "attempt"
    aid = "aid"
    solo = "solo"


# ─── Table model ──────────────────────────────────────────────────────────────

class Activity(SQLModel, table=True):
    __tablename__ = "activities"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Core fields
    activity_type: ActivityType
    title: str
    date: datetime
    duration_minutes: Optional[int] = None
    distance_km: Optional[float] = None
    elevation_gain_m: Optional[float] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    location_name: Optional[str] = None
    notes: Optional[str] = None
    source: ActivitySource = Field(default=ActivitySource.manual)
    raw_json: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Tags: sub-categories stored as a JSON array of strings
    # e.g. ["indoor"], ["outdoor", "trad"], ["commute"], ["trail_run"]
    tags: list = Field(default_factory=list, sa_column=Column(JSON))

    # Session-level climbing fields (area, partner, region apply to whole session)
    area: Optional[str] = None      # specific crag/gym name, e.g. "Hexenküche"
    region: Optional[str] = None    # broader grouping for filtering, e.g. "Fränkische Schweiz", "Kletterhalle Wien"
    partner: Optional[str] = None

    # Garmin / intervals.icu linkage
    intervals_activity_id: Optional[str] = None

    # Endurance metrics (from Garmin via intervals.icu)
    avg_heart_rate: Optional[int] = None   # bpm
    calories: Optional[int] = None        # kcal


# ─── Pydantic request/response models ─────────────────────────────────────────

class ActivityCreate(SQLModel):
    activity_type: ActivityType
    title: str
    date: datetime
    duration_minutes: Optional[int] = None
    distance_km: Optional[float] = None
    elevation_gain_m: Optional[float] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    location_name: Optional[str] = None
    notes: Optional[str] = None
    source: ActivitySource = ActivitySource.manual
    tags: list[str] = []
    area: Optional[str] = None
    region: Optional[str] = None
    partner: Optional[str] = None
    intervals_activity_id: Optional[str] = None
    avg_heart_rate: Optional[int] = None
    calories: Optional[int] = None
    # Optional routes for chat confirmation flow — saved automatically on create
    routes: Optional[list[dict]] = None


class ActivityUpdate(SQLModel):
    activity_type: Optional[ActivityType] = None
    title: Optional[str] = None
    date: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    distance_km: Optional[float] = None
    elevation_gain_m: Optional[float] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    location_name: Optional[str] = None
    notes: Optional[str] = None
    source: Optional[ActivitySource] = None
    tags: Optional[list[str]] = None
    area: Optional[str] = None
    region: Optional[str] = None
    partner: Optional[str] = None
    intervals_activity_id: Optional[str] = None
    avg_heart_rate: Optional[int] = None
    calories: Optional[int] = None


class ActivityOut(SQLModel):
    id: int
    created_at: datetime
    updated_at: datetime
    activity_type: ActivityType
    title: str
    date: datetime
    duration_minutes: Optional[int] = None
    distance_km: Optional[float] = None
    elevation_gain_m: Optional[float] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    location_name: Optional[str] = None
    notes: Optional[str] = None
    source: ActivitySource
    tags: list[str] = []
    area: Optional[str] = None
    region: Optional[str] = None
    partner: Optional[str] = None
    intervals_activity_id: Optional[str] = None
    avg_heart_rate: Optional[int] = None
    calories: Optional[int] = None
