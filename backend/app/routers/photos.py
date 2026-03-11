"""Photo upload, listing, serving, and deletion for activities."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from starlette.responses import FileResponse

from app.config import get_settings
from app.database import get_session
from app.models.activity import Activity
from app.models.photo import ActivityPhoto, ActivityPhotoOut
from app.services.exif import extract_exif

router = APIRouter(tags=["photos"])
settings = get_settings()

_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB per file


def _photo_dir(activity_id: int) -> Path:
    return Path(settings.photo_storage_path) / str(activity_id)


# ── Upload ────────────────────────────────────────────────────────────────────


@router.post(
    "/activities/{activity_id}/photos",
    response_model=list[ActivityPhotoOut],
    status_code=201,
)
async def upload_photos(
    activity_id: int,
    files: list[UploadFile] = File(...),
    session: AsyncSession = Depends(get_session),
):
    """Upload one or more photos for an activity."""
    # Verify activity exists
    activity = await session.get(Activity, activity_id)
    if not activity:
        raise HTTPException(404, "Activity not found")

    created: list[ActivityPhoto] = []

    for upload in files:
        # Validate content type
        if upload.content_type not in _ALLOWED_TYPES:
            raise HTTPException(
                400,
                f"Unsupported file type '{upload.content_type}'. "
                f"Allowed: {', '.join(sorted(_ALLOWED_TYPES))}",
            )

        # Read file bytes
        data = await upload.read()
        if len(data) > _MAX_FILE_SIZE:
            raise HTTPException(400, f"File '{upload.filename}' exceeds 15 MB limit")

        # Generate UUID-based filename
        ext = Path(upload.filename or "photo.jpg").suffix.lower() or ".jpg"
        stored_name = f"{uuid.uuid4().hex}{ext}"

        # Write to disk
        dest_dir = _photo_dir(activity_id)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / stored_name
        dest_path.write_bytes(data)

        # Extract EXIF
        exif = extract_exif(data)

        # Create DB record
        photo = ActivityPhoto(
            activity_id=activity_id,
            filename=stored_name,
            original_name=upload.filename or "photo.jpg",
            content_type=upload.content_type or "image/jpeg",
            size_bytes=len(data),
            exif_lat=exif.lat,
            exif_lon=exif.lon,
            exif_date=exif.date,
        )
        session.add(photo)
        created.append(photo)

    await session.commit()
    for p in created:
        await session.refresh(p)

    return created


# ── List ──────────────────────────────────────────────────────────────────────


@router.get(
    "/activities/{activity_id}/photos",
    response_model=list[ActivityPhotoOut],
)
async def list_photos(
    activity_id: int,
    session: AsyncSession = Depends(get_session),
):
    """List all photos for an activity, ordered by creation time."""
    result = await session.execute(
        select(ActivityPhoto)
        .where(ActivityPhoto.activity_id == activity_id)
        .order_by(ActivityPhoto.created_at)
    )
    return result.scalars().all()


# ── Serve file ────────────────────────────────────────────────────────────────


@router.get("/photos/{photo_id}/file")
async def serve_photo(
    photo_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Serve the actual photo file."""
    photo = await session.get(ActivityPhoto, photo_id)
    if not photo:
        raise HTTPException(404, "Photo not found")

    file_path = _photo_dir(photo.activity_id) / photo.filename
    if not file_path.exists():
        raise HTTPException(404, "Photo file missing from storage")

    return FileResponse(
        path=str(file_path),
        media_type=photo.content_type,
        filename=photo.original_name,
    )


# ── Delete ────────────────────────────────────────────────────────────────────


@router.delete("/photos/{photo_id}", status_code=204)
async def delete_photo(
    photo_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Delete a photo (DB record + file on disk)."""
    photo = await session.get(ActivityPhoto, photo_id)
    if not photo:
        raise HTTPException(404, "Photo not found")

    # Remove file from disk
    file_path = _photo_dir(photo.activity_id) / photo.filename
    file_path.unlink(missing_ok=True)

    # Remove DB record
    await session.delete(photo)
    await session.commit()
