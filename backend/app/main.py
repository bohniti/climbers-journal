from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.dependencies import get_current_user
from app.routers import activities, chat, auth
from app.routers import routes as routes_router
from app.routers import import_router, stats

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
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


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
