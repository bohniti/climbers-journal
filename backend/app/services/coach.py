"""Unified coach service — combines activity logging, find/edit, and weekly summaries."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable, Optional

from app.config import get_settings
from app.services.llm import get_client, _execute_search_intervals, _execute_search_web

log = logging.getLogger(__name__)
settings = get_settings()


# ─── Result types ─────────────────────────────────────────────────────────────


@dataclass
class PendingUpdate:
    activity_id: int
    changes: dict[str, Any]
    current_values: dict[str, Any]


@dataclass
class CoachResult:
    reply: str
    pending_activity: Optional[dict] = None
    needs_confirmation: bool = False
    pending_update: Optional[PendingUpdate] = None
    found_activities: Optional[list[dict]] = None


# ─── System prompt ────────────────────────────────────────────────────────────

COACH_SYSTEM = """You are a personal climbing & outdoor activities coach assistant. You help the user with three main tasks — automatically detect which one applies based on the conversation:

## 1. LOG a new activity
When the user describes a new activity (e.g., "I went climbing yesterday", "Did a 7a today"):
- Gather the necessary details
- Check intervals.icu for matching Garmin data when a date is mentioned
- Validate climbing routes via web search when route names are given
- Present a summary and wait for explicit confirmation before calling `record_activity`

## 2. FIND & EDIT existing activities
When the user wants to find, view, or edit past activities (e.g., "show me my climbs last week", "edit my Tuesday session", "update the grade on yesterday's route", "find my multipitch from August"):
- Call `search_journal` to find matching activities
- Show what was found and ask which one they mean if multiple match
- If they want to edit: understand what changes to make, show a summary, then call `update_activity` to propose the changes
- You can also accept images to help identify or match activities

## 3. SUMMARISE a week
When the user asks for a summary (e.g., "how was my week?", "summarise last week", "what did I do this month"):
- Call `get_weekly_summary` to fetch the data
- Provide a narrative coaching summary: what was done, highlights, patterns, suggestions

---

## Activity types and their tags:

### `bouldering` — no rope, individual problems
- Tags: `indoor` (gym) or `outdoor` (rock)
- For climbing sessions collect each problem: grade (Font / V-scale), style, notes

### `sport_climb` — bolted single-pitch or multi-pitch routes
- Tags: `indoor` (gym/wall) or `outdoor` (rock crag), optionally `trad` for single-pitch gear routes
- Collect each route: name, grade, style, optionally height and sector

### `multi_pitch` — routes with 2+ pitches requiring anchors
- Tags: `bolted` (sport multi-pitch) or `trad` (gear protection), optionally `alpine`
- Typically 1 route per session — collect: name, grade, pitches, style, height

### `cycling`
- Tags: `commute`, `road_bike`, `gravel_bike`, `mtb` (mountain bike), `indoor`

### `hiking`
- No required tags; optionally `alpine` for high-mountain approaches

### `fitness` — gym sessions, yoga, general strength/conditioning
- Tags: `gym`, `yoga`, etc.

### `other` — anything that doesn't fit above, including running and swimming
- Tags: `run`, `trail_run`, `swim`, etc.

## Grade formats:
- YDS: 5.8, 5.10a, 5.12c → grade_system = "yds"
- French: 5a, 6b+, 7c, 9a → grade_system = "french"
- Fontainebleau: 6A, 7B+, 8C → grade_system = "font"
- UIAA: IV, VII+, IX → grade_system = "uiaa"
- V-scale: V3, V8, V10 → grade_system = "vscale"
- Alpine: F, PD, AD, D, TD, ED → grade_system = "alpine"

## Rules for logging new activities:
- NEVER call `record_activity` without first presenting a summary and getting explicit user confirmation.
- When intervals.icu returns matching activities, tell the user what was found and ask which matches.
- Multi-pitch does NOT automatically mean trad — always ask.
- For climbing sessions with multiple routes, collect all routes before calling `record_activity`.

## Rules for editing existing activities:
- NEVER call `update_activity` without first showing the proposed changes and getting explicit user confirmation.
- Always call `search_journal` first to find the activity — don't guess IDs.
- If you found the activity via image: describe what you see in the image to help the user confirm it's the right one.

## Rules for summaries:
- Always call `get_weekly_summary` first to get real data.
- Be encouraging and specific — mention real routes, grades, and achievements.
- Highlight patterns (consecutive days, grade progression, favourite area).
- Keep summaries concise but insightful — 3–5 sentences typically.
"""


# ─── Tool definitions ─────────────────────────────────────────────────────────

_SEARCH_INTERVALS_TOOL = {
    "type": "function",
    "function": {
        "name": "search_intervals_activities",
        "description": (
            "Search intervals.icu (synced from Garmin) for outdoor activities around a given date. "
            "Returns GPS location, duration, distance, elevation gain, and heart rate data. "
            "Call this as soon as the user mentions a date or relative time like 'yesterday'."
        ),
        "parameters": {
            "type": "object",
            "required": ["date"],
            "properties": {
                "date": {
                    "type": "string",
                    "format": "date",
                    "description": "The date to search around, in YYYY-MM-DD format.",
                },
                "days_around": {
                    "type": "integer",
                    "description": "How many days before and after the date to include (default 1).",
                    "default": 1,
                },
            },
        },
    },
}

_SEARCH_WEB_TOOL = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": (
            "Search the web via Brave Search to validate or enrich climbing route information. "
            "Searches thecrag.com, bergsteigen.com, and mountainproject.com first; "
            "automatically falls back to open web if not enough results are found there. "
            "Use this to: verify a route's grade, find the correct area/crag name, look up route length and pitch count."
        ),
        "parameters": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A specific search query, e.g. 'Hohe Wand Bergsteigen climbing route grade Austria'",
                },
            },
        },
    },
}

_RECORD_ACTIVITY_TOOL = {
    "type": "function",
    "function": {
        "name": "record_activity",
        "description": "Record a confirmed new outdoor activity. Only call AFTER the user has explicitly confirmed your summary.",
        "parameters": {
            "type": "object",
            "required": ["activity_type", "title", "date"],
            "properties": {
                "activity_type": {
                    "type": "string",
                    "enum": ["bouldering", "sport_climb", "multi_pitch", "cycling", "hiking", "fitness", "other"],
                },
                "title": {"type": "string"},
                "date": {"type": "string", "format": "date-time"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "duration_minutes": {"type": "integer"},
                "distance_km": {"type": "number"},
                "elevation_gain_m": {"type": "number"},
                "location_name": {"type": "string"},
                "lat": {"type": "number"},
                "lon": {"type": "number"},
                "area": {"type": "string"},
                "region": {"type": "string"},
                "avg_heart_rate": {"type": "integer"},
                "calories": {"type": "integer"},
                "partner": {"type": "string"},
                "notes": {"type": "string"},
                "intervals_activity_id": {"type": "string"},
                "routes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "route_name": {"type": "string"},
                            "grade": {"type": "string"},
                            "grade_system": {
                                "type": "string",
                                "enum": ["yds", "french", "font", "uiaa", "ice_wis", "alpine", "vscale"],
                            },
                            "style": {
                                "type": "string",
                                "enum": ["onsight", "flash", "redpoint", "top_rope", "attempt", "aid", "solo"],
                            },
                            "pitches": {"type": "integer"},
                            "height_m": {"type": "number"},
                            "sector": {"type": "string"},
                            "notes": {"type": "string"},
                            "sort_order": {"type": "integer"},
                        },
                    },
                },
            },
        },
    },
}

_SEARCH_JOURNAL_TOOL = {
    "type": "function",
    "function": {
        "name": "search_journal",
        "description": (
            "Search the user's activity journal. Use this to find past activities before editing them, "
            "or when the user asks to find specific sessions. Returns a list of matching activities with IDs."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Free-text search keywords (e.g. route name, area, partner)",
                },
                "activity_type": {
                    "type": "string",
                    "enum": ["bouldering", "sport_climb", "multi_pitch", "cycling", "hiking", "fitness", "other"],
                    "description": "Filter by activity type",
                },
                "date_from": {
                    "type": "string",
                    "format": "date",
                    "description": "Start of date range (YYYY-MM-DD)",
                },
                "date_to": {
                    "type": "string",
                    "format": "date",
                    "description": "End of date range (YYYY-MM-DD)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (default 10)",
                    "default": 10,
                },
            },
        },
    },
}

_GET_WEEKLY_SUMMARY_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weekly_summary",
        "description": (
            "Get a structured summary of the user's activities for a given week. "
            "Returns total counts, hours, elevation, and per-day activity breakdown. "
            "Call this when the user asks for a weekly or periodic summary."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "week_start": {
                    "type": "string",
                    "format": "date",
                    "description": (
                        "Monday of the week to summarise (YYYY-MM-DD). "
                        "Omit for the current week. Use 'last' for last week."
                    ),
                },
            },
        },
    },
}

_UPDATE_ACTIVITY_TOOL = {
    "type": "function",
    "function": {
        "name": "update_activity",
        "description": (
            "Propose changes to an existing activity. Only call AFTER the user has confirmed what to change. "
            "The user will review and approve the changes before they are saved."
        ),
        "parameters": {
            "type": "object",
            "required": ["activity_id"],
            "properties": {
                "activity_id": {
                    "type": "integer",
                    "description": "The ID of the activity to update (from search_journal results)",
                },
                "title": {"type": "string"},
                "activity_type": {
                    "type": "string",
                    "enum": ["bouldering", "sport_climb", "multi_pitch", "cycling", "hiking", "fitness", "other"],
                },
                "date": {"type": "string", "format": "date-time"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "duration_minutes": {"type": "integer"},
                "distance_km": {"type": "number"},
                "elevation_gain_m": {"type": "number"},
                "location_name": {"type": "string"},
                "area": {"type": "string"},
                "region": {"type": "string"},
                "partner": {"type": "string"},
                "notes": {"type": "string"},
                "avg_heart_rate": {"type": "integer"},
                "calories": {"type": "integer"},
            },
        },
    },
}

_TOOLS = [
    _SEARCH_INTERVALS_TOOL,
    _SEARCH_WEB_TOOL,
    _RECORD_ACTIVITY_TOOL,
    _SEARCH_JOURNAL_TOOL,
    _GET_WEEKLY_SUMMARY_TOOL,
    _UPDATE_ACTIVITY_TOOL,
]


# ─── Main coach function ──────────────────────────────────────────────────────


async def run_coach(
    messages: list[dict],
    images: list[dict],
    location_context: Optional[str],
    db_search: Callable,
    db_weekly_summary: Callable,
    db_get_activity: Callable,
) -> CoachResult:
    """Run the unified coach LLM loop."""
    system = COACH_SYSTEM
    if location_context:
        system += f"\n\nUser's approximate location (from IP): {location_context}"
    system += f"\n\nToday's date: {date.today().isoformat()}"

    # Build the full message list.
    # If there are images, attach them to the last user message.
    processed_messages = _inject_images(list(messages), images)
    full_messages = [{"role": "system", "content": system}] + processed_messages

    client = get_client()

    for _ in range(8):
        response = await client.chat.completions.create(
            model=settings.nvidia_model,
            messages=full_messages,
            tools=_TOOLS,
            tool_choice="auto",
            max_tokens=4096,
            temperature=0.3,
        )

        msg = response.choices[0].message

        if not msg.tool_calls:
            return CoachResult(reply=msg.content or "How can I help you?")

        full_messages.append(msg.model_dump(exclude_none=True))

        has_record = False
        has_update = False
        record_data: Optional[dict] = None
        update_result: Optional[PendingUpdate] = None
        found_activities: Optional[list[dict]] = None
        reply_text = msg.content or ""

        for tc in msg.tool_calls:
            fn = tc.function.name
            args = json.loads(tc.function.arguments)

            if fn == "search_intervals_activities":
                result_str = await _execute_search_intervals(args)
                full_messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_str})

            elif fn == "search_web":
                result_str = await _execute_search_web(args)
                full_messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_str})

            elif fn == "record_activity":
                has_record = True
                record_data = args
                reply_text = msg.content or _build_log_confirmation(args)
                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps({"status": "pending_user_confirmation"}),
                })

            elif fn == "search_journal":
                try:
                    activities = await db_search(
                        query=args.get("query"),
                        activity_type=args.get("activity_type"),
                        date_from=args.get("date_from"),
                        date_to=args.get("date_to"),
                        limit=int(args.get("limit", 10)),
                    )
                    found_activities = activities
                    result_str = json.dumps({"activities": activities, "count": len(activities)})
                except Exception as exc:
                    log.warning("search_journal failed: %s", exc)
                    result_str = json.dumps({"error": str(exc), "activities": []})
                full_messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_str})

            elif fn == "get_weekly_summary":
                try:
                    week_start = args.get("week_start")
                    summary = await db_weekly_summary(week_start)
                    result_str = json.dumps(summary)
                except Exception as exc:
                    log.warning("get_weekly_summary failed: %s", exc)
                    result_str = json.dumps({"error": str(exc)})
                full_messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_str})

            elif fn == "update_activity":
                activity_id = args.pop("activity_id")
                try:
                    current = await db_get_activity(activity_id)
                    has_update = True
                    update_result = PendingUpdate(
                        activity_id=activity_id,
                        changes=args,
                        current_values={k: current.get(k) for k in args},
                    )
                    reply_text = msg.content or _build_update_confirmation(args, current)
                except Exception as exc:
                    log.warning("update_activity lookup failed: %s", exc)
                    reply_text = f"Could not find activity {activity_id}: {exc}"
                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps({"status": "pending_user_confirmation"}),
                })

        if has_record:
            return CoachResult(
                reply=reply_text,
                pending_activity=record_data,
                needs_confirmation=True,
                found_activities=found_activities,
            )

        if has_update:
            return CoachResult(
                reply=reply_text,
                needs_confirmation=True,
                pending_update=update_result,
                found_activities=found_activities,
            )

    return CoachResult(reply="Something went wrong. Please try again.")


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _inject_images(messages: list[dict], images: list[dict]) -> list[dict]:
    """Attach base64 images to the last user message."""
    if not images:
        return messages

    # Find the last user message
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "user":
            content = messages[i]["content"]
            # Convert to multi-part content
            parts: list[dict] = [{"type": "text", "text": content if isinstance(content, str) else str(content)}]
            for img in images:
                parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{img['content_type']};base64,{img['data']}",
                    },
                })
            messages[i] = {**messages[i], "content": parts}
            break

    return messages


def _build_log_confirmation(data: dict) -> str:
    parts = []
    if data.get("activity_type"):
        parts.append(f"Type: {data['activity_type'].replace('_', ' ')}")
    tags = data.get("tags") or []
    if tags:
        parts.append(f"Tags: {', '.join(tags)}")
    if data.get("date"):
        parts.append(f"Date: {data['date'][:10]}")
    if data.get("area"):
        parts.append(f"Area: {data['area']}")
    if data.get("region"):
        parts.append(f"Region: {data['region']}")
    if data.get("duration_minutes"):
        h, m = divmod(int(data["duration_minutes"]), 60)
        parts.append(f"Duration: {h}h {m}m" if h else f"Duration: {m}m")
    if data.get("elevation_gain_m"):
        parts.append(f"Elevation: {data['elevation_gain_m']} m")
    if data.get("partner"):
        parts.append(f"Partner: {data['partner']}")
    summary = " · ".join(parts)

    routes = data.get("routes") or []
    route_lines = []
    for i, r in enumerate(routes):
        name = r.get("route_name") or f"Route {i + 1}"
        grade_str = r.get("grade", "?")
        if r.get("grade_system"):
            grade_str += f" ({r['grade_system']})"
        style_str = r.get("style", "")
        line = f"  {i + 1}. {name} — {grade_str}"
        if style_str:
            line += f", {style_str}"
        route_lines.append(line)

    text = f"Here's what I've got:\n{summary}"
    if route_lines:
        text += "\n\nRoutes:\n" + "\n".join(route_lines)
    text += "\n\nDoes that look right? I'll save it once you confirm."
    return text


def _build_update_confirmation(changes: dict, current: dict) -> str:
    lines = ["Here are the proposed changes:"]
    for field, new_val in changes.items():
        old_val = current.get(field, "(empty)")
        lines.append(f"  • {field}: {old_val!r} → {new_val!r}")
    lines.append("\nShall I apply these changes?")
    return "\n".join(lines)
