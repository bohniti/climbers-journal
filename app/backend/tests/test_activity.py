"""Tests for the unified Activity model, sport_category(), serialize_activity(), feed, and cascade."""

from datetime import date, timedelta

import pytest

from climbers_journal.models.activity import (
    Activity,
    ActivitySource,
    _SUBTYPE_CATEGORY,
    sport_category,
)
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
from climbers_journal.services.activity import (
    cascade_activity_crag,
    create_climbing_activity,
    get_activity_feed,
    get_or_create_climbing_activity,
    serialize_activity,
)


# ── sport_category() ─────────────────────────────────────────────────


class TestSportCategory:
    def test_all_known_subtypes_mapped(self):
        """Every entry in _SUBTYPE_CATEGORY maps to a known category."""
        known_categories = {"run", "ride", "swim", "winter", "climbing", "water", "fitness", "other"}
        for subtype, category in _SUBTYPE_CATEGORY.items():
            assert category in known_categories, f"{subtype} → {category} is not a known category"

    @pytest.mark.parametrize(
        "subtype,expected",
        [
            ("Run", "run"),
            ("TrailRun", "run"),
            ("VirtualRun", "run"),
            ("Ride", "ride"),
            ("GravelRide", "ride"),
            ("MountainBikeRide", "ride"),
            ("Swim", "swim"),
            ("AlpineSki", "winter"),
            ("BackcountrySki", "winter"),
            ("Snowboard", "winter"),
            ("RockClimbing", "climbing"),
            ("Canoeing", "water"),
            ("Kayaking", "water"),
            ("Hike", "fitness"),
            ("Walk", "fitness"),
            ("Yoga", "fitness"),
            ("WeightTraining", "fitness"),
            ("Badminton", "other"),
            ("Golf", "other"),
        ],
    )
    def test_known_subtypes(self, subtype: str, expected: str):
        assert sport_category(subtype) == expected

    def test_unknown_subtype_returns_other(self):
        assert sport_category("UnknownSport") == "other"

    def test_empty_string_returns_other(self):
        assert sport_category("") == "other"


# ── serialize_activity() ─────────────────────────────────────────────


class TestSerializeActivity:
    def _make_activity(self, **overrides) -> Activity:
        defaults = dict(
            id=1,
            date=date(2026, 3, 10),
            type="run",
            subtype="Run",
            name="Morning Run",
            source=ActivitySource.intervals_icu,
            duration_s=3600,
            distance_m=10000.0,
            elevation_gain_m=150.0,
            avg_hr=145,
            max_hr=175,
            training_load=80.0,
        )
        defaults.update(overrides)
        activity = Activity(**defaults)
        # Ensure ascents relationship is initialized
        if not hasattr(activity, "ascents") or activity.ascents is None:
            activity.ascents = []
        return activity

    def test_endurance_activity(self):
        activity = self._make_activity()
        result = serialize_activity(activity)

        assert result["id"] == 1
        assert result["date"] == "2026-03-10"
        assert result["type"] == "run"
        assert result["subtype"] == "Run"
        assert result["name"] == "Morning Run"
        assert result["source"] == "intervals_icu"
        assert result["duration_s"] == 3600
        assert result["distance_m"] == 10000.0
        assert result["avg_hr"] == 145
        assert result["max_hr"] == 175
        assert result["ascents"] == []
        assert result["ascent_count"] == 0
        assert result["crag_id"] is None
        assert result["crag_name"] is None

    def test_climbing_activity_with_ascents(self):
        activity = self._make_activity(
            id=2,
            type="climbing",
            subtype="RockClimbing",
            name=None,
            source=ActivitySource.manual,
            crag_id=10,
            crag_name="Frankenjura",
            duration_s=None,
            distance_m=None,
            elevation_gain_m=None,
            avg_hr=None,
            max_hr=None,
            training_load=None,
        )
        ascent = Ascent(
            id=100,
            date=date(2026, 3, 10),
            tick_type=TickType.onsight,
            route_name="Wallstreet",
            grade="8a",
            tries=1,
            rating=5,
            notes=None,
            partner=None,
            route_id=50,
            crag_id=10,
            crag_name="Frankenjura",
        )
        activity.ascents = [ascent]

        result = serialize_activity(activity)

        assert result["type"] == "climbing"
        assert result["crag_id"] == 10
        assert result["crag_name"] == "Frankenjura"
        assert result["ascent_count"] == 1
        assert len(result["ascents"]) == 1
        assert result["ascents"][0]["route_name"] == "Wallstreet"
        assert result["ascents"][0]["grade"] == "8a"
        assert result["ascents"][0]["tick_type"] == "onsight"

    def test_merged_activity_climbing_with_hr(self):
        """A climbing activity that also has HR data from a linked sync."""
        activity = self._make_activity(
            id=3,
            type="climbing",
            subtype="RockClimbing",
            source=ActivitySource.intervals_icu,
            crag_id=10,
            crag_name="Frankenjura",
            duration_s=7200,
            avg_hr=130,
            max_hr=165,
            training_load=90.0,
            distance_m=None,
            elevation_gain_m=None,
        )
        activity.ascents = []

        result = serialize_activity(activity)

        assert result["type"] == "climbing"
        assert result["duration_s"] == 7200
        assert result["avg_hr"] == 130
        assert result["crag_id"] == 10
        assert result["ascents"] == []


# ── get_or_create_climbing_activity() ────────────────────────────────


class TestGetOrCreateClimbingActivity:
    @pytest.mark.asyncio
    async def test_creates_new(self, session):
        crag = Crag(
            name="Test Crag",
            name_normalized=normalize_name("Test Crag"),
            venue_type=VenueType.outdoor_crag,
            default_grade_sys=GradeSystem.french,
        )
        session.add(crag)
        await session.flush()

        activity, created = await get_or_create_climbing_activity(
            session,
            activity_date=date(2026, 3, 10),
            crag_id=crag.id,
            crag_name="Test Crag",
        )
        assert created is True
        assert activity.type == "climbing"
        assert activity.subtype == "RockClimbing"
        assert activity.source == ActivitySource.manual
        assert activity.crag_id == crag.id

    @pytest.mark.asyncio
    async def test_finds_existing(self, session):
        crag = Crag(
            name="Test Crag",
            name_normalized=normalize_name("Test Crag"),
            venue_type=VenueType.outdoor_crag,
            default_grade_sys=GradeSystem.french,
        )
        session.add(crag)
        await session.flush()

        a1, created1 = await get_or_create_climbing_activity(
            session, activity_date=date(2026, 3, 10), crag_id=crag.id
        )
        a2, created2 = await get_or_create_climbing_activity(
            session, activity_date=date(2026, 3, 10), crag_id=crag.id
        )
        assert created1 is True
        assert created2 is False
        assert a1.id == a2.id


# ── cascade_activity_crag() ──────────────────────────────────────────


class TestCascadeActivityCrag:
    @pytest.mark.asyncio
    async def test_cascade_updates_ascents(self, session):
        """Cascading crag change updates all ascents in the activity."""
        crag1 = Crag(
            name="Old Crag",
            name_normalized=normalize_name("Old Crag"),
            venue_type=VenueType.outdoor_crag,
            default_grade_sys=GradeSystem.french,
        )
        crag2 = Crag(
            name="New Crag",
            name_normalized=normalize_name("New Crag"),
            venue_type=VenueType.outdoor_crag,
            default_grade_sys=GradeSystem.french,
        )
        session.add_all([crag1, crag2])
        await session.flush()

        result = await create_climbing_activity(
            session,
            crag_name="Old Crag",
            venue_type=VenueType.outdoor_crag,
            ascents_data=[
                {"route_name": "R1", "grade": "6a", "tick_type": "redpoint", "date": "2026-03-10"},
                {"route_name": "R2", "grade": "6b", "tick_type": "flash", "date": "2026-03-10"},
            ],
        )
        await session.flush()

        updated_count = await cascade_activity_crag(
            session,
            activity_id=result["activity_id"],
            new_crag_id=crag2.id,
            new_crag_name="New Crag",
        )
        assert updated_count == 2


# ── get_activity_feed() ──────────────────────────────────────────────


class TestActivityFeed:
    @pytest.mark.asyncio
    async def test_feed_returns_all_types(self, session):
        """Feed includes both climbing and endurance activities."""
        # Climbing activity
        await create_climbing_activity(
            session,
            crag_name="Crag",
            crag_country="Germany",
            venue_type=VenueType.outdoor_crag,
            ascents_data=[
                {"route_name": "R1", "grade": "7a", "tick_type": "redpoint", "date": "2026-03-10"},
            ],
        )
        # Endurance activity
        endurance = Activity(
            intervals_id="feed-1",
            date=date(2026, 3, 11),
            type="run",
            subtype="Run",
            name="Morning Run",
            duration_s=3600,
            source=ActivitySource.intervals_icu,
        )
        session.add(endurance)
        await session.flush()

        feed = await get_activity_feed(session)
        assert len(feed) == 2
        types = {item["type"] for item in feed}
        assert types == {"climbing", "run"}

    @pytest.mark.asyncio
    async def test_feed_ordered_by_date_desc(self, session):
        for i in range(3):
            a = Activity(
                intervals_id=f"order-{i}",
                date=date(2026, 3, 1) + timedelta(days=i),
                type="run",
                subtype="Run",
                name=f"Run {i}",
                duration_s=3600,
                source=ActivitySource.intervals_icu,
            )
            session.add(a)
        await session.flush()

        feed = await get_activity_feed(session)
        dates = [item["date"] for item in feed]
        assert dates == sorted(dates, reverse=True)

    @pytest.mark.asyncio
    async def test_feed_filter_climbing(self, session):
        await create_climbing_activity(
            session,
            crag_name="Crag",
            ascents_data=[
                {"route_name": "R1", "grade": "6a", "tick_type": "redpoint", "date": "2026-03-10"},
            ],
        )
        session.add(Activity(
            intervals_id="f-1",
            date=date(2026, 3, 11),
            type="run",
            subtype="Run",
            duration_s=3600,
            source=ActivitySource.intervals_icu,
        ))
        await session.flush()

        feed = await get_activity_feed(session, feed_type="climbing")
        assert len(feed) == 1
        assert feed[0]["type"] == "climbing"

    @pytest.mark.asyncio
    async def test_feed_filter_endurance(self, session):
        await create_climbing_activity(
            session,
            crag_name="Crag",
            ascents_data=[
                {"route_name": "R1", "grade": "6a", "tick_type": "redpoint", "date": "2026-03-10"},
            ],
        )
        session.add(Activity(
            intervals_id="f-2",
            date=date(2026, 3, 11),
            type="run",
            subtype="Run",
            duration_s=3600,
            source=ActivitySource.intervals_icu,
        ))
        await session.flush()

        feed = await get_activity_feed(session, feed_type="endurance")
        assert len(feed) == 1
        assert feed[0]["type"] == "run"

    @pytest.mark.asyncio
    async def test_feed_pagination(self, session):
        for i in range(5):
            session.add(Activity(
                intervals_id=f"page-{i}",
                date=date(2026, 3, 1) + timedelta(days=i),
                type="run",
                subtype="Run",
                duration_s=3600,
                source=ActivitySource.intervals_icu,
            ))
        await session.flush()

        page1 = await get_activity_feed(session, offset=0, limit=2)
        page2 = await get_activity_feed(session, offset=2, limit=2)
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0]["id"] != page2[0]["id"]

    @pytest.mark.asyncio
    async def test_feed_climbing_includes_ascents(self, session):
        """Climbing activities in the feed include nested ascent data."""
        await create_climbing_activity(
            session,
            crag_name="Frankenjura",
            crag_country="Germany",
            venue_type=VenueType.outdoor_crag,
            ascents_data=[
                {"route_name": "Wallstreet", "grade": "8a", "tick_type": "onsight", "date": "2026-03-10"},
                {"route_name": "Sautanz", "grade": "7c+", "tick_type": "redpoint", "date": "2026-03-10"},
            ],
        )
        await session.flush()

        feed = await get_activity_feed(session)
        assert len(feed) == 1
        item = feed[0]
        assert item["type"] == "climbing"
        assert item["ascent_count"] == 2
        assert len(item["ascents"]) == 2
        route_names = {a["route_name"] for a in item["ascents"]}
        assert route_names == {"Wallstreet", "Sautanz"}
