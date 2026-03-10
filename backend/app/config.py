from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://journal:journal@localhost:5432/journal"

    # LLM (Nvidia NIM / Kimi K2.5)
    nvidia_api_key: str = ""
    nvidia_model: str = "moonshotai/kimi-k2.5"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"

    # intervals.icu
    intervals_icu_api_key: str = ""
    intervals_icu_athlete_id: str = ""  # e.g. "i12345" — find it in your intervals.icu profile URL

    # Brave Search
    brave_api_key: str = ""

    # Auth
    app_username: str = "admin"
    app_password: str = ""
    jwt_secret: str = "change-me-in-production"
    jwt_expire_days: int = 30

    # App
    backend_url: str = "http://localhost:8000"
    cors_origins: list[str] = ["http://localhost:3000"]
    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
