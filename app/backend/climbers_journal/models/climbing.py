import enum
import unicodedata
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Column, Index, String
from sqlmodel import Field, Relationship, SQLModel


# ── Enums ──────────────────────────────────────────────────────────────


class VenueType(str, enum.Enum):
    outdoor_crag = "outdoor_crag"
    indoor_gym = "indoor_gym"


class GradeSystem(str, enum.Enum):
    french = "french"
    yds = "yds"
    v_scale = "v_scale"
    uiaa = "uiaa"
    font = "font"


class RouteStyle(str, enum.Enum):
    sport = "sport"
    trad = "trad"
    boulder = "boulder"
    multi_pitch = "multi_pitch"
    alpine = "alpine"


class TickType(str, enum.Enum):
    onsight = "onsight"
    flash = "flash"
    redpoint = "redpoint"
    pinkpoint = "pinkpoint"
    repeat = "repeat"
    attempt = "attempt"
    hang = "hang"


# ── Grade system auto-suggestion ───────────────────────────────────────

COUNTRY_GRADE_SYSTEM: dict[str, GradeSystem] = {
    "France": GradeSystem.french,
    "Spain": GradeSystem.french,
    "Italy": GradeSystem.french,
    "Belgium": GradeSystem.french,
    "Greece": GradeSystem.french,
    "Turkey": GradeSystem.french,
    "Portugal": GradeSystem.french,
    "Croatia": GradeSystem.french,
    "Slovenia": GradeSystem.french,
    "Czech Republic": GradeSystem.uiaa,
    "USA": GradeSystem.yds,
    "Canada": GradeSystem.yds,
    "Mexico": GradeSystem.yds,
    "Germany": GradeSystem.uiaa,
    "Austria": GradeSystem.uiaa,
    "Switzerland": GradeSystem.french,
    "UK": GradeSystem.french,
    "Australia": GradeSystem.french,
    "Japan": GradeSystem.french,
    "South Africa": GradeSystem.french,
    "Thailand": GradeSystem.french,
    "China": GradeSystem.french,
    "Norway": GradeSystem.french,
    "Sweden": GradeSystem.french,
    "Finland": GradeSystem.french,
}


def suggest_grade_system(country: str | None) -> GradeSystem:
    """Return the default grade system for a country, defaulting to french."""
    if country is None:
        return GradeSystem.french
    return COUNTRY_GRADE_SYSTEM.get(country, GradeSystem.french)


# ── Helpers ────────────────────────────────────────────────────────────


def normalize_name(name: str) -> str:
    """Lowercase, strip, and remove diacritics for case-insensitive matching."""
    name = name.strip().lower()
    # Decompose unicode, remove combining marks (diacritics)
    nfkd = unicodedata.normalize("NFKD", name)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# ── Models ─────────────────────────────────────────────────────────────


class Crag(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    name_normalized: str = Field(
        sa_column=Column(String, index=True),
    )
    country: str | None = None
    region: str | None = None
    venue_type: VenueType = Field(default=VenueType.outdoor_crag)
    default_grade_sys: GradeSystem = Field(default=GradeSystem.french)
    latitude: float | None = None
    longitude: float | None = None
    description: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    areas: list["Area"] = Relationship(back_populates="crag")
    routes: list["Route"] = Relationship(back_populates="crag")
    ascents: list["Ascent"] = Relationship(back_populates="crag")
    sessions: list["ClimbingSession"] = Relationship(back_populates="crag")


class Area(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    name_normalized: str = Field(
        sa_column=Column(String, index=True),
    )
    description: str | None = None
    crag_id: int = Field(foreign_key="crag.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    crag: Crag | None = Relationship(back_populates="areas")
    routes: list["Route"] = Relationship(back_populates="area")


class Route(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    name_normalized: str = Field(
        sa_column=Column(String, index=True),
    )
    grade: str  # raw string: "8a", "5.12a", "V10"
    grade_system: GradeSystem = Field(default=GradeSystem.french)
    style: RouteStyle = Field(default=RouteStyle.sport)
    pitches: int = Field(default=1)
    height_m: int | None = None
    description: str | None = None
    crag_id: int = Field(foreign_key="crag.id")
    area_id: int | None = Field(default=None, foreign_key="area.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    crag: Crag | None = Relationship(back_populates="routes")
    area: Area | None = Relationship(back_populates="routes")
    ascents: list["Ascent"] = Relationship(back_populates="route")


class ClimbingSession(SQLModel, table=True):
    __tablename__ = "climbing_session"
    __table_args__ = (
        Index("ix_session_date", "date"),
        Index("ix_session_crag_id", "crag_id"),
        Index("uq_session_date_crag", "date", "crag_id", unique=True),
    )

    id: int | None = Field(default=None, primary_key=True)
    date: date
    crag_id: int = Field(foreign_key="crag.id")
    crag_name: str | None = None  # denormalized
    notes: str | None = None
    linked_activity_id: int | None = Field(
        default=None, foreign_key="endurance_activity.id"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    crag: Crag | None = Relationship(back_populates="sessions")
    ascents: list["Ascent"] = Relationship(back_populates="session")
    linked_activity: Optional["EnduranceActivity"] = Relationship()


class Ascent(SQLModel, table=True):
    __table_args__ = (
        Index("ix_ascent_crag_tick_date", "crag_id", "tick_type", "date"),
        Index("ix_ascent_session_id", "session_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    date: date
    tick_type: TickType
    tries: int | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = None
    partner: str | None = None
    route_id: int | None = Field(default=None, foreign_key="route.id")
    crag_id: int = Field(foreign_key="crag.id")
    session_id: int | None = Field(default=None, foreign_key="climbing_session.id")
    # Denormalized for read performance
    crag_name: str | None = None
    route_name: str | None = None
    grade: str | None = None  # override for gym ascents without route
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    route: Route | None = Relationship(back_populates="ascents")
    crag: Crag | None = Relationship(back_populates="ascents")
    session: ClimbingSession | None = Relationship(back_populates="ascents")
