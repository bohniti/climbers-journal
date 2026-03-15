"""Tests for stats/dashboard endpoints."""

from datetime import date, timedelta

import pytest

from climbers_journal.models.climbing import TickType, VenueType
from climbers_journal.routers.stats import (
    _build_climbing_stats,
    _build_endurance_stats,
    _build_grade_pyramid,
    _recent_climbing,
    _recent_endurance,
)
from climbers_journal.services.climbing import create_climbing_session


# ── Grade Pyramid ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_grade_pyramid_empty(session):
    result = await _build_grade_pyramid(session)
    assert result == []


@pytest.mark.asyncio
async def test_grade_pyramid_with_sends(session):
    today = date.today()
    await create_climbing_session(
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
    await create_climbing_session(
        session,
        crag_name="Outdoor Crag",
        crag_country="Germany",
        venue_type=VenueType.outdoor_crag,
        ascents_data=[
            {"route_name": "Outdoor Route", "grade": "7a", "tick_type": TickType.redpoint, "date": today},
        ],
    )
    await create_climbing_session(
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
    await create_climbing_session(
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

    await create_climbing_session(
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
    await create_climbing_session(
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
