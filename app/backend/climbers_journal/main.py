import logging
import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from climbers_journal.config import get_settings  # noqa: E402
from climbers_journal.routers.chat import router as chat_router  # noqa: E402
from climbers_journal.routers.climbing import router as climbing_router  # noqa: E402
from climbers_journal.routers.import_csv import router as import_router  # noqa: E402
from climbers_journal.routers.stats import router as stats_router  # noqa: E402
from climbers_journal.routers.sync import router as sync_router  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(title="Climbers Journal", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(chat_router)
app.include_router(climbing_router)
app.include_router(import_router)
app.include_router(stats_router)
app.include_router(sync_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/config/status")
async def config_status():
    """Check which integrations are configured (have non-empty env vars)."""
    s = get_settings()
    default_provider = s.llm.providers.get(s.llm.default_provider)
    llm_key_env = default_provider.api_key_env if default_provider else ""
    intervals_key_env = s.intervals.api_key_env
    intervals_id_env = s.intervals.athlete_id_env

    return {
        "intervals_configured": (
            os.getenv(intervals_key_env, "") != ""
            and os.getenv(intervals_id_env, "") != ""
        ),
        "llm_configured": os.getenv(llm_key_env, "") != "",
    }
