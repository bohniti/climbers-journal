"""Tests for endurance activity sync service."""

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from sqlmodel import select

from climbers_journal.models.activity import Activity, ActivitySource
from climbers_journal.models.climbing import Crag, GradeSystem, VenueType, normalize_name
from climbers_journal.services.sync import (
    _month_ranges,
    _parse_activity,
    list_activities,
    sync_activities,
    update_activity,
    upsert_activity,
)


# ── Unit Tests ─────────────────────────────────────────────────────────


class TestMonthRanges:
    def test_single_month(self):
        ranges = _month_ranges(date(2026, 1, 5), date(2026, 1, 25))
        assert ranges == [(date(2026, 1, 5), date(2026, 1, 25))]

    def test_multi_month(self):
        ranges = _month_ranges(date(2026, 1, 15), date(2026, 3, 10))
        assert len(ranges) == 3
        assert ranges[0] == (date(2026, 1, 15), date(2026, 1, 31))
        assert ranges[1] == (date(2026, 2, 1), date(2026, 2, 28))
        assert ranges[2] == (date(2026, 3, 1), date(2026, 3, 10))

    def test_same_day(self):
        ranges = _month_ranges(date(2026, 6, 15), date(2026, 6, 15))
        assert ranges == [(date(2026, 6, 15), date(2026, 6, 15))]


class TestParseActivity:
    def test_basic_fields(self):
        raw = {
            "id": "i12345",
            "start_date_local": "2026-03-10T08:00:00",
            "type": "Run",
            "name": "Morning Run",
            "moving_time": 3600,
            "distance": 10000.0,
            "total_elevation_gain": 150.0,
            "average_heartrate": 145,
            "max_heartrate": 175,
            "icu_training_load": 85.0,
            "icu_intensity": 0.72,
        }
        result = _parse_activity(raw)
        assert result["intervals_id"] == "i12345"
        assert result["date"] == date(2026, 3, 10)
        assert result["type"] == "run"
        assert result["subtype"] == "Run"
        assert result["name"] == "Morning Run"
        assert result["duration_s"] == 3600
        assert result["distance_m"] == 10000.0
        assert result["elevation_gain_m"] == 150.0
        assert result["avg_hr"] == 145
        assert result["max_hr"] == 175
        assert result["training_load"] == 85.0
        assert result["intensity"] == 0.72
        assert result["source"] == ActivitySource.intervals_icu
        assert result["raw_data"] == raw

    def test_missing_optional_fields(self):
        raw = {"id": "i999", "type": "Ride", "moving_time": 7200}
        result = _parse_activity(raw)
        assert result["intervals_id"] == "i999"
        assert result["type"] == "ride"
        assert result["subtype"] == "Ride"
        assert result["duration_s"] == 7200
        assert result["distance_m"] is None
        assert result["avg_hr"] is None


# ── DB Tests ───────────────────────────────────────────────────────────


def _make_activity_data(**overrides) -> dict:
    defaults = {
        "intervals_id": "i100",
        "date": date(2026, 3, 10),
        "type": "run",
        "subtype": "Run",
        "name": "Test Run",
        "duration_s": 3600,
        "distance_m": 10000.0,
        "elevation_gain_m": 100.0,
        "avg_hr": 140,
        "max_hr": 170,
        "training_load": 80.0,
        "intensity": 0.7,
        "source": ActivitySource.intervals_icu,
        "raw_data": {"id": "i100", "type": "Run"},
    }
    defaults.update(overrides)
    return defaults


class TestUpsertActivity:
    @pytest.mark.asyncio
    async def test_insert_new(self, session):
        data = _make_activity_data()
        activity, created = await upsert_activity(session, data)
        await session.flush()
        assert created is True
        assert activity.intervals_id == "i100"
        assert activity.type == "run"
        assert activity.duration_s == 3600

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self, session):
        data = _make_activity_data()
        _, created1 = await upsert_activity(session, data)
        await session.flush()
        assert created1 is True

        # Upsert with same intervals_id but updated fields
        updated_data = _make_activity_data(name="Updated Run", duration_s=4000)
        activity, created2 = await upsert_activity(session, updated_data)
        await session.flush()
        assert created2 is False
        assert activity.name == "Updated Run"
        assert activity.duration_s == 4000

    @pytest.mark.asyncio
    async def test_upsert_idempotent(self, session):
        data = _make_activity_data()
        await upsert_activity(session, data)
        await session.flush()
        await upsert_activity(session, data)
        await session.flush()

        result = await session.exec(select(Activity))
        activities = list(result.all())
        assert len(activities) == 1


class TestListActivities:
    @pytest.mark.asyncio
    async def test_list_empty(self, session):
        result = await list_activities(session)
        assert result == []

    @pytest.mark.asyncio
    async def test_list_with_filters(self, session):
        run = _make_activity_data(intervals_id="r1", type="run", subtype="Run", date=date(2026, 3, 10))
        ride = _make_activity_data(intervals_id="r2", type="ride", subtype="Ride", date=date(2026, 3, 11))
        await upsert_activity(session, run)
        await upsert_activity(session, ride)
        await session.flush()

        # Filter by type
        runs = await list_activities(session, activity_type="run")
        assert len(runs) == 1
        assert runs[0]["type"] == "run"

        # Filter by date range
        result = await list_activities(
            session, date_from=date(2026, 3, 11), date_to=date(2026, 3, 11)
        )
        assert len(result) == 1
        assert result[0]["type"] == "ride"

    @pytest.mark.asyncio
    async def test_list_pagination(self, session):
        for i in range(5):
            data = _make_activity_data(
                intervals_id=f"p{i}",
                date=date(2026, 3, 1) + timedelta(days=i),
            )
            await upsert_activity(session, data)
        await session.flush()

        page1 = await list_activities(session, offset=0, limit=2)
        assert len(page1) == 2

        page2 = await list_activities(session, offset=2, limit=2)
        assert len(page2) == 2

        # Date desc ordering: first page should have later dates
        assert page1[0]["date"] > page2[0]["date"]


class TestUpdateActivity:
    @pytest.mark.asyncio
    async def test_update_name_and_notes(self, session):
        data = _make_activity_data()
        activity, _ = await upsert_activity(session, data)
        await session.flush()

        updated = await update_activity(
            session, activity.id, name="New Name", notes="Some notes"
        )
        assert updated is not None
        assert updated.name == "New Name"
        assert updated.notes == "Some notes"

    @pytest.mark.asyncio
    async def test_update_not_found(self, session):
        result = await update_activity(session, 99999, name="nope")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_crag_id_denormalizes_name(self, session):
        """Changing crag_id should also update crag_name."""
        crag = Crag(
            name="Test Crag",
            name_normalized=normalize_name("Test Crag"),
            venue_type=VenueType.outdoor_crag,
            default_grade_sys=GradeSystem.french,
        )
        session.add(crag)
        await session.flush()

        data = _make_activity_data(type="climbing", subtype="RockClimbing")
        activity, _ = await upsert_activity(session, data)
        await session.flush()

        updated = await update_activity(session, activity.id, crag_id=crag.id)
        assert updated is not None
        assert updated.crag_id == crag.id
        assert updated.crag_name == "Test Crag"


class TestSyncActivities:
    @pytest.mark.asyncio
    async def test_sync_short_range(self, session):
        """Sync a short range (< 90 days) — single chunk."""
        mock_activities = [
            {"id": "a1", "start_date_local": "2026-03-01T08:00:00", "type": "Run",
             "moving_time": 3600, "distance": 10000.0},
            {"id": "a2", "start_date_local": "2026-03-02T09:00:00", "type": "Ride",
             "moving_time": 7200, "distance": 40000.0},
        ]
        with patch(
            "climbers_journal.services.sync.intervals.get_activities",
            new_callable=AsyncMock,
            return_value=mock_activities,
        ):
            result = await sync_activities(
                session,
                oldest=date(2026, 3, 1),
                newest=date(2026, 3, 10),
            )

        assert result["total_created"] == 2
        assert result["total_updated"] == 0
        assert len(result["synced"]) == 1
        assert len(result["failed"]) == 0

    @pytest.mark.asyncio
    async def test_sync_idempotent(self, session):
        """Running sync twice with same data doesn't create duplicates."""
        mock_activities = [
            {"id": "a1", "start_date_local": "2026-03-01T08:00:00", "type": "Run",
             "moving_time": 3600},
        ]
        with patch(
            "climbers_journal.services.sync.intervals.get_activities",
            new_callable=AsyncMock,
            return_value=mock_activities,
        ):
            result1 = await sync_activities(
                session, oldest=date(2026, 3, 1), newest=date(2026, 3, 10),
            )
            result2 = await sync_activities(
                session, oldest=date(2026, 3, 1), newest=date(2026, 3, 10),
            )

        assert result1["total_created"] == 1
        assert result2["total_created"] == 0
        assert result2["total_updated"] == 1

    @pytest.mark.asyncio
    async def test_sync_429_retry(self, session):
        """Retries on 429 with exponential backoff."""
        mock_response = httpx.Response(429, request=httpx.Request("GET", "https://example.com"))
        call_count = 0

        async def flaky_get_activities(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise httpx.HTTPStatusError("rate limited", request=mock_response.request, response=mock_response)
            return [{"id": "retry1", "start_date_local": "2026-03-01T08:00:00",
                     "type": "Run", "moving_time": 1800}]

        with patch(
            "climbers_journal.services.sync.intervals.get_activities",
            side_effect=flaky_get_activities,
        ), patch("climbers_journal.services.sync.asyncio.sleep", new_callable=AsyncMock):
            result = await sync_activities(
                session, oldest=date(2026, 3, 1), newest=date(2026, 3, 10),
            )

        assert call_count == 3
        assert result["total_created"] == 1

    @pytest.mark.asyncio
    async def test_sync_partial_failure(self, session):
        """Reports partial failures when one month chunk fails."""
        call_count = 0
        months = ["01", "02", "03", "04"]

        async def partial_failure(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("Server error")
            month = months[call_count - 1] if call_count <= len(months) else "01"
            return [{"id": f"pf{call_count}", "start_date_local": f"2026-{month}-15T08:00:00",
                     "type": "Run", "moving_time": 3600}]

        with patch(
            "climbers_journal.services.sync.intervals.get_activities",
            side_effect=partial_failure,
        ):
            # Use > 90 day range to trigger month-chunked sync
            result = await sync_activities(
                session,
                oldest=date(2026, 1, 1),
                newest=date(2026, 4, 30),
            )

        assert len(result["synced"]) == 3
        assert len(result["failed"]) == 1
        assert result["failed"][0]["month"] == "2026-02"
        assert "Server error" in result["failed"][0]["error"]
