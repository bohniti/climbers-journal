"""Tests for journal query tools (search_routes, get_ascents, get_climbing_stats, get_training_overview)."""

from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from climbers_journal.models.climbing import (
    Ascent,
    Crag,
    GradeSystem,
    Route,
    RouteStyle,
    TickType,
    VenueType,
    normalize_name,
)
from climbers_journal.models.endurance import ActivitySource, EnduranceActivity
from climbers_journal.tools.journal import handle


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def today():
    return date.today()


async def _seed_climbing_data(session, today):
    """Create sample crags, routes, and ascents for testing."""
    # Outdoor crag
    crag = Crag(
        name="Frankenjura",
        name_normalized=normalize_name("Frankenjura"),
        country="Germany",
        venue_type=VenueType.outdoor_crag,
        default_grade_sys=GradeSystem.uiaa,
    )
    session.add(crag)
    await session.flush()

    # Routes
    route1 = Route(
        name="Wallstreet",
        name_normalized=normalize_name("Wallstreet"),
        grade="8a",
        grade_system=GradeSystem.french,
        style=RouteStyle.sport,
        crag_id=crag.id,
    )
    route2 = Route(
        name="Action Directe",
        name_normalized=normalize_name("Action Directe"),
        grade="9a",
        grade_system=GradeSystem.french,
        style=RouteStyle.sport,
        crag_id=crag.id,
    )
    route3 = Route(
        name="Sautanz",
        name_normalized=normalize_name("Sautanz"),
        grade="7c+",
        grade_system=GradeSystem.french,
        style=RouteStyle.sport,
        crag_id=crag.id,
    )
    session.add_all([route1, route2, route3])
    await session.flush()

    # Ascents
    ascents = [
        Ascent(
            date=today,
            tick_type=TickType.onsight,
            route_id=route1.id,
            crag_id=crag.id,
            crag_name="Frankenjura",
            route_name="Wallstreet",
            grade="8a",
            tries=1,
        ),
        Ascent(
            date=today,
            tick_type=TickType.attempt,
            route_id=route2.id,
            crag_id=crag.id,
            crag_name="Frankenjura",
            route_name="Action Directe",
            grade="9a",
            tries=3,
            notes="fell at crux",
        ),
        Ascent(
            date=today - timedelta(days=3),
            tick_type=TickType.redpoint,
            route_id=route3.id,
            crag_id=crag.id,
            crag_name="Frankenjura",
            route_name="Sautanz",
            grade="7c+",
            tries=2,
        ),
        Ascent(
            date=today - timedelta(days=30),
            tick_type=TickType.flash,
            route_id=route1.id,
            crag_id=crag.id,
            crag_name="Frankenjura",
            route_name="Wallstreet",
            grade="8a",
        ),
    ]
    session.add_all(ascents)

    # Indoor gym
    gym = Crag(
        name="Boulderhalle Wien",
        name_normalized=normalize_name("Boulderhalle Wien"),
        country="Austria",
        venue_type=VenueType.indoor_gym,
        default_grade_sys=GradeSystem.font,
    )
    session.add(gym)
    await session.flush()

    gym_ascent = Ascent(
        date=today - timedelta(days=1),
        tick_type=TickType.redpoint,
        crag_id=gym.id,
        crag_name="Boulderhalle Wien",
        grade="V6",
    )
    session.add(gym_ascent)
    await session.flush()

    return crag, gym, [route1, route2, route3]


async def _seed_endurance_data(session, today):
    """Create sample endurance activities."""
    activities = [
        EnduranceActivity(
            intervals_id="act-1",
            date=today - timedelta(days=1),
            type="Run",
            name="Morning Run",
            duration_s=3600,
            distance_m=10000,
            avg_hr=145,
            training_load=80.0,
            source=ActivitySource.intervals_icu,
        ),
        EnduranceActivity(
            intervals_id="act-2",
            date=today - timedelta(days=3),
            type="Ride",
            name="Easy Ride",
            duration_s=5400,
            distance_m=30000,
            avg_hr=130,
            training_load=60.0,
            source=ActivitySource.intervals_icu,
        ),
    ]
    session.add_all(activities)
    await session.flush()
    return activities


# ── search_routes ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_search_routes_by_name(session, today):
    await _seed_climbing_data(session, today)

    result = await handle("search_routes", {"name": "wall"}, {"db_session": session})
    data = json.loads(result)
    assert data["count"] == 1
    assert data["routes"][0]["name"] == "Wallstreet"
    assert data["routes"][0]["crag"] == "Frankenjura"


@pytest.mark.asyncio
async def test_search_routes_by_grade(session, today):
    await _seed_climbing_data(session, today)

    result = await handle("search_routes", {"grade": "9a"}, {"db_session": session})
    data = json.loads(result)
    assert data["count"] == 1
    assert data["routes"][0]["name"] == "Action Directe"


@pytest.mark.asyncio
async def test_search_routes_by_crag(session, today):
    await _seed_climbing_data(session, today)

    result = await handle("search_routes", {"crag_name": "franken"}, {"db_session": session})
    data = json.loads(result)
    assert data["count"] == 3


@pytest.mark.asyncio
async def test_search_routes_no_results(session, today):
    await _seed_climbing_data(session, today)

    result = await handle("search_routes", {"name": "nonexistent"}, {"db_session": session})
    data = json.loads(result)
    assert data["count"] == 0


# ── get_ascents ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_ascents_all(session, today):
    await _seed_climbing_data(session, today)

    result = await handle("get_ascents", {}, {"db_session": session})
    data = json.loads(result)
    assert data["count"] == 5  # 4 outdoor + 1 gym


@pytest.mark.asyncio
async def test_get_ascents_sends_only(session, today):
    await _seed_climbing_data(session, today)

    result = await handle("get_ascents", {"sends_only": True}, {"db_session": session})
    data = json.loads(result)
    # onsight(Wallstreet) + redpoint(Sautanz) + flash(Wallstreet) + redpoint(gym V6) = 4
    assert data["count"] == 4
    tick_types = {a["tick_type"] for a in data["ascents"]}
    assert "attempt" not in tick_types


@pytest.mark.asyncio
async def test_get_ascents_by_date_range(session, today):
    await _seed_climbing_data(session, today)

    result = await handle(
        "get_ascents",
        {"date_from": str(today - timedelta(days=2)), "date_to": str(today)},
        {"db_session": session},
    )
    data = json.loads(result)
    # today: Wallstreet onsight + Action Directe attempt, yesterday: gym V6 = 3
    assert data["count"] == 3


@pytest.mark.asyncio
async def test_get_ascents_by_tick_type(session, today):
    await _seed_climbing_data(session, today)

    result = await handle("get_ascents", {"tick_type": "onsight"}, {"db_session": session})
    data = json.loads(result)
    assert data["count"] == 1
    assert data["ascents"][0]["route"] == "Wallstreet"


@pytest.mark.asyncio
async def test_get_ascents_by_crag_name(session, today):
    await _seed_climbing_data(session, today)

    result = await handle("get_ascents", {"crag_name": "boulder"}, {"db_session": session})
    data = json.loads(result)
    assert data["count"] == 1
    assert data["ascents"][0]["grade"] == "V6"


# ── get_climbing_stats ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_climbing_stats_basic(session, today):
    await _seed_climbing_data(session, today)

    result = await handle("get_climbing_stats", {}, {"db_session": session})
    data = json.loads(result)

    assert data["total_ascents"] == 5
    assert data["total_sends"] == 4  # onsight + redpoint + flash + gym redpoint
    assert data["onsight_rate_pct"] == 25.0  # 1 onsight / 4 sends
    assert len(data["hardest_sends"]) > 0
    assert len(data["grade_pyramid"]) > 0


@pytest.mark.asyncio
async def test_climbing_stats_venue_filter(session, today):
    await _seed_climbing_data(session, today)

    result = await handle(
        "get_climbing_stats",
        {"venue_type": "outdoor_crag"},
        {"db_session": session},
    )
    data = json.loads(result)

    # Outdoor only: 4 ascents (3 sends + 1 attempt)
    assert data["total_ascents"] == 4
    assert data["total_sends"] == 3


@pytest.mark.asyncio
async def test_climbing_stats_date_filter(session, today):
    await _seed_climbing_data(session, today)

    result = await handle(
        "get_climbing_stats",
        {"date_from": str(today), "date_to": str(today)},
        {"db_session": session},
    )
    data = json.loads(result)

    # Today only: Wallstreet onsight + Action Directe attempt = 2
    assert data["total_ascents"] == 2
    assert data["total_sends"] == 1


# ── get_training_overview ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_training_overview(session, today):
    await _seed_climbing_data(session, today)
    await _seed_endurance_data(session, today)

    result = await handle(
        "get_training_overview",
        {"date_from": str(today - timedelta(days=7)), "date_to": str(today)},
        {"db_session": session},
    )
    data = json.loads(result)

    # Climbing
    assert data["climbing"]["total_ascents"] >= 3
    assert data["climbing"]["total_sends"] >= 2
    assert data["climbing"]["hardest_send"] is not None

    # Endurance
    assert data["endurance"]["activities_count"] == 2
    assert data["endurance"]["total_duration_min"] == 150  # (3600+5400)/60
    assert data["endurance"]["total_distance_km"] == 40.0  # (10000+30000)/1000
    assert data["endurance"]["total_training_load"] == 140.0


@pytest.mark.asyncio
async def test_training_overview_defaults_to_last_week(session, today):
    """When no dates provided, defaults to last 7 days."""
    await _seed_climbing_data(session, today)

    result = await handle("get_training_overview", {}, {"db_session": session})
    data = json.loads(result)

    assert data["period"]["from"] == str(today - timedelta(days=7))
    assert data["period"]["to"] == str(today)


# ── handle returns None for unknown tools ─────────────────────────────


@pytest.mark.asyncio
async def test_handle_unknown_tool(session):
    result = await handle("unknown_tool", {}, {"db_session": session})
    assert result is None


# ── handle without session returns error ──────────────────────────────


@pytest.mark.asyncio
async def test_handle_no_session():
    result = await handle("search_routes", {"name": "test"}, {})
    data = json.loads(result)
    assert "error" in data
