"""Application configuration via pydantic-settings + YAML."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, YamlConfigSettingsSource

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


class LLMProviderConfig(BaseModel):
    model: str
    base_url: str
    api_key_env: str
    rpm_limit: int | None = None
    tpm_limit: int | None = None


class LLMConfig(BaseModel):
    default_provider: str = "gemini"
    providers: dict[str, LLMProviderConfig] = {
        "gemini": LLMProviderConfig(
            model="gemini-2.5-flash-lite",
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key_env="GOOGLE_API_KEY",
            rpm_limit=10,
            tpm_limit=250000,
        ),
        "kimi": LLMProviderConfig(
            model="moonshotai/kimi-k2.5",
            base_url="https://integrate.api.nvidia.com/v1",
            api_key_env="NVIDIA_API_KEY",
        ),
    }


class IntervalsConfig(BaseModel):
    base_url: str = "https://intervals.icu/api/v1"
    api_key_env: str = "INTERVALS_API_KEY"
    athlete_id_env: str = "INTERVALS_ATHLETE_ID"


class CORSConfig(BaseModel):
    origins: list[str] = ["http://localhost:3000"]


class AppSettings(BaseSettings):
    _yaml_path: ClassVar[Path] = CONFIG_PATH

    llm: LLMConfig = LLMConfig()
    intervals: IntervalsConfig = IntervalsConfig()
    cors: CORSConfig = CORSConfig()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        yaml_path = cls._yaml_path
        return (
            init_settings,
            YamlConfigSettingsSource(settings_cls, yaml_file=str(yaml_path)),
        )


@lru_cache
def get_settings() -> AppSettings:
    """Load and cache application settings.

    Falls back to sensible defaults if config.yaml is missing.
    Malformed YAML or invalid fields will fail fast.
    """
    if not CONFIG_PATH.exists():
        logger.warning(
            "config.yaml not found at %s — using default settings", CONFIG_PATH
        )
        # Build with no YAML source — just defaults
        original = AppSettings._yaml_path
        AppSettings._yaml_path = Path("/dev/null/nonexistent")
        try:
            settings = AppSettings()
        finally:
            AppSettings._yaml_path = original
    else:
        logger.info("Loading config from %s", CONFIG_PATH)
        settings = AppSettings()

    logger.info(
        "LLM provider: %s (%s)",
        settings.llm.default_provider,
        settings.llm.providers.get(settings.llm.default_provider, "unknown"),
    )
    return settings
