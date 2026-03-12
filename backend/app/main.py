from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

from app.config import get_settings
from app.dependencies import get_current_user
from app.routers import activities, chat, auth
from app.routers import routes as routes_router
from app.routers import import_router, stats, photos, refine, coach

log = logging.getLogger(__name__)
settings = get_settings()


def _setup_tracing() -> None:
    """Instrument OpenAI SDK with Phoenix / OpenTelemetry — fails gracefully if not configured."""
    phoenix_endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
    if not phoenix_endpoint:
        return
    try:
        from phoenix.otel import register
        from openinference.instrumentation.openai import OpenAIInstrumentor

        tracer_provider = register(
            project_name="climbers-journal",
            endpoint=phoenix_endpoint,
        )
        OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
        log.info("Phoenix tracing enabled → %s", phoenix_endpoint)
    except Exception as exc:
        log.warning("Phoenix tracing setup failed (non-fatal): %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _setup_tracing()
    # Tables are managed by Alembic migrations — do not call create_all() here
    yield


app = FastAPI(
    title="Climbers Journal API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public routes
app.include_router(auth.router)

# Protected routes — require valid JWT
_auth = [Depends(get_current_user)]
app.include_router(activities.router, dependencies=_auth)
app.include_router(chat.router, dependencies=_auth)
app.include_router(routes_router.router, dependencies=_auth)
app.include_router(import_router.router, dependencies=_auth)
app.include_router(stats.router, dependencies=_auth)
app.include_router(photos.router, dependencies=_auth)
app.include_router(refine.router, dependencies=_auth)
app.include_router(coach.router, dependencies=_auth)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
