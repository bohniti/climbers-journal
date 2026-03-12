from typing import Optional
from dataclasses import dataclass
from datetime import date, datetime
from openai import AsyncOpenAI
from app.config import get_settings
import json
import logging

log = logging.getLogger(__name__)
settings = get_settings()

_client: Optional[AsyncOpenAI] = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            base_url=settings.nvidia_base_url,
            api_key=settings.nvidia_api_key,
        )
    return _client


SYSTEM_PROMPT = """You are an outdoor activities journal assistant. You help the user log climbs, hikes, cycling rides, fitness sessions, and other outdoor activities accurately.

## Your workflow — follow this exactly:

1. **Gather information** — ask clarifying questions until you have enough to log the activity correctly.
2. **Check intervals.icu** — if the user mentions a date (or says "yesterday", "today", "last Saturday"), call `search_intervals_activities` to look for a matching Garmin activity. Use its duration, elevation, and distance data if found.
3. **Validate via web search** — if the user names a specific climbing route, call `search_web` to verify grade, pitch count, and area. Skip for non-climbing activities unless location is ambiguous.
4. **Present a summary** — before calling `record_activity`, write out what you understood:
   "Here's what I've got — [details]. Does that look right?"
5. **Wait for confirmation** — only call `record_activity` after the user explicitly says "yes", "correct", "save it", etc.
6. **Never guess silently** — if unsure about any field, ask.

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
- Ask if not clear which kind

### `hiking`
- No required tags; optionally `alpine` for high-mountain approaches

### `fitness` — gym sessions, yoga, general strength/conditioning
- Tags: `gym`, `yoga`, etc.

### `other` — anything that doesn't fit above, including running and swimming
- Tags: `run`, `trail_run`, `swim`, etc.

## Routes for climbing sessions:

For `bouldering` and `sport_climb`, ask how many routes/problems were climbed and collect each one:
- route_name (optional for gym problems)
- grade + grade_system
- style (onsight / flash / redpoint / top_rope / attempt)
- pitches, height_m, sector (optional)

For `multi_pitch`, collect one route with all details including pitch count.

**Example multi-pitch session:**
User: "Did a 7-pitch bolted route called Traumtänzer at Rätikon, 6c+, onsight"
→ activity_type: multi_pitch, tags: ["bolted"], 1 route: {name: "Traumtänzer", grade: "6c+", grade_system: "french", style: "onsight", pitches: 7}

**Example sport climbing session:**
User: "indoor climbing yesterday, did 6b flash, 7a attempt, 6c redpoint"
→ activity_type: sport_climb, tags: ["indoor"], 3 routes each with grade + style

## Grade formats:
- YDS: 5.8, 5.10a, 5.12c → grade_system = "yds"
- French: 5a, 6b+, 7c, 9a → grade_system = "french"
- Fontainebleau: 6A, 7B+, 8C → grade_system = "font"
- UIAA: IV, VII+, IX → grade_system = "uiaa"
- V-scale: V3, V8, V10 → grade_system = "vscale"
- Alpine: F, PD, AD, D, TD, ED → grade_system = "alpine"

## What to ask when info is missing:
- **All activities**: date (required — needed to search intervals.icu)
- **Climbing**: indoor or outdoor? bolted or gear? number of routes/pitches?
- **Cycling**: which kind (road, gravel, MTB, commute)?
- **Multi-pitch**: how many pitches? bolted or trad?
- **Partner(s)** for any activity

## Important rules:
- NEVER call `record_activity` without first presenting a summary and getting user confirmation.
- When intervals.icu returns matching activities, tell the user what was found and ask which matches.
- If intervals.icu finds nothing, continue without Garmin data.
- Multi-pitch does NOT automatically mean trad — always ask.
- For climbing sessions with multiple routes, collect all routes before calling `record_activity`.
"""

# ─── Tool definitions ─────────────────────────────────────────────────────────

SEARCH_INTERVALS_TOOL = {
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

SEARCH_WEB_TOOL = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": (
            "Search the web via Brave Search to validate or enrich climbing route information. "
            "Searches thecrag.com, bergsteigen.com, and mountainproject.com first (best route databases); "
            "automatically falls back to open web if not enough results are found there. "
            "Use this to: verify a route's grade, find the correct area/crag name, look up route length and pitch count, "
            "check if a route name exists and is spelled correctly, or get general info about a climbing area. "
            "Good queries: 'Hohe Wand climbing routes Austria', 'Frankenjura 7c sport climb Rotstein', "
            "'El Capitan Nose route pitches grade'. Call this before presenting the summary when route details seem uncertain."
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

RECORD_ACTIVITY_TOOL = {
    "type": "function",
    "function": {
        "name": "record_activity",
        "description": "Record a confirmed outdoor activity. Only call AFTER the user has explicitly confirmed your summary.",
        "parameters": {
            "type": "object",
            "required": ["activity_type", "title", "date"],
            "properties": {
                "activity_type": {
                    "type": "string",
                    "enum": ["bouldering", "sport_climb", "multi_pitch", "cycling", "hiking", "fitness", "other"],
                    "description": "bouldering=no rope; sport_climb=bolted/single-pitch; multi_pitch=2+ pitches; cycling; hiking; fitness=gym/yoga/strength; other=run/trail_run/swim/anything else",
                },
                "title": {"type": "string", "description": "Short descriptive title for the session"},
                "date": {"type": "string", "format": "date-time"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Sub-category tags. bouldering/sport_climb: indoor|outdoor. multi_pitch: trad|bolted|alpine. cycling: commute|road_bike|gravel_bike|mtb|indoor. fitness: gym|yoga. other: run|trail_run|swim. Leave empty if unsure.",
                },
                "duration_minutes": {"type": "integer"},
                "distance_km": {"type": "number"},
                "elevation_gain_m": {"type": "number"},
                "location_name": {"type": "string"},
                "lat": {"type": "number"},
                "lon": {"type": "number"},
                "area": {"type": "string", "description": "Specific climbing area or crag name, e.g. 'Hexenküche', 'Kletterhalle Wien'"},
                "region": {"type": "string", "description": "Broader region for filtering, e.g. 'Fränkische Schweiz', 'Hohe Wand', 'Kletterhalle Wien', 'Kalymnos', 'Cala Gonone'. Use the same region name consistently."},
                "partner": {"type": "string"},
                "notes": {"type": "string"},
                "intervals_activity_id": {
                    "type": "string",
                    "description": "intervals.icu activity ID if matched to a Garmin activity",
                },
                "routes": {
                    "type": "array",
                    "description": "Individual routes/problems for bouldering, sport_climb, or multi_pitch sessions. Each entry is one route climbed.",
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
                            "pitches": {"type": "integer", "description": "Number of pitches (multi_pitch or multi-pitch sport)"},
                            "height_m": {"type": "number"},
                            "rock_type": {"type": "string"},
                            "sector": {"type": "string", "description": "Sub-area or sector within the crag"},
                            "notes": {"type": "string"},
                            "sort_order": {"type": "integer", "description": "Display order within session (0-indexed)"},
                        },
                    },
                },
            },
        },
    },
}

TOOLS = [SEARCH_INTERVALS_TOOL, SEARCH_WEB_TOOL, RECORD_ACTIVITY_TOOL]


# ─── Result type ──────────────────────────────────────────────────────────────

@dataclass
class LLMResult:
    reply: str
    activity_data: Optional[dict] = None
    needs_confirmation: bool = False


# ─── Tool executor ────────────────────────────────────────────────────────────

async def _execute_search_intervals(args: dict) -> str:
    """Run the search_intervals_activities tool and return a JSON string for the LLM."""
    from app.services.intervals import search_activities

    raw_date = args.get("date", date.today().isoformat())
    days_around = int(args.get("days_around", 1))

    try:
        target = date.fromisoformat(raw_date)
    except ValueError:
        target = date.today()

    if not settings.intervals_icu_api_key or not settings.intervals_icu_athlete_id:
        return json.dumps({
            "error": "intervals.icu not configured",
            "note": "Set INTERVALS_ICU_API_KEY and INTERVALS_ICU_ATHLETE_ID in .env to enable Garmin sync.",
        })

    try:
        activities = await search_activities(around_date=target, days_around=days_around)
    except Exception as e:
        log.warning("intervals.icu search failed: %s", e)
        return json.dumps({"error": str(e), "activities": []})

    if not activities:
        return json.dumps({
            "activities": [],
            "message": f"No activities found in intervals.icu around {raw_date}.",
        })

    return json.dumps({
        "activities": [a.to_llm_dict() for a in activities],
        "count": len(activities),
    })


async def _execute_search_web(args: dict) -> str:
    """Run the search_web tool and return a JSON string for the LLM."""
    from app.services.brave_search import web_search, CLIMBING_SITES

    query = args.get("query", "")
    if not query:
        return json.dumps({"error": "No query provided"})

    if not settings.brave_api_key:
        return json.dumps({
            "error": "Brave Search not configured",
            "note": "Set BRAVE_API_KEY in .env to enable web search.",
        })

    try:
        # Always use preferred climbing sites first; brave_search falls back to
        # open web automatically if fewer than MIN_SITE_RESULTS come back.
        results = await web_search(query, count=5, preferred_sites=CLIMBING_SITES)
    except Exception as e:
        log.warning("Brave Search failed: %s", e)
        return json.dumps({"error": str(e), "results": []})

    if not results:
        return json.dumps({"results": [], "message": f"No results found for: {query}"})

    return json.dumps({
        "results": [
            {"title": r.title, "url": r.url, "description": r.description}
            for r in results
        ]
    })


# ─── Main chat function ───────────────────────────────────────────────────────

async def extract_activity_from_chat(
    messages: list[dict],
    location_context: Optional[str] = None,
) -> LLMResult:
    system = SYSTEM_PROMPT
    if location_context:
        system += f"\n\nUser's approximate location (from IP): {location_context}"

    full_messages = [{"role": "system", "content": system}] + list(messages)
    client = get_client()

    # Tool execution loop — max 6 rounds to prevent infinite loops
    for _ in range(6):
        response = await client.chat.completions.create(
            model=settings.nvidia_model,
            messages=full_messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=4096,
            temperature=0.3,
        )

        msg = response.choices[0].message

        if not msg.tool_calls:
            # Plain text response — return to user
            return LLMResult(reply=msg.content or "Could you describe your activity?")

        # Add the assistant message (with tool calls) to history
        full_messages.append(msg.model_dump(exclude_none=True))

        # Process each tool call
        has_record_activity = False
        record_activity_data: Optional[dict] = None
        record_activity_reply: str = ""

        for tc in msg.tool_calls:
            fn = tc.function.name
            args = json.loads(tc.function.arguments)

            if fn == "search_intervals_activities":
                result_str = await _execute_search_intervals(args)
                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_str,
                })

            elif fn == "search_web":
                result_str = await _execute_search_web(args)
                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_str,
                })

            elif fn == "record_activity":
                # Don't save yet — return to client for user confirmation
                has_record_activity = True
                record_activity_data = args
                record_activity_reply = msg.content or _build_confirmation_text(args)
                # Still need to add a tool result so the message history stays valid
                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps({"status": "pending_user_confirmation"}),
                })

        if has_record_activity:
            return LLMResult(
                reply=record_activity_reply,
                activity_data=record_activity_data,
                needs_confirmation=True,
            )

        # Otherwise loop — LLM will now see tool results and respond

    return LLMResult(reply="Something went wrong processing your request. Please try again.")


def _build_confirmation_text(data: dict) -> str:
    parts = []
    if data.get("activity_type"):
        parts.append(f"Type: {data['activity_type'].replace('_', ' ')}")
    tags = data.get("tags") or []
    if tags:
        parts.append(f"Tags: {', '.join(tags)}")
    if data.get("region"):
        parts.append(f"Region: {data['region']}")
    if data.get("area"):
        parts.append(f"Area: {data['area']}")
    if data.get("date"):
        parts.append(f"Date: {data['date'][:10]}")
    if data.get("elevation_gain_m"):
        parts.append(f"Elevation: {data['elevation_gain_m']} m")
    if data.get("duration_minutes"):
        h, m = divmod(int(data["duration_minutes"]), 60)
        parts.append(f"Duration: {h}h {m}m" if h else f"Duration: {m}m")
    if data.get("partner"):
        parts.append(f"Partner: {data['partner']}")
    summary = " · ".join(parts)

    # Routes
    routes = data.get("routes") or []
    route_lines = []
    for i, r in enumerate(routes):
        route_name = r.get("route_name") or f"Route {i + 1}"
        grade_str = r.get("grade", "?")
        if r.get("grade_system"):
            grade_str += f" ({r['grade_system']})"
        style_str = r.get("style", "")
        pitches = r.get("pitches")
        line = f"  {i + 1}. {route_name} — {grade_str}"
        if style_str:
            line += f", {style_str}"
        if pitches:
            line += f", {pitches}p"
        route_lines.append(line)

    text = f"Here's what I've got:\n{summary}"
    if route_lines:
        text += "\n\nRoutes:\n" + "\n".join(route_lines)
    text += "\n\nDoes that look right? I'll save it once you confirm."
    return text
