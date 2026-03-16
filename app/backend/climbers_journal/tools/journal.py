"""Journal query tools — search routes, get ascents, stats, and training overview."""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, case
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from climbers_journal.models.climbing import (
    Ascent,
    ClimbingSession,
    Crag,
    Route,
    TickType,
    VenueType,
    normalize_name,
)
from climbers_journal.models.endurance import EnduranceActivity
from climbers_journal.services.climbing import list_climbing_sessions, _session_to_dict

# Tick types that count as "sends"
SEND_TICK_TYPES = {
    TickType.onsight,
    TickType.flash,
    TickType.redpoint,
    TickType.pinkpoint,
    TickType.repeat,
}

definitions: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_routes",
            "description": (
                "Search for climbing routes in the journal by name, grade, or crag. "
                "Returns matching routes with their crag and grade info."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Route name to search for (partial match, case-insensitive).",
                    },
                    "grade": {
                        "type": "string",
                        "description": "Exact grade to filter by (e.g. '7a', '5.12a', 'V6').",
                    },
                    "crag_name": {
                        "type": "string",
                        "description": "Crag name to filter by (partial match, case-insensitive).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default 20).",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ascents",
            "description": (
                "Query climbing ascents from the journal with filters. "
                "Returns ascent records with route, grade, crag, date, and tick type."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format.",
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format.",
                    },
                    "grade": {
                        "type": "string",
                        "description": "Filter by grade (exact match).",
                    },
                    "tick_type": {
                        "type": "string",
                        "description": "Filter by tick type: onsight, flash, redpoint, pinkpoint, repeat, attempt, hang.",
                    },
                    "crag_name": {
                        "type": "string",
                        "description": "Filter by crag name (partial match, case-insensitive).",
                    },
                    "sends_only": {
                        "type": "boolean",
                        "description": "If true, only return sends (onsight/flash/redpoint/pinkpoint/repeat), excluding attempts and hangs.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (default 50).",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_climbing_stats",
            "description": (
                "Get climbing statistics: sends by grade (grade pyramid), onsight rate, "
                "volume over time, hardest sends. Can filter by date range and venue type."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format.",
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format.",
                    },
                    "venue_type": {
                        "type": "string",
                        "description": "Filter by venue: 'outdoor_crag' or 'indoor_gym'. Omit for all.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_training_overview",
            "description": (
                "Get a combined training overview for a period: climbing volume + "
                "endurance load side by side. Shows both domains in their native metrics."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD (defaults to 7 days ago).",
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD (defaults to today).",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sessions",
            "description": (
                "Query climbing sessions grouped by date and crag. Each session contains "
                "nested ascents (routes climbed). Filter by date range or crag name."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format.",
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format.",
                    },
                    "crag_name": {
                        "type": "string",
                        "description": "Filter by crag name (partial match, case-insensitive).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max sessions to return (default 20).",
                    },
                },
                "required": [],
            },
        },
    },
]


async def _search_routes(args: dict[str, Any], session: AsyncSession) -> str:
    """Find routes by name, grade, or crag."""
    limit = min(args.get("limit", 20), 100)

    stmt = select(Route, Crag.name.label("crag_name_col")).join(Crag, Route.crag_id == Crag.id)

    if name := args.get("name"):
        normalized = normalize_name(name)
        stmt = stmt.where(Route.name_normalized.contains(normalized))

    if grade := args.get("grade"):
        stmt = stmt.where(Route.grade == grade)

    if crag_name := args.get("crag_name"):
        normalized_crag = normalize_name(crag_name)
        stmt = stmt.where(Crag.name_normalized.contains(normalized_crag))

    stmt = stmt.order_by(Route.name).limit(limit)
    result = await session.exec(stmt)
    rows = result.all()

    routes = []
    for route, crag_name_val in rows:
        routes.append({
            "id": route.id,
            "name": route.name,
            "grade": route.grade,
            "grade_system": route.grade_system.value,
            "style": route.style.value,
            "crag": crag_name_val,
        })

    return json.dumps({"routes": routes, "count": len(routes)}, default=str)


async def _get_ascents(args: dict[str, Any], session: AsyncSession) -> str:
    """Query ascents with filters."""
    limit = min(args.get("limit", 50), 200)

    stmt = select(Ascent)

    if date_from := args.get("date_from"):
        stmt = stmt.where(Ascent.date >= date.fromisoformat(date_from))
    if date_to := args.get("date_to"):
        stmt = stmt.where(Ascent.date <= date.fromisoformat(date_to))
    if grade := args.get("grade"):
        stmt = stmt.where(Ascent.grade == grade)
    if tick_type := args.get("tick_type"):
        stmt = stmt.where(Ascent.tick_type == TickType(tick_type))
    if crag_name := args.get("crag_name"):
        normalized_crag = normalize_name(crag_name)
        stmt = stmt.join(Crag, Ascent.crag_id == Crag.id).where(
            Crag.name_normalized.contains(normalized_crag)
        )
    if args.get("sends_only"):
        stmt = stmt.where(Ascent.tick_type.in_([t.value for t in SEND_TICK_TYPES]))

    stmt = stmt.order_by(Ascent.date.desc()).limit(limit)
    result = await session.exec(stmt)
    ascents = result.all()

    items = []
    for a in ascents:
        items.append({
            "id": a.id,
            "date": str(a.date),
            "route": a.route_name,
            "grade": a.grade,
            "crag": a.crag_name,
            "tick_type": a.tick_type.value,
            "tries": a.tries,
            "notes": a.notes,
        })

    return json.dumps({"ascents": items, "count": len(items)}, default=str)


async def _get_climbing_stats(args: dict[str, Any], session: AsyncSession) -> str:
    """Compute climbing stats: grade pyramid, onsight rate, volume, hardest sends."""

    # Base filter for ascents
    base_filters = []
    if date_from := args.get("date_from"):
        base_filters.append(Ascent.date >= date.fromisoformat(date_from))
    if date_to := args.get("date_to"):
        base_filters.append(Ascent.date <= date.fromisoformat(date_to))

    venue_type = args.get("venue_type")
    if venue_type:
        # Use subquery to avoid JOIN issues with GROUP BY
        venue_crag_ids = select(Crag.id).where(Crag.venue_type == VenueType(venue_type))
        base_filters.append(Ascent.crag_id.in_(venue_crag_ids))

    def _apply_filters(stmt):
        for f in base_filters:
            stmt = stmt.where(f)
        return stmt

    # 1. Grade pyramid — sends grouped by grade
    pyramid_stmt = (
        select(Ascent.grade, Ascent.tick_type, func.count().label("count"))
        .where(Ascent.tick_type.in_([t.value for t in SEND_TICK_TYPES]))
        .where(Ascent.grade.isnot(None))
        .group_by(Ascent.grade, Ascent.tick_type)
        .order_by(Ascent.grade)
    )
    pyramid_stmt = _apply_filters(pyramid_stmt)
    result = await session.exec(pyramid_stmt)
    pyramid_rows = result.all()

    grade_pyramid: dict[str, dict[str, int]] = {}
    for grade_val, tick_type_val, count in pyramid_rows:
        if grade_val not in grade_pyramid:
            grade_pyramid[grade_val] = {}
        grade_pyramid[grade_val][tick_type_val] = count

    # 2. Total counts by tick type
    totals_stmt = (
        select(Ascent.tick_type, func.count().label("count"))
        .group_by(Ascent.tick_type)
    )
    totals_stmt = _apply_filters(totals_stmt)
    result = await session.exec(totals_stmt)
    totals = {row[0]: row[1] for row in result.all()}

    total_ascents = sum(totals.values())
    total_sends = sum(v for k, v in totals.items() if TickType(k) in SEND_TICK_TYPES)
    total_onsights = totals.get(TickType.onsight.value, 0)

    # 3. Onsight rate (onsights / sends)
    onsight_rate = round(total_onsights / total_sends * 100, 1) if total_sends > 0 else 0

    # 4. Hardest sends (top 5 by grade, descending — simple string sort, imperfect but useful)
    hardest_stmt = (
        select(Ascent)
        .where(Ascent.tick_type.in_([t.value for t in SEND_TICK_TYPES]))
        .where(Ascent.grade.isnot(None))
        .order_by(Ascent.grade.desc())
        .limit(5)
    )
    hardest_stmt = _apply_filters(hardest_stmt)
    result = await session.exec(hardest_stmt)
    hardest = [
        {
            "route": a.route_name,
            "grade": a.grade,
            "tick_type": a.tick_type.value,
            "crag": a.crag_name,
            "date": str(a.date),
        }
        for a in result.all()
    ]

    # 5. Volume by month (last 12 months)
    twelve_months_ago = date.today() - timedelta(days=365)
    month_col = func.date_trunc("month", Ascent.date).label("month")
    send_values = [t.value for t in SEND_TICK_TYPES]
    volume_stmt = (
        select(
            month_col,
            func.count().label("total"),
            func.sum(case((Ascent.tick_type.in_(send_values), 1), else_=0)).label("sends"),
        )
        .where(Ascent.date >= twelve_months_ago)
        .group_by(month_col)
        .order_by(month_col)
    )
    volume_stmt = _apply_filters(volume_stmt)
    result = await session.exec(volume_stmt)
    volume_by_month = [
        {"month": row[0].strftime("%Y-%m"), "total": row[1], "sends": row[2]}
        for row in result.all()
    ]

    stats = {
        "total_ascents": total_ascents,
        "total_sends": total_sends,
        "onsight_rate_pct": onsight_rate,
        "totals_by_tick_type": totals,
        "grade_pyramid": grade_pyramid,
        "hardest_sends": hardest,
        "volume_by_month": volume_by_month,
    }

    return json.dumps(stats, default=str)


async def _get_training_overview(args: dict[str, Any], session: AsyncSession) -> str:
    """Combined climbing + endurance overview for a period."""
    today = date.today()
    d_from = date.fromisoformat(args["date_from"]) if args.get("date_from") else today - timedelta(days=7)
    d_to = date.fromisoformat(args["date_to"]) if args.get("date_to") else today

    # Climbing: count ascents and sends per day
    climbing_stmt = (
        select(
            Ascent.date,
            func.count().label("total_ascents"),
            func.count(case((Ascent.tick_type.in_([t.value for t in SEND_TICK_TYPES]), 1))).label("sends"),
        )
        .where(Ascent.date >= d_from, Ascent.date <= d_to)
        .group_by(Ascent.date)
        .order_by(Ascent.date)
    )
    result = await session.exec(climbing_stmt)
    climbing_days = [
        {"date": str(row[0]), "ascents": row[1], "sends": row[2]}
        for row in result.all()
    ]

    # Climbing summary
    climbing_total = sum(d["ascents"] for d in climbing_days)
    climbing_sends = sum(d["sends"] for d in climbing_days)

    # Hardest send in period
    hardest_stmt = (
        select(Ascent)
        .where(
            Ascent.date >= d_from,
            Ascent.date <= d_to,
            Ascent.tick_type.in_([t.value for t in SEND_TICK_TYPES]),
            Ascent.grade.isnot(None),
        )
        .order_by(Ascent.grade.desc())
        .limit(1)
    )
    result = await session.exec(hardest_stmt)
    hardest = result.first()
    hardest_send = None
    if hardest:
        hardest_send = {
            "route": hardest.route_name,
            "grade": hardest.grade,
            "tick_type": hardest.tick_type.value,
            "date": str(hardest.date),
        }

    # Endurance: activities in period
    endurance_stmt = (
        select(EnduranceActivity)
        .where(EnduranceActivity.date >= d_from, EnduranceActivity.date <= d_to)
        .order_by(EnduranceActivity.date)
    )
    result = await session.exec(endurance_stmt)
    endurance_activities = result.all()

    endurance_items = []
    total_duration_s = 0
    total_distance_m = 0.0
    total_load = 0.0
    for ea in endurance_activities:
        total_duration_s += ea.duration_s
        if ea.distance_m:
            total_distance_m += ea.distance_m
        if ea.training_load:
            total_load += ea.training_load
        endurance_items.append({
            "date": str(ea.date),
            "type": ea.type,
            "name": ea.name,
            "duration_min": round(ea.duration_s / 60),
            "distance_km": round(ea.distance_m / 1000, 1) if ea.distance_m else None,
            "training_load": ea.training_load,
        })

    overview = {
        "period": {"from": str(d_from), "to": str(d_to)},
        "climbing": {
            "days_active": len(climbing_days),
            "total_ascents": climbing_total,
            "total_sends": climbing_sends,
            "hardest_send": hardest_send,
            "daily_breakdown": climbing_days,
        },
        "endurance": {
            "activities_count": len(endurance_items),
            "total_duration_min": round(total_duration_s / 60),
            "total_distance_km": round(total_distance_m / 1000, 1),
            "total_training_load": round(total_load, 1),
            "activities": endurance_items,
        },
    }

    return json.dumps(overview, default=str)


async def _get_sessions(args: dict[str, Any], session: AsyncSession) -> str:
    """Query climbing sessions with nested ascents."""
    limit = min(args.get("limit", 20), 50)

    date_from = date.fromisoformat(args["date_from"]) if args.get("date_from") else None
    date_to = date.fromisoformat(args["date_to"]) if args.get("date_to") else None

    crag_id = None
    if crag_name := args.get("crag_name"):
        normalized_crag = normalize_name(crag_name)
        crag_stmt = select(Crag).where(Crag.name_normalized.contains(normalized_crag))
        result = await session.exec(crag_stmt)
        crag = result.first()
        if crag:
            crag_id = crag.id
        else:
            return json.dumps({"sessions": [], "count": 0, "note": f"No crag found matching '{crag_name}'"})

    sessions = await list_climbing_sessions(
        session,
        date_from=date_from,
        date_to=date_to,
        crag_id=crag_id,
        limit=limit,
    )

    items = [_session_to_dict(cs) for cs in sessions]
    return json.dumps({"sessions": items, "count": len(items)}, default=str)


async def handle(tool_name: str, arguments: dict[str, Any], context: dict[str, Any]) -> str | None:
    """Handle a tool call. Returns None if the tool name is not ours."""
    session: AsyncSession | None = context.get("db_session")

    handlers = {
        "search_routes": _search_routes,
        "get_ascents": _get_ascents,
        "get_climbing_stats": _get_climbing_stats,
        "get_training_overview": _get_training_overview,
        "get_sessions": _get_sessions,
    }

    handler = handlers.get(tool_name)
    if handler is None:
        return None

    if session is None:
        return json.dumps({"error": "No database session available. Cannot query journal data."})

    return await handler(arguments, session)
