"""intervals.icu API client."""

import os
from datetime import date, timedelta

import httpx

from climbers_journal.config import get_settings

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    """Return a shared httpx.AsyncClient, creating it on first use."""
    global _client
    if _client is None or _client.is_closed:
        settings = get_settings()
        api_key = os.getenv(settings.intervals.api_key_env, "")
        _client = httpx.AsyncClient(auth=("API_KEY", api_key))
    return _client


def _base_url() -> str:
    return get_settings().intervals.base_url


def _athlete_id() -> str:
    settings = get_settings()
    return os.getenv(settings.intervals.athlete_id_env, "")


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
    resp = await _get_client().get(
        f"{_base_url()}/athlete/{_athlete_id()}/activities",
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
    return activities[0] if activities else {}


async def get_wellness(oldest: str | None = None, newest: str | None = None) -> list[dict]:
    """Fetch wellness data. Dates as YYYY-MM-DD strings."""
    today = date.today()
    params: dict[str, str] = {
        "oldest": oldest or (today - timedelta(days=30)).isoformat(),
        "newest": newest or today.isoformat(),
    }
    resp = await _get_client().get(
        f"{_base_url()}/athlete/{_athlete_id()}/wellness",
        params=params,
    )
    resp.raise_for_status()
    return resp.json()
