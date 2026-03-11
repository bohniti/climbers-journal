"""Extract GPS coordinates and date from JPEG/TIFF EXIF metadata using Pillow."""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS

log = logging.getLogger(__name__)


@dataclass
class ExifData:
    lat: Optional[float] = None
    lon: Optional[float] = None
    date: Optional[datetime] = None


def _dms_to_decimal(dms: tuple, ref: str) -> float:
    """Convert GPS DMS (degrees, minutes, seconds) to decimal degrees."""
    degrees, minutes, seconds = dms
    decimal = float(degrees) + float(minutes) / 60 + float(seconds) / 3600
    if ref in ("S", "W"):
        decimal = -decimal
    return round(decimal, 7)


def _get_gps_info(exif_data: dict) -> tuple[Optional[float], Optional[float]]:
    """Extract lat/lon from EXIF GPS info."""
    gps_info_raw = exif_data.get("GPSInfo")
    if not gps_info_raw:
        return None, None

    # Resolve GPS tag IDs to names
    gps_info: dict = {}
    for key, val in gps_info_raw.items():
        tag_name = GPSTAGS.get(key, key)
        gps_info[tag_name] = val

    lat_dms = gps_info.get("GPSLatitude")
    lat_ref = gps_info.get("GPSLatitudeRef")
    lon_dms = gps_info.get("GPSLongitude")
    lon_ref = gps_info.get("GPSLongitudeRef")

    if not (lat_dms and lat_ref and lon_dms and lon_ref):
        return None, None

    try:
        lat = _dms_to_decimal(lat_dms, lat_ref)
        lon = _dms_to_decimal(lon_dms, lon_ref)
        # Basic sanity check
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        log.debug("Failed to parse GPS DMS: %s", exc)

    return None, None


def _get_date(exif_data: dict) -> Optional[datetime]:
    """Extract DateTimeOriginal from EXIF."""
    for tag_name in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
        raw = exif_data.get(tag_name)
        if raw:
            try:
                return datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S")
            except ValueError:
                continue
    return None


def extract_exif(file_bytes: bytes) -> ExifData:
    """Extract GPS lat/lon and date from image EXIF data.

    Returns ExifData with whatever could be extracted; fields are None if
    the image has no EXIF, or the relevant tags are missing/corrupt.
    """
    try:
        img = Image.open(io.BytesIO(file_bytes))
        raw_exif = img._getexif()  # noqa: SLF001
        if not raw_exif:
            return ExifData()

        # Resolve numeric tag IDs → human-readable names
        exif_data: dict = {}
        for tag_id, value in raw_exif.items():
            tag_name = TAGS.get(tag_id, tag_id)
            exif_data[tag_name] = value

        lat, lon = _get_gps_info(exif_data)
        date = _get_date(exif_data)
        return ExifData(lat=lat, lon=lon, date=date)

    except Exception as exc:
        log.debug("EXIF extraction failed: %s", exc)
        return ExifData()
