"""Tests for the parse_climbing_session tool."""

from __future__ import annotations

import json

import pytest

from climbers_journal.models.climbing import (
    Crag,
    GradeSystem,
    Route,
    VenueType,
    normalize_name,
)
from climbers_journal.tools.record import _build_draft, handle


# ── _build_draft without DB ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_build_draft_basic_no_db():
    """Draft builds without a DB session (all items marked new)."""
    args = {
        "crag_name": "Frankenjura",
        "crag_country": "Germany",
        "venue_type": "outdoor_crag",
        "date": "2026-03-15",
        "ascents": [
            {
                "route_name": "Wallstreet",
                "grade": "8a",
                "tick_type": "onsight",
                "tries": 1,
            },
            {
                "route_name": "Action Directe",
                "grade": "9a",
                "tick_type": "attempt",
                "tries": 2,
                "notes": "fell at crux",
            },
        ],
    }
    draft = await _build_draft(args, session=None)

    assert draft["type"] == "climbing_session"
    assert draft["crag"]["name"] == "Frankenjura"
    assert draft["crag"]["country"] == "Germany"
    assert draft["crag"]["status"] == "new"
    assert draft["crag"]["grade_system"] == "uiaa"  # Germany → UIAA
    assert draft["date"] == "2026-03-15"
    assert len(draft["ascents"]) == 2

    a0 = draft["ascents"][0]
    assert a0["route_name"] == "Wallstreet"
    assert a0["grade"] == "8a"
    assert a0["tick_type"] == "onsight"
    assert a0["tries"] == 1

    a1 = draft["ascents"][1]
    assert a1["route_name"] == "Action Directe"
    assert a1["tick_type"] == "attempt"
    assert a1["notes"] == "fell at crux"


@pytest.mark.asyncio
async def test_build_draft_gym_no_route_names():
    """Gym sessions can omit route names."""
    args = {
        "crag_name": "Boulderhalle Wien",
        "venue_type": "indoor_gym",
        "ascents": [
            {"grade": "V5", "tick_type": "flash"},
            {"grade": "V6", "tick_type": "attempt"},
        ],
    }
    draft = await _build_draft(args, session=None)
    assert draft["crag"]["venue_type"] == "indoor_gym"
    for a in draft["ascents"]:
        assert "route_name" not in a
        assert a["grade"] is not None


@pytest.mark.asyncio
async def test_build_draft_default_grade_system():
    """No country → defaults to french grade system."""
    args = {
        "crag_name": "Mystery Crag",
        "ascents": [{"route_name": "Test", "grade": "7a", "tick_type": "redpoint"}],
    }
    draft = await _build_draft(args, session=None)
    assert draft["crag"]["grade_system"] == "french"


# ── _build_draft with DB (existing crag/routes) ─────────────────────


@pytest.mark.asyncio
async def test_build_draft_finds_existing_crag(session):
    """Draft marks crag as 'existing' when it's in the DB."""
    crag = Crag(
        name="Frankenjura",
        name_normalized=normalize_name("Frankenjura"),
        country="Germany",
        venue_type=VenueType.outdoor_crag,
        default_grade_sys=GradeSystem.uiaa,
    )
    session.add(crag)
    await session.flush()

    args = {
        "crag_name": "frankenjura",  # lowercase — should still match
        "ascents": [{"route_name": "TestRoute", "grade": "7a", "tick_type": "redpoint"}],
    }
    draft = await _build_draft(args, session=session)
    assert draft["crag"]["status"] == "existing"
    assert draft["crag"]["country"] == "Germany"


@pytest.mark.asyncio
async def test_build_draft_finds_existing_route(session):
    """Draft marks route as 'existing' and uses its stored grade."""
    crag = Crag(
        name="Frankenjura",
        name_normalized=normalize_name("Frankenjura"),
        country="Germany",
        venue_type=VenueType.outdoor_crag,
        default_grade_sys=GradeSystem.uiaa,
    )
    session.add(crag)
    await session.flush()

    route = Route(
        name="Wallstreet",
        name_normalized=normalize_name("Wallstreet"),
        grade="8a",
        grade_system=GradeSystem.french,
        crag_id=crag.id,
    )
    session.add(route)
    await session.flush()

    args = {
        "crag_name": "Frankenjura",
        "ascents": [
            {"route_name": "wallstreet", "tick_type": "onsight"},  # no grade provided
        ],
    }
    draft = await _build_draft(args, session=session)

    a = draft["ascents"][0]
    assert a["route_status"] == "existing"
    assert a["route_id"] == route.id
    assert a["grade"] == "8a"  # inherited from DB


@pytest.mark.asyncio
async def test_build_draft_new_route_at_existing_crag(session):
    """Route not in DB is marked 'new'."""
    crag = Crag(
        name="Frankenjura",
        name_normalized=normalize_name("Frankenjura"),
        country="Germany",
        venue_type=VenueType.outdoor_crag,
        default_grade_sys=GradeSystem.uiaa,
    )
    session.add(crag)
    await session.flush()

    args = {
        "crag_name": "Frankenjura",
        "ascents": [
            {"route_name": "Brand New Route", "grade": "7c+", "tick_type": "redpoint"},
        ],
    }
    draft = await _build_draft(args, session=session)

    a = draft["ascents"][0]
    assert a["route_status"] == "new"
    assert "route_id" not in a
    assert a["grade"] == "7c+"


# ── handle() integration ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_returns_none_for_unknown_tool():
    """Unknown tool names return None."""
    result = await handle("unknown_tool", {}, {})
    assert result is None


@pytest.mark.asyncio
async def test_handle_sets_draft_card_on_context():
    """handle() sets context['draft_card'] for the chat endpoint to surface."""
    context: dict = {}
    args = {
        "crag_name": "Test Crag",
        "ascents": [{"route_name": "R1", "grade": "6a", "tick_type": "flash"}],
    }
    result = await handle("parse_climbing_session", args, context)

    assert result is not None
    parsed = json.loads(result)
    assert "draft" in parsed
    assert "summary" in parsed

    # draft_card is set on context
    assert "draft_card" in context
    assert context["draft_card"]["crag"]["name"] == "Test Crag"
    assert len(context["draft_card"]["ascents"]) == 1
