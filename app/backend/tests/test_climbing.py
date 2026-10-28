from datetime import date, timedelta

import pytest
from fastapi import HTTPException

from climbers_journal.models.climbing import (
    GradeSystem,
    RouteStyle,
    TickType,
    VenueType,
    normalize_name,
    suggest_grade_system,
)
from climbers_journal.services.activity import (
    create_ascent,
    create_climbing_activity,
    create_or_find_area,
    create_or_find_crag,
    create_or_find_route,
    delete_ascent,
    get_ascent,
    list_ascents,
    list_crags,
    update_ascent,
)


# ── normalize_name ─────────────────────────────────────────────────────


class TestNormalizeName:
    def test_basic(self):
        assert normalize_name("Frankenjura") == "frankenjura"

    def test_strips_whitespace(self):
        assert normalize_name("  Frankenjura  ") == "frankenjura"

    def test_removes_diacritics(self):
        assert normalize_name("Bühler") == "buhler"
        assert normalize_name("Céüse") == "ceuse"

    def test_preserves_numbers(self):
        assert normalize_name("Sector 7b") == "sector 7b"


# ── suggest_grade_system ───────────────────────────────────────────────


class TestSuggestGradeSystem:
    def test_germany_uiaa(self):
        assert suggest_grade_system("Germany") == GradeSystem.uiaa

    def test_usa_yds(self):
        assert suggest_grade_system("USA") == GradeSystem.yds

    def test_france_french(self):
        assert suggest_grade_system("France") == GradeSystem.french

    def test_unknown_defaults_to_french(self):
        assert suggest_grade_system("Mars") == GradeSystem.french

    def test_none_defaults_to_french(self):
        assert suggest_grade_system(None) == GradeSystem.french


# ── Crag CRUD ──────────────────────────────────────────────────────────


class TestCragCrud:
    async def test_create_crag(self, session):
        crag, created = await create_or_find_crag(
            session, name="Frankenjura", country="Germany"
        )
        assert created is True
        assert crag.id is not None
        assert crag.name == "Frankenjura"
        assert crag.default_grade_sys == GradeSystem.uiaa  # auto-suggested

    async def test_find_existing_crag(self, session):
        crag1, _ = await create_or_find_crag(session, name="Frankenjura")
        crag2, created = await create_or_find_crag(session, name="frankenjura")
        assert created is False
        assert crag1.id == crag2.id

    async def test_find_with_diacritics(self, session):
        crag1, _ = await create_or_find_crag(session, name="Céüse")
        crag2, created = await create_or_find_crag(session, name="Ceuse")
        assert created is False
        assert crag1.id == crag2.id

    async def test_list_crags(self, session):
        await create_or_find_crag(session, name="B Crag")
        await create_or_find_crag(session, name="A Crag")
        await session.flush()
        crags = await list_crags(session)
        assert len(crags) == 2
        assert crags[0].name == "A Crag"  # sorted by name

    async def test_list_crags_pagination(self, session):
        for i in range(5):
            await create_or_find_crag(session, name=f"Crag {i}")
        await session.flush()
        page = await list_crags(session, offset=2, limit=2)
        assert len(page) == 2


# ── Area CRUD ──────────────────────────────────────────────────────────


class TestAreaCrud:
    async def test_create_area(self, session):
        crag, _ = await create_or_find_crag(session, name="Frankenjura")
        area, created = await create_or_find_area(
            session, name="Krottenseer Turm", crag_id=crag.id
        )
        assert created is True
        assert area.crag_id == crag.id

    async def test_find_existing_area(self, session):
        crag, _ = await create_or_find_crag(session, name="Frankenjura")
        a1, _ = await create_or_find_area(
            session, name="Krottenseer Turm", crag_id=crag.id
        )
        a2, created = await create_or_find_area(
            session, name="krottenseer turm", crag_id=crag.id
        )
        assert created is False
        assert a1.id == a2.id


# ── Route CRUD ─────────────────────────────────────────────────────────


class TestRouteCrud:
    async def test_create_route(self, session):
        crag, _ = await create_or_find_crag(
            session, name="Frankenjura", country="Germany"
        )
        route, created = await create_or_find_route(
            session, name="Action Directe", grade="9a", crag_id=crag.id
        )
        assert created is True
        assert route.grade == "9a"
        assert route.grade_system == GradeSystem.uiaa  # inherited from crag

    async def test_find_existing_route(self, session):
        crag, _ = await create_or_find_crag(session, name="Frankenjura")
        r1, _ = await create_or_find_route(
            session, name="Action Directe", grade="9a", crag_id=crag.id
        )
        r2, created = await create_or_find_route(
            session, name="action directe", grade="9a", crag_id=crag.id
        )
        assert created is False
        assert r1.id == r2.id


# ── Ascent CRUD ────────────────────────────────────────────────────────


class TestAscentCrud:
    async def _make_crag_and_route(self, session):
        crag, _ = await create_or_find_crag(
            session, name="Frankenjura", country="Germany"
        )
        route, _ = await create_or_find_route(
            session, name="Wallstreet", grade="8a", crag_id=crag.id
        )
        return crag, route

    async def test_create_ascent(self, session):
        crag, route = await self._make_crag_and_route(session)
        ascent = await create_ascent(
            session,
            ascent_date=date(2026, 3, 10),
            tick_type=TickType.onsight,
            crag_id=crag.id,
            route_id=route.id,
        )
        assert ascent.id is not None
        assert ascent.crag_name == "Frankenjura"
        assert ascent.route_name == "Wallstreet"
        assert ascent.grade == "8a"

    async def test_duplicate_ascent_rejected(self, session):
        crag, route = await self._make_crag_and_route(session)
        await create_ascent(
            session,
            ascent_date=date(2026, 3, 10),
            tick_type=TickType.onsight,
            crag_id=crag.id,
            route_id=route.id,
        )
        with pytest.raises(HTTPException) as exc_info:
            await create_ascent(
                session,
                ascent_date=date(2026, 3, 10),
                tick_type=TickType.onsight,
                crag_id=crag.id,
                route_id=route.id,
            )
        assert exc_info.value.status_code == 409

    async def test_future_date_rejected(self, session):
        crag, route = await self._make_crag_and_route(session)
        with pytest.raises(HTTPException) as exc_info:
            await create_ascent(
                session,
                ascent_date=date.today() + timedelta(days=1),
                tick_type=TickType.redpoint,
                crag_id=crag.id,
                route_id=route.id,
            )
        assert exc_info.value.status_code == 422

    async def test_outdoor_requires_route(self, session):
        crag, _ = await self._make_crag_and_route(session)
        with pytest.raises(HTTPException) as exc_info:
            await create_ascent(
                session,
                ascent_date=date(2026, 3, 10),
                tick_type=TickType.redpoint,
                crag_id=crag.id,
                route_id=None,
            )
        assert exc_info.value.status_code == 422

    async def test_gym_ascent_without_route(self, session):
        gym, _ = await create_or_find_crag(
            session, name="Boulderhalle", venue_type=VenueType.indoor_gym
        )
        ascent = await create_ascent(
            session,
            ascent_date=date(2026, 3, 10),
            tick_type=TickType.flash,
            crag_id=gym.id,
            route_id=None,
            grade="V6",
        )
        assert ascent.grade == "V6"
        assert ascent.route_id is None

    async def test_get_ascent(self, session):
        crag, route = await self._make_crag_and_route(session)
        ascent = await create_ascent(
            session,
            ascent_date=date(2026, 3, 10),
            tick_type=TickType.redpoint,
            crag_id=crag.id,
            route_id=route.id,
        )
        found = await get_ascent(session, ascent.id)
        assert found is not None
        assert found.id == ascent.id

    async def test_update_ascent(self, session):
        crag, route = await self._make_crag_and_route(session)
        ascent = await create_ascent(
            session,
            ascent_date=date(2026, 3, 10),
            tick_type=TickType.attempt,
            crag_id=crag.id,
            route_id=route.id,
        )
        updated = await update_ascent(
            session, ascent.id, tick_type=TickType.redpoint, rating=5
        )
        assert updated.tick_type == TickType.redpoint
        assert updated.rating == 5

    async def test_delete_ascent(self, session):
        crag, route = await self._make_crag_and_route(session)
        ascent = await create_ascent(
            session,
            ascent_date=date(2026, 3, 10),
            tick_type=TickType.redpoint,
            crag_id=crag.id,
            route_id=route.id,
        )
        await delete_ascent(session, ascent.id)
        assert await get_ascent(session, ascent.id) is None

    async def test_list_ascents_with_filters(self, session):
        crag, route = await self._make_crag_and_route(session)
        await create_ascent(
            session,
            ascent_date=date(2026, 3, 1),
            tick_type=TickType.onsight,
            crag_id=crag.id,
            route_id=route.id,
        )
        await create_ascent(
            session,
            ascent_date=date(2026, 3, 10),
            tick_type=TickType.attempt,
            crag_id=crag.id,
            route_id=route.id,
        )
        # Filter by tick_type
        onsights = await list_ascents(session, tick_type=TickType.onsight)
        assert len(onsights) == 1
        # Filter by date range
        march = await list_ascents(
            session, date_from=date(2026, 3, 1), date_to=date(2026, 3, 31)
        )
        assert len(march) == 2


# ── Bulk Session Create ────────────────────────────────────────────────


class TestClimbingSession:
    async def test_create_session(self, session):
        result = await create_climbing_activity(
            session,
            crag_name="Frankenjura",
            crag_country="Germany",
            ascents_data=[
                {
                    "route_name": "Wallstreet",
                    "grade": "8a",
                    "tick_type": "onsight",
                    "date": "2026-03-10",
                    "tries": 1,
                },
                {
                    "route_name": "Action Directe",
                    "grade": "9a",
                    "tick_type": "attempt",
                    "date": "2026-03-10",
                    "tries": 3,
                },
            ],
        )
        assert result["crag_created"] is True
        assert result["ascents_created"] == 2
        assert result["ascents_skipped"] == 0

    async def test_session_dedup(self, session):
        data = [
            {
                "route_name": "Wallstreet",
                "grade": "8a",
                "tick_type": "onsight",
                "date": "2026-03-10",
            },
        ]
        await create_climbing_activity(
            session, crag_name="Frankenjura", ascents_data=data
        )
        result = await create_climbing_activity(
            session, crag_name="Frankenjura", ascents_data=data
        )
        assert result["crag_created"] is False
        assert result["ascents_created"] == 0
        assert result["ascents_skipped"] == 1

    async def test_gym_session(self, session):
        result = await create_climbing_activity(
            session,
            crag_name="Boulderhalle Wien",
            venue_type=VenueType.indoor_gym,
            ascents_data=[
                {
                    "grade": "V4",
                    "tick_type": "flash",
                    "date": "2026-03-10",
                },
                {
                    "grade": "V6",
                    "tick_type": "redpoint",
                    "date": "2026-03-10",
                },
            ],
        )
        assert result["ascents_created"] == 2
