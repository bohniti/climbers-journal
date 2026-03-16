"""Tests for config loading and rate-limit retry logic."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from openai import RateLimitError

from climbers_journal.config import AppSettings, get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear the lru_cache before each test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _load_from(yaml_path: Path) -> AppSettings:
    """Helper: load settings from a specific YAML path."""
    original = AppSettings._yaml_path
    AppSettings._yaml_path = yaml_path
    try:
        return AppSettings()
    finally:
        AppSettings._yaml_path = original


# --- Config loading tests ---


def test_config_loads_from_yaml(tmp_path: Path):
    """Happy path: config.yaml is loaded and parsed correctly."""
    yaml_content = """\
llm:
  default_provider: gemini
  providers:
    gemini:
      model: gemini-2.5-flash-lite
      base_url: https://generativelanguage.googleapis.com/v1beta/openai/
      api_key_env: GOOGLE_API_KEY
      rpm_limit: 10
      tpm_limit: 250000
intervals:
  base_url: https://intervals.icu/api/v1
  api_key_env: INTERVALS_API_KEY
  athlete_id_env: INTERVALS_ATHLETE_ID
cors:
  origins:
    - http://localhost:3000
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml_content)

    settings = _load_from(config_file)
    assert settings.llm.default_provider == "gemini"
    assert "gemini" in settings.llm.providers
    assert settings.llm.providers["gemini"].model == "gemini-2.5-flash-lite"
    assert settings.intervals.base_url == "https://intervals.icu/api/v1"
    assert settings.cors.origins == ["http://localhost:3000"]


def test_config_missing_file_uses_defaults(tmp_path: Path):
    """Missing config.yaml falls back to sensible defaults via get_settings()."""
    missing_path = tmp_path / "nonexistent.yaml"
    with patch("climbers_journal.config.CONFIG_PATH", missing_path):
        settings = get_settings()
        assert settings.llm.default_provider == "gemini"
        assert "gemini" in settings.llm.providers
        assert "kimi" in settings.llm.providers
        assert settings.intervals.base_url == "https://intervals.icu/api/v1"


def test_config_malformed_yaml_fails(tmp_path: Path):
    """Malformed YAML should raise an error."""
    bad_yaml = tmp_path / "config.yaml"
    bad_yaml.write_text("llm: {providers: {gemini: not_valid}}")

    with pytest.raises(Exception):
        _load_from(bad_yaml)


def test_config_invalid_field_type_fails(tmp_path: Path):
    """Invalid field types should raise a validation error."""
    bad_config = tmp_path / "config.yaml"
    bad_config.write_text(
        "llm:\n  default_provider: gemini\n  providers:\n    gemini:\n      model: 123\n      base_url: true\n      api_key_env: []\n"
    )

    with pytest.raises(Exception):
        _load_from(bad_config)


# --- Rate limit retry tests ---


@pytest.mark.asyncio
async def test_call_with_retry_succeeds_on_second_attempt():
    """Rate limit on first call, succeeds on retry."""
    from climbers_journal.services.llm import _call_with_retry

    mock_client = AsyncMock()
    rate_limit_err = RateLimitError(
        message="rate limited",
        response=AsyncMock(status_code=429, headers={}, json=lambda: {}),
        body=None,
    )
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[rate_limit_err, "success"]
    )

    with patch("climbers_journal.services.llm.RETRY_DELAY_S", 0):
        result = await _call_with_retry(mock_client, "model", [], None)

    assert result == "success"
    assert mock_client.chat.completions.create.call_count == 2


@pytest.mark.asyncio
async def test_call_with_retry_exhaustion_raises():
    """All retries exhausted — should re-raise RateLimitError."""
    from climbers_journal.services.llm import _call_with_retry

    mock_client = AsyncMock()
    rate_limit_err = RateLimitError(
        message="rate limited",
        response=AsyncMock(status_code=429, headers={}, json=lambda: {}),
        body=None,
    )
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[rate_limit_err, rate_limit_err, rate_limit_err]
    )

    with patch("climbers_journal.services.llm.RETRY_DELAY_S", 0):
        with pytest.raises(RateLimitError):
            await _call_with_retry(mock_client, "model", [], None)

    assert mock_client.chat.completions.create.call_count == 3
