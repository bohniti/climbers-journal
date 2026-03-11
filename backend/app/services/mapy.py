"""Mapy.com REST API client for geocoding and reverse geocoding."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import httpx

from app.config import get_settings

log = logging.getLogger(__name__)

_BASE = "https://api.mapy.com/v1"


@dataclass
class GeoResult:
    name: str
    label: str
    lat: float
    lon: float
    type: str
    location: str
    regional_structure: list[dict] = field(default_factory=list)


def _parse_items(data: dict) -> list[GeoResult]:
    results: list[GeoResult] = []
    for item in data.get("items", []):
        pos = item.get("position", {})
        results.append(
            GeoResult(
                name=item.get("name", ""),
                label=item.get("label", ""),
                lat=pos.get("lat", 0),
                lon=pos.get("lon", 0),
                type=item.get("type", ""),
                location=item.get("location", ""),
                regional_structure=item.get("regionalStructure", []),
            )
        )
    return results


async def geocode(query: str, limit: int = 5) -> list[GeoResult]:
    """Forward geocode: place name → coordinates + regional structure."""
    settings = get_settings()
    if not settings.mapy_api_key:
        log.warning("MAPY_API_KEY not configured — geocode skipped")
        return []

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{_BASE}/geocode",
            params={
                "query": query,
                "lang": "en",
                "limit": limit,
                "apikey": settings.mapy_api_key,
            },
        )
        resp.raise_for_status()
        return _parse_items(resp.json())


async def reverse_geocode(lat: float, lon: float) -> list[GeoResult]:
    """Reverse geocode: coordinates → place name + regional structure."""
    settings = get_settings()
    if not settings.mapy_api_key:
        log.warning("MAPY_API_KEY not configured — reverse_geocode skipped")
        return []

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{_BASE}/rgeocode",
            params={
                "lat": lat,
                "lon": lon,
                "lang": "en",
                "apikey": settings.mapy_api_key,
            },
        )
        resp.raise_for_status()
        return _parse_items(resp.json())
