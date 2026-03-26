"""CSV import service for climbing history.

Expected CSV columns:
  date (YYYY-MM-DD, required)
  crag_name (required)
  route_name (optional — omit for indoor gym sessions)
  grade (required)
  tick_type (required — onsight/flash/redpoint/pinkpoint/repeat/attempt/hang)
  area_name (optional)
  venue_type (optional — outdoor_crag or indoor_gym, default outdoor_crag)
  country (optional)
  region (optional)
  style (optional — sport/trad/boulder/multi_pitch/alpine, default sport)
  tries (optional — integer)
  rating (optional — 1-5)
  notes (optional)
  partner (optional)
"""

import csv
import io
from datetime import date

from sqlmodel.ext.asyncio.session import AsyncSession

from climbers_journal.models.climbing import (
    RouteStyle,
    TickType,
    VenueType,
)
from climbers_journal.models.activity import ActivitySource
from climbers_journal.services.activity import (
    create_climbing_activity,
)

REQUIRED_COLUMNS = {"date", "crag_name", "grade", "tick_type"}
OPTIONAL_COLUMNS = {
    "route_name", "area_name", "venue_type", "country", "region",
    "style", "tries", "rating", "notes", "partner",
}
ALL_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS

BATCH_SIZE = 100


def _validate_header(header: list[str]) -> list[str]:
    """Validate CSV header. Returns list of errors (empty = valid)."""
    columns = {col.strip().lower() for col in header}
    missing = REQUIRED_COLUMNS - columns
    if missing:
        return [f"Missing required columns: {', '.join(sorted(missing))}"]
    unknown = columns - ALL_COLUMNS
    if unknown:
        return [f"Unknown columns: {', '.join(sorted(unknown))}"]
    return []


def _validate_row(row: dict, row_num: int) -> tuple[dict | None, str | None]:
    """Validate and parse a single CSV row. Returns (parsed_row, error)."""
    # Required fields
    for col in REQUIRED_COLUMNS:
        if not row.get(col, "").strip():
            return None, f"Row {row_num}: missing required field '{col}'"

    # Date
    try:
        parsed_date = date.fromisoformat(row["date"].strip())
    except ValueError:
        return None, f"Row {row_num}: invalid date '{row['date']}' (expected YYYY-MM-DD)"

    if parsed_date > date.today():
        return None, f"Row {row_num}: date cannot be in the future"

    # Tick type
    tick_type_str = row["tick_type"].strip().lower()
    try:
        TickType(tick_type_str)
    except ValueError:
        valid = ", ".join(t.value for t in TickType)
        return None, f"Row {row_num}: invalid tick_type '{tick_type_str}' (valid: {valid})"

    # Venue type
    venue_type_str = row.get("venue_type", "").strip().lower() or "outdoor_crag"
    try:
        VenueType(venue_type_str)
    except ValueError:
        return None, f"Row {row_num}: invalid venue_type '{venue_type_str}'"

    # Style
    style_str = row.get("style", "").strip().lower() or None
    if style_str:
        try:
            RouteStyle(style_str)
        except ValueError:
            valid = ", ".join(s.value for s in RouteStyle)
            return None, f"Row {row_num}: invalid style '{style_str}' (valid: {valid})"

    # Outdoor crags require route_name
    route_name = row.get("route_name", "").strip() or None
    if venue_type_str == "outdoor_crag" and not route_name:
        return None, f"Row {row_num}: outdoor ascents require route_name"

    # Tries (optional int)
    tries = None
    tries_str = row.get("tries", "").strip()
    if tries_str:
        try:
            tries = int(tries_str)
        except ValueError:
            return None, f"Row {row_num}: invalid tries '{tries_str}' (expected integer)"

    # Rating (optional 1-5)
    rating = None
    rating_str = row.get("rating", "").strip()
    if rating_str:
        try:
            rating = int(rating_str)
            if not 1 <= rating <= 5:
                return None, f"Row {row_num}: rating must be between 1 and 5"
        except ValueError:
            return None, f"Row {row_num}: invalid rating '{rating_str}' (expected 1-5)"

    return {
        "date": parsed_date,
        "crag_name": row["crag_name"].strip(),
        "route_name": route_name,
        "grade": row["grade"].strip(),
        "tick_type": tick_type_str,
        "area_name": row.get("area_name", "").strip() or None,
        "venue_type": venue_type_str,
        "country": row.get("country", "").strip() or None,
        "region": row.get("region", "").strip() or None,
        "style": style_str,
        "tries": tries,
        "rating": rating,
        "notes": row.get("notes", "").strip() or None,
        "partner": row.get("partner", "").strip() or None,
    }, None


async def import_climbing_csv(
    session: AsyncSession,
    file_content: str,
) -> dict:
    """Import climbing ascents from CSV content.

    Groups rows by crag and uses create_climbing_session for each batch.
    Returns import report with created/skipped/error counts.
    """
    reader = csv.DictReader(io.StringIO(file_content))

    if reader.fieldnames is None:
        return {
            "created": 0,
            "skipped": 0,
            "rows_imported": 0,
            "errors": [{"row": 0, "reason": "Empty CSV file or missing header"}],
        }

    # Normalize header
    reader.fieldnames = [f.strip().lower() for f in reader.fieldnames]

    header_errors = _validate_header(reader.fieldnames)
    if header_errors:
        return {
            "created": 0,
            "skipped": 0,
            "rows_imported": 0,
            "errors": [{"row": 0, "reason": e} for e in header_errors],
        }

    # Parse and validate all rows, group by crag
    errors: list[dict] = []
    crag_batches: dict[str, list[dict]] = {}  # crag_name -> rows
    crag_meta: dict[str, dict] = {}  # crag_name -> {country, region, venue_type}
    row_count = 0

    for row_num, row in enumerate(reader, start=2):  # row 1 = header
        row_count += 1
        parsed, error = _validate_row(row, row_num)
        if error:
            errors.append({"row": row_num, "reason": error})
            continue

        crag_key = parsed["crag_name"]
        if crag_key not in crag_batches:
            crag_batches[crag_key] = []
            crag_meta[crag_key] = {
                "country": parsed["country"],
                "region": parsed["region"],
                "venue_type": parsed["venue_type"],
            }

        crag_batches[crag_key].append({
            "route_name": parsed["route_name"],
            "area_name": parsed["area_name"],
            "grade": parsed["grade"],
            "tick_type": parsed["tick_type"],
            "date": parsed["date"],
            "style": parsed["style"],
            "tries": parsed["tries"],
            "rating": parsed["rating"],
            "notes": parsed["notes"],
            "partner": parsed["partner"],
        })

    # Process batches — commit per BATCH_SIZE rows across all crags
    total_created = 0
    total_skipped = 0
    rows_imported = 0

    for crag_name, ascents in crag_batches.items():
        meta = crag_meta[crag_name]

        # Process in batches of BATCH_SIZE
        for i in range(0, len(ascents), BATCH_SIZE):
            batch = ascents[i : i + BATCH_SIZE]
            try:
                result = await create_climbing_activity(
                    session,
                    crag_name=crag_name,
                    crag_country=meta["country"],
                    crag_region=meta["region"],
                    venue_type=VenueType(meta["venue_type"]),
                    ascents_data=batch,
                    source=ActivitySource.csv_import,
                )
                total_created += result["ascents_created"]
                total_skipped += result["ascents_skipped"]
                rows_imported += len(batch)
                await session.commit()
            except Exception as exc:
                await session.rollback()
                errors.append({
                    "row": i + 2,  # approximate row number
                    "reason": f"Batch error for crag '{crag_name}': {exc}",
                })

    return {
        "created": total_created,
        "skipped": total_skipped,
        "rows_imported": rows_imported,
        "errors": errors,
    }
