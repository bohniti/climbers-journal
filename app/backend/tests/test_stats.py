"""Tests for stats/dashboard endpoints."""

from datetime import date, timedelta

import pytest

from climbers_journal.models.activity import Activity, ActivitySource
from climbers_journal.models.climbing import TickType, VenueType
from climbers_journal.routers.stats import (
    _build_climbing_stats,
    _build_endurance_stats,
    _build_grade_pyramid,
    _recent_climbing,
    _recent_endurance,
    get_calendar,
    get_weekly,
)
from climbers_journal.services.activity import create_climbing_activity


# ── Grade Pyramid ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_grade_pyramid_empty(session):
    result = await _build_grade_pyramid(session)
    assert result == []


@pytest.mark.asyncio
async def test_grade_pyramid_with_sends(session):
    today = date.today()
    await create_climbing_activity(
        session,
        crag_name="Test Crag",
        crag_country="Germany",
        venue_type=VenueType.outdoor_crag,
        ascents_data=[
            {"route_name": "Route A", "grade": "7a", "tick_type": TickType.redpoint, "date": today},
            {"route_name": "Route B", "grade": "7a", "tick_type": TickType.onsight, "date": today},
            {"route_name": "Route C", "grade": "6c", "tick_type": TickType.flash, "date": today},
            {"route_name": "Route D", "grade": "7a", "tick_type": TickType.attempt, "date": today},
        ],
    )
    await session.commit()

    result = await _build_grade_pyramid(session)
    grades = {e.grade: e for e in result}

    # Only sends appear (attempt excluded)
    assert "6c" in grades
    assert grades["6c"].flash == 1
    assert grades["6c"].total == 1

    assert "7a" in grades
    assert grades["7a"].redpoint == 1
    assert grades["7a"].onsight == 1
    assert grades["7a"].total == 2


@pytest.mark.asyncio
async def test_grade_pyramid_venue_filter(session):
    today = date.today()
    await create_climbing_activity(
        session,
        crag_name="Outdoor Crag",
        crag_country="Germany",
        venue_type=VenueType.outdoor_crag,
        ascents_data=[
            {"route_name": "Outdoor Route", "grade": "7a", "tick_type": TickType.redpoint, "date": today},
        ],
    )
    await create_climbing_activity(
        session,
        crag_name="Indoor Gym",
        crag_country="Germany",
        venue_type=VenueType.indoor_gym,
        ascents_data=[
            {"grade": "6b", "tick_type": TickType.flash, "date": today},
        ],
    )
    await session.commit()

    outdoor = await _build_grade_pyramid(session, venue_type="outdoor_crag")
    assert len(outdoor) == 1
    assert outdoor[0].grade == "7a"

    indoor = await _build_grade_pyramid(session, venue_type="indoor_gym")
    assert len(indoor) == 1
    assert indoor[0].grade == "6b"


@pytest.mark.asyncio
async def test_grade_pyramid_period_filter(session):
    today = date.today()
    old = date(today.year - 1, 1, 15)
    await create_climbing_activity(
        session,
        crag_name="Crag",
        crag_country="Germany",
        venue_type=VenueType.outdoor_crag,
        ascents_data=[
            {"route_name": "Old Route", "grade": "6a", "tick_type": TickType.redpoint, "date": old},
            {"route_name": "New Route", "grade": "7b", "tick_type": TickType.onsight, "date": today},
        ],
    )
    await session.commit()

    this_year = await _build_grade_pyramid(session, period="this_year")
    grades = [e.grade for e in this_year]
    assert "7b" in grades
    assert "6a" not in grades


# ── Climbing Stats ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_climbing_stats(session):
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    await create_climbing_activity(
        session,
        crag_name="Crag",
        crag_country="Germany",
        venue_type=VenueType.outdoor_crag,
        ascents_data=[
            {"route_name": "R1", "grade": "7a", "tick_type": TickType.redpoint, "date": today},
            {"route_name": "R2", "grade": "8a", "tick_type": TickType.onsight, "date": today},
            {"route_name": "R3", "grade": "6a", "tick_type": TickType.attempt, "date": today},
        ],
    )
    await session.commit()

    stats = await _build_climbing_stats(session, week_ago, month_ago, today)
    assert stats.total_sends_week == 2  # attempts don't count
    assert stats.total_sends_month == 2
    assert stats.hardest_send is not None
    assert stats.hardest_send.grade == "8a"


# ── Endurance Stats ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_endurance_stats_empty(session):
    today = date.today()
    week_ago = today - timedelta(days=7)
    stats = await _build_endurance_stats(session, week_ago, today)
    assert stats.activities_week == 0
    assert stats.total_duration_min_week == 0


# ── Recent Items ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_recent_climbing(session):
    today = date.today()
    await create_climbing_activity(
        session,
        crag_name="Crag",
        crag_country="Germany",
        venue_type=VenueType.outdoor_crag,
        ascents_data=[
            {"route_name": "R1", "grade": "7a", "tick_type": TickType.redpoint, "date": today},
        ],
    )
    await session.commit()

    recent = await _recent_climbing(session, today - timedelta(days=7), today)
    assert len(recent) == 1
    assert recent[0].route_name == "R1"
    assert recent[0].grade == "7a"


@pytest.mark.asyncio
async def test_recent_endurance_empty(session):
    today = date.today()
    recent = await _recent_endurance(session, today - timedelta(days=7), today)
    assert recent == []


# ── Calendar ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_calendar_empty(session):
    today = date.today()
    month_str = f"{today.year}-{today.month:02d}"
    result = await get_calendar(month=month_str, session=session)
    assert result.month == month_str
    assert result.days == []


@pytest.mark.asyncio
async def test_calendar_with_climbing(session):
    today = date.today()
    month_str = f"{today.year}-{today.month:02d}"

    await create_climbing_activity(
        session,
        crag_name="Test Crag",
        crag_country="Germany",
        venue_type=VenueType.outdoor_crag,
        ascents_data=[
            {"route_name": "R1", "grade": "7a", "tick_type": TickType.redpoint, "date": today},
            {"route_name": "R2", "grade": "8a", "tick_type": TickType.onsight, "date": today},
        ],
    )
    await session.commit()

    result = await get_calendar(month=month_str, session=session)
    assert len(result.days) == 1
    day = result.days[0]
    assert day.date == today.isoformat()
    assert day.climbing is not None
    assert day.climbing.route_count == 2
    assert day.climbing.venue_type == "outdoor_crag"


@pytest.mark.asyncio
async def test_calendar_with_endurance(session):
    today = date.today()
    month_str = f"{today.year}-{today.month:02d}"

    activity = Activity(
        intervals_id="test-1",
        date=today,
        type="run",
        subtype="Run",
        name="Morning Run",
        duration_s=3600,
        distance_m=10000,
        source=ActivitySource.intervals_icu,
    )
    session.add(activity)
    await session.commit()

    result = await get_calendar(month=month_str, session=session)
    assert len(result.days) == 1
    day = result.days[0]
    assert day.endurance is not None
    assert len(day.endurance.activities) == 1
    assert day.endurance.activities[0]["type"] == "Run"
    assert day.endurance.activities[0]["duration_s"] == 3600


@pytest.mark.asyncio
async def test_calendar_mixed_venue_types(session):
    today = date.today()
    month_str = f"{today.year}-{today.month:02d}"

    await create_climbing_activity(
        session,
        crag_name="Outdoor Crag",
        crag_country="Germany",
        venue_type=VenueType.outdoor_crag,
        ascents_data=[
            {"route_name": "R1", "grade": "7a", "tick_type": TickType.redpoint, "date": today},
        ],
    )
    await create_climbing_activity(
        session,
        crag_name="Indoor Gym",
        crag_country="Germany",
        venue_type=VenueType.indoor_gym,
        ascents_data=[
            {"grade": "6b", "tick_type": TickType.flash, "date": today},
        ],
    )
    await session.commit()

    result = await get_calendar(month=month_str, session=session)
    assert len(result.days) == 1
    assert result.days[0].climbing.venue_type == "mixed"


# ── Weekly Activity ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_weekly_empty(session):
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    result = await get_weekly(week_start=monday.isoformat(), session=session)
    assert len(result.days) == 7
    assert all(d.climbing_count == 0 for d in result.days)
    assert all(d.endurance_activities == [] for d in result.days)
    assert result.session_streak == 0


@pytest.mark.asyncio
async def test_weekly_mixed_data(session):
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    await create_climbing_activity(
        session,
        crag_name="Crag",
        crag_country="Germany",
        venue_type=VenueType.outdoor_crag,
        ascents_data=[
            {"route_name": "R1", "grade": "7a", "tick_type": TickType.redpoint, "date": monday},
            {"route_name": "R2", "grade": "6c", "tick_type": TickType.flash, "date": monday},
        ],
    )
    activity = Activity(
        intervals_id="test-weekly-1",
        date=monday,
        type="run",
        subtype="Run",
        name="Morning Run",
        duration_s=3600,
        source=ActivitySource.intervals_icu,
    )
    session.add(activity)
    await session.commit()

    result = await get_weekly(week_start=monday.isoformat(), session=session)
    assert len(result.days) == 7

    # Monday should have 2 climbs and 1 endurance
    mon_day = result.days[0]
    assert mon_day.climbing_count == 2
    assert len(mon_day.ascents) == 2
    assert len(mon_day.endurance_activities) == 1
    assert mon_day.endurance_activities[0].type == "Run"

    # Other days should be empty
    for d in result.days[1:]:
        assert d.climbing_count == 0


@pytest.mark.asyncio
async def test_weekly_climbing_only_day(session):
    today = date.today()
    # Use last week to avoid future-date validation
    last_monday = today - timedelta(days=today.weekday() + 7)
    climb_day = last_monday + timedelta(days=2)  # Wednesday of last week

    await create_climbing_activity(
        session,
        crag_name="Crag",
        crag_country="Germany",
        venue_type=VenueType.indoor_gym,
        ascents_data=[
            {"route_name": "Boulder1", "grade": "6a", "tick_type": TickType.onsight, "date": climb_day},
        ],
    )
    await session.commit()

    result = await get_weekly(week_start=last_monday.isoformat(), session=session)
    wed_day = result.days[2]
    assert wed_day.climbing_count == 1
    assert wed_day.endurance_activities == []


@pytest.mark.asyncio
async def test_weekly_session_streak(session):
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    month_start = date(today.year, today.month, 1)

    # Create sessions on 3 different days this month
    for i in range(3):
        d = month_start + timedelta(days=i)
        await create_climbing_activity(
            session,
            crag_name="Crag",
            crag_country="Germany",
            venue_type=VenueType.outdoor_crag,
            ascents_data=[
                {"route_name": f"R{i}", "grade": "6a", "tick_type": TickType.redpoint, "date": d},
            ],
        )
    await session.commit()

    result = await get_weekly(week_start=monday.isoformat(), session=session)
    assert result.session_streak == 3
