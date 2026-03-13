"""intervals.icu API client."""

import os

import httpx

BASE_URL = "https://intervals.icu/api/v1"


def _auth() -> tuple[str, str]:
    api_key = os.getenv("INTERVALS_API_KEY", "")
    return ("API_KEY", api_key)


def _athlete_id() -> str:
    return os.getenv("INTERVALS_ATHLETE_ID", "")


async def get_activities(limit: int = 10) -> list[dict]:
    """Fetch recent activities."""
    async with httpx.AsyncClient(auth=_auth()) as client:
        resp = await client.get(
            f"{BASE_URL}/athlete/{_athlete_id()}/activities",
            params={"limit": limit},
        )
        resp.raise_for_status()
        return resp.json()


async def get_latest_activity() -> dict:
    """Fetch the most recent activity."""
    activities = await get_activities(limit=1)
    return activities[0] if activities else {}


async def get_wellness(oldest: str | None = None, newest: str | None = None) -> list[dict]:
    """Fetch wellness data. Dates as YYYY-MM-DD strings."""
    params: dict[str, str] = {}
    if oldest:
        params["oldest"] = oldest
    if newest:
        params["newest"] = newest
    async with httpx.AsyncClient(auth=_auth()) as client:
        resp = await client.get(
            f"{BASE_URL}/athlete/{_athlete_id()}/wellness",
            params=params,
        )
        resp.raise_for_status()
        return resp.json()
