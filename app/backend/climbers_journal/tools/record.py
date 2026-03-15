"""Climbing session record tool — parses natural language into structured drafts."""

from __future__ import annotations

import json
from typing import Any

from sqlmodel.ext.asyncio.session import AsyncSession

from climbers_journal.models.climbing import normalize_name, suggest_grade_system
from climbers_journal.services.climbing import find_crag_by_name, list_routes

definitions: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "parse_climbing_session",
            "description": (
                "Parse a climbing session description into a structured draft for the user to review. "
                "Call this tool when the user describes routes they climbed, attempted, or worked on. "
                "The draft will be shown as an editable card for the user to confirm or modify before saving. "
                "Do NOT call this for questions about climbing history — only for logging new sessions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "crag_name": {
                        "type": "string",
                        "description": "Name of the crag or gym (e.g. 'Frankenjura', 'Boulderhalle Wien').",
                    },
                    "crag_country": {
                        "type": "string",
                        "description": "Country of the crag (e.g. 'Germany', 'Austria'). Used for grade system auto-suggestion.",
                    },
                    "venue_type": {
                        "type": "string",
                        "enum": ["outdoor_crag", "indoor_gym"],
                        "description": "Whether this is an outdoor crag or indoor gym. Default: outdoor_crag.",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date of the session in YYYY-MM-DD format. Use today's date if not specified.",
                    },
                    "ascents": {
                        "type": "array",
                        "description": "List of ascents (routes climbed, attempted, etc.).",
                        "items": {
                            "type": "object",
                            "properties": {
                                "route_name": {
                                    "type": "string",
                                    "description": "Name of the route. Omit for unnamed gym problems.",
                                },
                                "grade": {
                                    "type": "string",
                                    "description": "Grade as a raw string (e.g. '8a', '5.12a', 'V10', '7+').",
                                },
                                "tick_type": {
                                    "type": "string",
                                    "enum": [
                                        "onsight",
                                        "flash",
                                        "redpoint",
                                        "pinkpoint",
                                        "repeat",
                                        "attempt",
                                        "hang",
                                    ],
                                    "description": "How the route was climbed.",
                                },
                                "tries": {
                                    "type": "integer",
                                    "description": "Number of attempts in this session.",
                                },
                                "notes": {
                                    "type": "string",
                                    "description": "Any notes about the ascent.",
                                },
                                "style": {
                                    "type": "string",
                                    "enum": [
                                        "sport",
                                        "trad",
                                        "boulder",
                                        "multi_pitch",
                                        "alpine",
                                    ],
                                    "description": "Climbing style. Default: sport.",
                                },
                            },
                            "required": ["tick_type"],
                        },
                    },
                },
                "required": ["crag_name", "ascents"],
            },
        },
    },
]


async def _build_draft(arguments: dict[str, Any], session: AsyncSession | None) -> dict[str, Any]:
    """Build a draft card from the parsed arguments, enriching with DB lookups."""
    crag_name = arguments["crag_name"]
    crag_country = arguments.get("crag_country")
    venue_type = arguments.get("venue_type", "outdoor_crag")
    session_date = arguments.get("date")

    # Look up existing crag
    crag_status = "new"
    crag_id = None
    if session:
        existing_crag = await find_crag_by_name(session, crag_name)
        if existing_crag:
            crag_status = "existing"
            crag_id = existing_crag.id
            # Use existing crag's country if not provided
            if not crag_country and existing_crag.country:
                crag_country = existing_crag.country

    grade_system = suggest_grade_system(crag_country).value if crag_country else "french"

    # Build existing route index for matching
    existing_routes: dict[str, dict] = {}
    if session and crag_id is not None:
        routes = await list_routes(session, crag_id=crag_id, limit=200)
        for r in routes:
            existing_routes[normalize_name(r.name)] = {
                "id": r.id,
                "name": r.name,
                "grade": r.grade,
            }

    # Build ascent drafts
    ascent_drafts = []
    for a in arguments.get("ascents", []):
        draft: dict[str, Any] = {
            "tick_type": a["tick_type"],
            "tries": a.get("tries"),
            "notes": a.get("notes"),
            "style": a.get("style", "sport"),
        }

        route_name = a.get("route_name")
        if route_name:
            draft["route_name"] = route_name
            normalized = normalize_name(route_name)
            match = existing_routes.get(normalized)
            if match:
                draft["route_status"] = "existing"
                draft["route_id"] = match["id"]
                # Use existing grade if not provided
                draft["grade"] = a.get("grade") or match["grade"]
            else:
                draft["route_status"] = "new"
                draft["grade"] = a.get("grade")
        else:
            draft["grade"] = a.get("grade")

        ascent_drafts.append(draft)

    return {
        "type": "climbing_session",
        "crag": {
            "name": crag_name,
            "country": crag_country,
            "venue_type": venue_type,
            "status": crag_status,
            "grade_system": grade_system,
        },
        "date": session_date,
        "ascents": ascent_drafts,
    }


async def handle(tool_name: str, arguments: dict[str, Any], context: dict[str, Any]) -> str | None:
    """Handle a tool call. Returns None if the tool name is not ours."""
    if tool_name != "parse_climbing_session":
        return None

    db_session = context.get("db_session")
    draft = await _build_draft(arguments, db_session)

    # Store draft_card on context so the chat endpoint can surface it
    context["draft_card"] = draft

    # Return a text summary for the LLM to incorporate in its reply
    crag = draft["crag"]
    n_ascents = len(draft["ascents"])
    status_note = f" ({crag['status']})" if crag.get("status") else ""
    summary = (
        f"Draft created for {n_ascents} ascent(s) at {crag['name']}{status_note}. "
        "The draft card is shown to the user for review. "
        "Tell the user to review the draft and confirm or edit it."
    )
    return json.dumps({"summary": summary, "draft": draft}, default=str)
