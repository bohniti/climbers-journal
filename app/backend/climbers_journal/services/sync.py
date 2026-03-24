"""Sync service — pull activities from intervals.icu into local DB."""

import asyncio
import logging
from datetime import date, timedelta

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from climbers_journal.models.activity import Activity, ActivitySource, sport_category
from climbers_journal.models.climbing import Crag
from climbers_journal.services import intervals

logger = logging.getLogger(__name__)


def _month_ranges(oldest: date, newest: date) -> list[tuple[date, date]]:
    """Split a date range into month-sized chunks."""
    ranges = []
    cursor = oldest.replace(day=1)
    while cursor <= newest:
        month_end = (cursor + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        chunk_start = max(cursor, oldest)
        chunk_end = min(month_end, newest)
        ranges.append((chunk_start, chunk_end))
        cursor = (cursor + timedelta(days=32)).replace(day=1)
    return ranges


def _parse_activity(raw: dict) -> dict:
    """Extract Activity fields from an intervals.icu activity payload."""
    activity_date = raw.get("start_date_local", raw.get("date", ""))
    if isinstance(activity_date, str) and len(activity_date) >= 10:
        activity_date = activity_date[:10]  # YYYY-MM-DD

    if isinstance(activity_date, str) and activity_date:
        activity_date = date.fromisoformat(activity_date)
    elif isinstance(activity_date, str):
        activity_date = date.today()

    subtype = raw.get("type", "Unknown")
    category = sport_category(subtype)

    return {
        "intervals_id": str(raw["id"]),
        "date": activity_date,
        "type": category,
        "subtype": subtype,
        "name": raw.get("name"),
        "duration_s": int(raw.get("moving_time", raw.get("elapsed_time", 0))),
        "distance_m": raw.get("distance"),
        "elevation_gain_m": raw.get("total_elevation_gain"),
        "avg_hr": raw.get("average_heartrate"),
        "max_hr": raw.get("max_heartrate"),
        "training_load": raw.get("icu_training_load"),
        "intensity": raw.get("icu_intensity"),
        "source": ActivitySource.intervals_icu,
        "raw_data": raw,
    }


async def _fetch_with_retry(oldest: str, newest: str, max_retries: int = 3) -> list[dict]:
    """Fetch activities from intervals.icu with exponential backoff on 429."""
    import httpx

    for attempt in range(max_retries):
        try:
            return await intervals.get_activities(oldest=oldest, newest=newest)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429 and attempt < max_retries - 1:
                delay = 2**attempt  # 1s, 2s, 4s
                logger.warning(
                    "Rate limited (429) fetching %s to %s, retrying in %ds (attempt %d/%d)",
                    oldest, newest, delay, attempt + 1, max_retries,
                )
                await asyncio.sleep(delay)
            else:
                raise


async def upsert_activity(session: AsyncSession, data: dict) -> tuple[Activity, bool]:
    """Insert or update an activity by intervals_id.

    Returns (activity, created) where created is True if newly inserted.
    """
    result = await session.exec(
        select(Activity).where(
            Activity.intervals_id == data["intervals_id"]
        )
    )
    existing = result.first()

    if existing:
        # Update fields on existing record
        for key, value in data.items():
            if key != "intervals_id":
                setattr(existing, key, value)
        session.add(existing)
        return existing, False

    activity = Activity(**data)
    session.add(activity)
    return activity, True


async def sync_activities(
    session: AsyncSession,
    *,
    oldest: date,
    newest: date,
) -> dict:
    """Sync activities from intervals.icu for a date range.

    For ranges > 90 days, fetches month by month with per-chunk commits.
    Returns a structured report of synced/failed months.
    """
    span_days = (newest - oldest).days
    if span_days > 90:
        chunks = _month_ranges(oldest, newest)
    else:
        chunks = [(oldest, newest)]

    synced_months: list[str] = []
    failed_months: list[dict] = []
    total_created = 0
    total_updated = 0

    logger.info("Starting sync: %s to %s (%d chunks)", oldest, newest, len(chunks))

    for chunk_start, chunk_end in chunks:
        month_label = chunk_start.strftime("%Y-%m")
        try:
            raw_activities = await _fetch_with_retry(
                oldest=chunk_start.isoformat(),
                newest=chunk_end.isoformat(),
            )

            chunk_created = 0
            chunk_updated = 0
            for raw in raw_activities:
                if "id" not in raw:
                    continue
                data = _parse_activity(raw)
                activity, created = await upsert_activity(session, data)
                if created:
                    chunk_created += 1
                else:
                    chunk_updated += 1

            await session.commit()
            total_created += chunk_created
            total_updated += chunk_updated
            synced_months.append(month_label)
            logger.info(
                "Synced %s: %d created, %d updated",
                month_label, chunk_created, chunk_updated,
            )

        except Exception as exc:
            await session.rollback()
            error_msg = str(exc)
            failed_months.append({"month": month_label, "error": error_msg})
            logger.error("Failed to sync %s: %s", month_label, error_msg)

    logger.info(
        "Sync complete: %d created, %d updated, %d months synced, %d failed",
        total_created, total_updated, len(synced_months), len(failed_months),
    )

    return {
        "synced": synced_months,
        "failed": failed_months,
        "total_created": total_created,
        "total_updated": total_updated,
    }


async def list_activities(
    session: AsyncSession,
    *,
    activity_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[Activity]:
    """List activities with optional filters and pagination."""
    stmt = select(Activity)
    if activity_type is not None:
        stmt = stmt.where(Activity.type == activity_type)
    if date_from is not None:
        stmt = stmt.where(Activity.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Activity.date <= date_to)
    result = await session.exec(
        stmt.order_by(Activity.date.desc()).offset(offset).limit(limit)  # type: ignore[union-attr]
    )
    return list(result.all())


async def update_activity(
    session: AsyncSession,
    activity_id: int,
    **updates: object,
) -> Activity | None:
    """Update editable fields on any Activity. Returns None if not found.

    When crag_id changes, automatically denormalizes crag_name and cascades
    to ascents for climbing-type activities.
    """
    activity = await session.get(Activity, activity_id)
    if activity is None:
        return None

    # Handle crag_id change: denormalize crag_name + cascade to ascents
    if "crag_id" in updates and updates["crag_id"] != activity.crag_id:
        new_crag_id = updates["crag_id"]
        if new_crag_id is not None:
            crag = await session.get(Crag, new_crag_id)
            if crag is None:
                # Crag not found — skip the entire crag_id update
                del updates["crag_id"]
            else:
                updates["crag_name"] = crag.name
                # Cascade to ascents if this is a climbing activity
                if activity.type == "climbing":
                    from sqlalchemy import text
                    await session.execute(
                        text(
                            "UPDATE ascent SET crag_id = :crag_id, crag_name = :crag_name "
                            "WHERE activity_id = :activity_id"
                        ),
                        {"crag_id": new_crag_id, "crag_name": crag.name, "activity_id": activity_id},
                    )
        else:
            updates["crag_name"] = None

    for key, value in updates.items():
        setattr(activity, key, value)

    session.add(activity)
    await session.flush()
    return activity
