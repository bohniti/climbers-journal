"""AI-powered activity refinement using LLM + Mapy.com geocoding tools."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from app.config import get_settings
from app.models.activity import Activity
from app.models.photo import ActivityPhoto
from app.models.route import SessionRoute
from app.services.llm import get_client
from app.services.mapy import geocode, reverse_geocode

log = logging.getLogger(__name__)
settings = get_settings()


# ── Result types ──────────────────────────────────────────────────────────────


@dataclass
class RefineSuggestion:
    field: str
    current_value: Any
    suggested_value: Any


@dataclass
class RefineResult:
    suggestions: list[RefineSuggestion] = field(default_factory=list)
    explanation: str = ""


# ── System prompt ─────────────────────────────────────────────────────────────

REFINE_SYSTEM = """\
You are a climbing journal data refinement assistant. You receive an activity \
record with its routes and photo metadata. Your job is to suggest improvements \
to make the data more accurate and complete.

## What you can improve
- **title** — make it more descriptive (include crag name, style, key route)
- **area** — the specific crag, gym, or trailhead name
- **region** — broader region for filtering (e.g. "Fränkische Schweiz", "Wien", \
"Kalymnos", "Cala Gonone")
- **lat / lon** — correct coordinates based on photo GPS or geocoding
- **notes** — suggest additions based on available data (keep existing notes)

## Rules
- Only suggest changes you are confident about.
- Use the `geocode` tool to verify or look up place names.
- Use the `reverse_geocode` tool when you have GPS coordinates from photos.
- If photo EXIF has GPS coordinates, those are highly reliable — trust them.
- When you have gathered enough information, call `suggest_refinements` with \
  your final suggestions. Only include fields you actually want to change.
- Keep suggestions concise and factual.
"""

# ── LLM tool definitions ─────────────────────────────────────────────────────

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "geocode",
            "description": (
                "Forward geocode a place name to get coordinates and regional "
                "structure. Use this to verify crag/area names and get accurate "
                "coordinates."
            ),
            "parameters": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Place name to geocode, e.g. "
                            "'Biddiriscottai Cala Gonone Sardinia'"
                        ),
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reverse_geocode",
            "description": (
                "Reverse geocode coordinates to get place name and regional "
                "structure. Use when you have GPS coordinates from photos."
            ),
            "parameters": {
                "type": "object",
                "required": ["lat", "lon"],
                "properties": {
                    "lat": {"type": "number"},
                    "lon": {"type": "number"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_refinements",
            "description": (
                "Submit your suggested refinements for this activity. "
                "Only include fields you want to change."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "area": {"type": "string"},
                    "region": {"type": "string"},
                    "lat": {"type": "number"},
                    "lon": {"type": "number"},
                    "notes": {"type": "string"},
                    "explanation": {
                        "type": "string",
                        "description": (
                            "Brief explanation of why you're suggesting these changes."
                        ),
                    },
                },
            },
        },
    },
]


# ── Tool executors ────────────────────────────────────────────────────────────


async def _exec_geocode(args: dict) -> str:
    query = args.get("query", "")
    results = await geocode(query, limit=3)
    if not results:
        return json.dumps({"results": [], "note": f"No results for '{query}'"})
    return json.dumps(
        {
            "results": [
                {
                    "name": r.name,
                    "label": r.label,
                    "lat": r.lat,
                    "lon": r.lon,
                    "location": r.location,
                    "type": r.type,
                    "regional_structure": r.regional_structure,
                }
                for r in results
            ]
        }
    )


async def _exec_reverse_geocode(args: dict) -> str:
    lat = args.get("lat", 0)
    lon = args.get("lon", 0)
    results = await reverse_geocode(lat, lon)
    if not results:
        return json.dumps({"results": [], "note": "No results for coordinates"})
    return json.dumps(
        {
            "results": [
                {
                    "name": r.name,
                    "location": r.location,
                    "regional_structure": r.regional_structure,
                }
                for r in results
            ]
        }
    )


# ── Build user message ───────────────────────────────────────────────────────


def _build_user_message(
    activity: Activity,
    routes: list[SessionRoute],
    photos: list[ActivityPhoto],
    pre_geocode: list[dict] | None = None,
) -> str:
    """Build a detailed user message with all available data for the LLM."""
    parts = ["# Activity to refine\n"]

    # Activity fields
    parts.append(f"- **Title**: {activity.title or '(none)'}")
    parts.append(f"- **Type**: {activity.activity_type}")
    parts.append(f"- **Date**: {activity.date}")
    parts.append(f"- **Area**: {activity.area or '(none)'}")
    parts.append(f"- **Region**: {activity.region or '(none)'}")
    parts.append(f"- **Lat/Lon**: {activity.lat}, {activity.lon}")
    if activity.notes:
        parts.append(f"- **Notes**: {activity.notes}")
    if activity.tags:
        parts.append(f"- **Tags**: {activity.tags}")
    if activity.partner:
        parts.append(f"- **Partner**: {activity.partner}")

    # Routes
    if routes:
        parts.append(f"\n## Routes ({len(routes)} routes)")
        for i, r in enumerate(routes, 1):
            line = f"{i}. {r.route_name or '(unnamed)'}"
            if r.grade:
                line += f" ({r.grade})"
            if r.style:
                line += f" — {r.style}"
            if r.sector:
                line += f" [sector: {r.sector}]"
            parts.append(line)

    # Photos with EXIF
    photos_with_gps = [p for p in photos if p.exif_lat and p.exif_lon]
    photos_with_date = [p for p in photos if p.exif_date]
    if photos:
        parts.append(f"\n## Photos ({len(photos)} photos)")
        if photos_with_gps:
            parts.append("Photos with GPS coordinates:")
            for p in photos_with_gps:
                parts.append(f"- {p.original_name}: lat={p.exif_lat}, lon={p.exif_lon}")
        if photos_with_date:
            parts.append("Photos with dates:")
            for p in photos_with_date:
                parts.append(f"- {p.original_name}: {p.exif_date}")

    # Pre-enriched geocode data
    if pre_geocode:
        parts.append("\n## Pre-resolved GPS locations (from photo EXIF)")
        for geo in pre_geocode:
            parts.append(
                f"- Coords ({geo['lat']}, {geo['lon']}) → "
                f"{geo['location']} — {geo['regional_structure']}"
            )

    return "\n".join(parts)


# ── Main refinement function ─────────────────────────────────────────────────


async def refine_activity(
    activity: Activity,
    routes: list[SessionRoute],
    photos: list[ActivityPhoto],
) -> RefineResult:
    """Send activity data to LLM and get refinement suggestions."""

    # Pre-enrich: reverse geocode photo GPS coords for context
    pre_geocode: list[dict] = []
    seen_coords: set[tuple[float, float]] = set()
    for p in photos:
        if p.exif_lat and p.exif_lon:
            coord_key = (round(p.exif_lat, 4), round(p.exif_lon, 4))
            if coord_key in seen_coords:
                continue
            seen_coords.add(coord_key)
            try:
                results = await reverse_geocode(p.exif_lat, p.exif_lon)
                if results:
                    r = results[0]
                    pre_geocode.append(
                        {
                            "lat": p.exif_lat,
                            "lon": p.exif_lon,
                            "location": r.location,
                            "regional_structure": [
                                rs.get("name", "") for rs in r.regional_structure
                            ],
                        }
                    )
            except Exception as exc:
                log.debug("Pre-geocode failed for (%s, %s): %s", p.exif_lat, p.exif_lon, exc)

    user_msg = _build_user_message(activity, routes, photos, pre_geocode)
    messages = [
        {"role": "system", "content": REFINE_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    client = get_client()

    # Tool execution loop — max 6 rounds
    for _ in range(6):
        response = await client.chat.completions.create(
            model=settings.nvidia_model,
            messages=messages,
            tools=_TOOLS,
            tool_choice="auto",
            max_tokens=2048,
            temperature=0.2,
        )

        msg = response.choices[0].message

        if not msg.tool_calls:
            # No tool calls — LLM returned text, use it as explanation
            return RefineResult(explanation=msg.content or "No suggestions.")

        messages.append(msg.model_dump(exclude_none=True))

        for tc in msg.tool_calls:
            fn = tc.function.name
            args = json.loads(tc.function.arguments)

            if fn == "geocode":
                result_str = await _exec_geocode(args)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_str})

            elif fn == "reverse_geocode":
                result_str = await _exec_reverse_geocode(args)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_str})

            elif fn == "suggest_refinements":
                # This is the final output — parse suggestions
                explanation = args.pop("explanation", "")
                messages.append(
                    {"role": "tool", "tool_call_id": tc.id, "content": json.dumps({"status": "ok"})}
                )

                suggestions = []
                field_map = {
                    "title": activity.title,
                    "area": activity.area,
                    "region": activity.region,
                    "lat": activity.lat,
                    "lon": activity.lon,
                    "notes": activity.notes,
                }

                for field_name, suggested_value in args.items():
                    current = field_map.get(field_name)
                    # Only include if the value actually changes
                    if str(suggested_value) != str(current):
                        suggestions.append(
                            RefineSuggestion(
                                field=field_name,
                                current_value=current,
                                suggested_value=suggested_value,
                            )
                        )

                return RefineResult(suggestions=suggestions, explanation=explanation)

    return RefineResult(explanation="Refinement timed out after too many tool calls.")
