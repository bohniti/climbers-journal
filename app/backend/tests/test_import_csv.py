from datetime import date

import pytest

from climbers_journal.models.climbing import TickType
from climbers_journal.services.climbing import list_ascents
from climbers_journal.services.import_csv import import_climbing_csv


VALID_HEADER = "date,crag_name,route_name,grade,tick_type,country,venue_type\n"


class TestImportCsv:
    async def test_happy_path(self, session):
        csv = (
            VALID_HEADER
            + "2026-03-01,Frankenjura,Wallstreet,8a,onsight,Germany,outdoor_crag\n"
            + "2026-03-01,Frankenjura,Action Directe,9a,attempt,Germany,outdoor_crag\n"
        )
        result = await import_climbing_csv(session, csv)
        assert result["created"] == 2
        assert result["skipped"] == 0
        assert result["rows_imported"] == 2
        assert result["errors"] == []

        # Verify ascents in DB
        ascents = await list_ascents(session)
        assert len(ascents) == 2

    async def test_dedup_on_reimport(self, session):
        csv = (
            VALID_HEADER
            + "2026-03-01,Frankenjura,Wallstreet,8a,onsight,Germany,outdoor_crag\n"
        )
        await import_climbing_csv(session, csv)
        result = await import_climbing_csv(session, csv)
        assert result["created"] == 0
        assert result["skipped"] == 1

    async def test_invalid_rows_collected(self, session):
        csv = (
            VALID_HEADER
            + "2026-03-01,Frankenjura,Wallstreet,8a,onsight,Germany,outdoor_crag\n"
            + "bad-date,Frankenjura,Route2,7a,flash,Germany,outdoor_crag\n"
            + "2026-03-01,Frankenjura,Route3,7b,INVALID_TICK,Germany,outdoor_crag\n"
        )
        result = await import_climbing_csv(session, csv)
        assert result["created"] == 1
        assert len(result["errors"]) == 2
        assert "invalid date" in result["errors"][0]["reason"]
        assert "invalid tick_type" in result["errors"][1]["reason"]

    async def test_missing_required_column(self, session):
        csv = "date,crag_name,grade\n2026-03-01,Frankenjura,8a\n"
        result = await import_climbing_csv(session, csv)
        assert result["created"] == 0
        assert len(result["errors"]) == 1
        assert "Missing required columns" in result["errors"][0]["reason"]

    async def test_empty_csv(self, session):
        result = await import_climbing_csv(session, "")
        assert result["created"] == 0
        assert len(result["errors"]) == 1

    async def test_outdoor_requires_route_name(self, session):
        csv = (
            VALID_HEADER
            + "2026-03-01,Frankenjura,,8a,onsight,Germany,outdoor_crag\n"
        )
        result = await import_climbing_csv(session, csv)
        assert result["created"] == 0
        assert len(result["errors"]) == 1
        assert "route_name" in result["errors"][0]["reason"]

    async def test_gym_without_route_name(self, session):
        csv = (
            VALID_HEADER
            + "2026-03-01,Boulderhalle,,V4,flash,,indoor_gym\n"
        )
        result = await import_climbing_csv(session, csv)
        assert result["created"] == 1
        assert result["errors"] == []

    async def test_optional_area_column(self, session):
        csv = (
            "date,crag_name,route_name,grade,tick_type,area_name,country\n"
            "2026-03-01,Frankenjura,Wallstreet,8a,onsight,Krottenseer Turm,Germany\n"
        )
        result = await import_climbing_csv(session, csv)
        assert result["created"] == 1
        assert result["errors"] == []

    async def test_invalid_rating(self, session):
        csv = (
            "date,crag_name,route_name,grade,tick_type,rating\n"
            "2026-03-01,Frankenjura,Wallstreet,8a,onsight,7\n"
        )
        result = await import_climbing_csv(session, csv)
        assert result["created"] == 0
        assert "rating" in result["errors"][0]["reason"]

    async def test_future_date_rejected(self, session):
        csv = (
            VALID_HEADER
            + "2099-01-01,Frankenjura,Wallstreet,8a,onsight,Germany,outdoor_crag\n"
        )
        result = await import_climbing_csv(session, csv)
        assert result["created"] == 0
        assert "future" in result["errors"][0]["reason"]

    async def test_multiple_crags(self, session):
        csv = (
            VALID_HEADER
            + "2026-03-01,Frankenjura,Wallstreet,8a,onsight,Germany,outdoor_crag\n"
            + "2026-03-02,El Chorro,Makinodromo,7b+,redpoint,Spain,outdoor_crag\n"
        )
        result = await import_climbing_csv(session, csv)
        assert result["created"] == 2
        assert result["rows_imported"] == 2
