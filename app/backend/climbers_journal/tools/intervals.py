"""intervals.icu tool definitions and handlers."""

from __future__ import annotations

import json
from typing import Any

import httpx

from climbers_journal.services import intervals

definitions: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_latest_activity",
            "description": "Get the most recent activity from intervals.icu with full details (type, duration, distance, power, HR, etc.).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_activities",
            "description": "Get recent activities from intervals.icu. Returns a list of activity summaries for a date range (defaults to last 30 days).",
            "parameters": {
                "type": "object",
                "properties": {
                    "oldest": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format (defaults to 30 days ago).",
                    },
                    "newest": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format (defaults to today).",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_wellness",
            "description": "Get wellness data (CTL/fitness, ATL/fatigue, ramp rate, HRV, sleep, etc.) from intervals.icu for a date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "oldest": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format.",
                    },
                    "newest": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format.",
                    },
                },
                "required": [],
            },
        },
    },
]


async def handle(tool_name: str, arguments: dict[str, Any]) -> str | None:
    """Handle a tool call. Returns None if the tool name is not ours."""
    try:
        if tool_name == "get_latest_activity":
            result = await intervals.get_latest_activity()
            return json.dumps(result, default=str)

        if tool_name == "get_activities":
            result = await intervals.get_activities(
                oldest=arguments.get("oldest"),
                newest=arguments.get("newest"),
            )
            return json.dumps(result, default=str)

        if tool_name == "get_wellness":
            result = await intervals.get_wellness(
                oldest=arguments.get("oldest"),
                newest=arguments.get("newest"),
            )
            return json.dumps(result, default=str)

    except httpx.HTTPStatusError as exc:
        return json.dumps({
            "error": f"intervals.icu API error: {exc.response.status_code}",
            "detail": exc.response.text,
        })

    return None
