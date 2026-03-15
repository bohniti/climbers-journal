"""intervals.icu API client."""

import os
from datetime import date, timedelta

import httpx

BASE_URL = "https://intervals.icu/api/v1"


def _auth() -> tuple[str, str]:
    api_key = os.getenv("INTERVALS_API_KEY", "")
    return ("API_KEY", api_key)


def _athlete_id() -> str:
    return os.getenv("INTERVALS_ATHLETE_ID", "")


async def get_activities(
    oldest: str | None = None,
    newest: str | None = None,
) -> list[dict]:
    """Fetch recent activities. Dates as YYYY-MM-DD strings."""
    today = date.today()
    params: dict[str, str] = {
        "oldest": oldest or (today - timedelta(days=30)).isoformat(),
        "newest": newest or today.isoformat(),
    }
    async with httpx.AsyncClient(auth=_auth()) as client:
        resp = await client.get(
            f"{BASE_URL}/athlete/{_athlete_id()}/activities",
            params=params,
        )
        resp.raise_for_status()
        return resp.json()


async def get_latest_activity() -> dict:
    """Fetch the most recent activity (last 7 days)."""
    today = date.today()
    activities = await get_activities(
        oldest=(today - timedelta(days=7)).isoformat(),
        newest=today.isoformat(),
    )
    return activities[-1] if activities else {}


async def get_wellness(oldest: str | None = None, newest: str | None = None) -> list[dict]:
    """Fetch wellness data. Dates as YYYY-MM-DD strings."""
    today = date.today()
    params: dict[str, str] = {
        "oldest": oldest or (today - timedelta(days=30)).isoformat(),
        "newest": newest or today.isoformat(),
    }
    async with httpx.AsyncClient(auth=_auth()) as client:
        resp = await client.get(
            f"{BASE_URL}/athlete/{_athlete_id()}/wellness",
            params=params,
        )
        resp.raise_for_status()
        return resp.json()
