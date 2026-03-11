from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class ActivityPhoto(SQLModel, table=True):
    """A photo attached to an activity. Stores metadata; the file lives on disk."""

    __tablename__ = "activity_photos"

    id: Optional[int] = Field(default=None, primary_key=True)
    activity_id: int = Field(foreign_key="activities.id", index=True)
    filename: str  # UUID-based stored name, e.g. "a1b2c3d4.jpg"
    original_name: str  # user's original filename
    content_type: str  # e.g. "image/jpeg"
    size_bytes: int
    exif_lat: Optional[float] = None
    exif_lon: Optional[float] = None
    exif_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Pydantic schemas ─────────────────────────────────────────────────────────


class ActivityPhotoOut(SQLModel):
    id: int
    activity_id: int
    filename: str
    original_name: str
    content_type: str
    size_bytes: int
    exif_lat: Optional[float] = None
    exif_lon: Optional[float] = None
    exif_date: Optional[datetime] = None
    created_at: datetime
