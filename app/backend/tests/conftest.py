import os

# Override DATABASE_URL before any app imports
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://localhost:5432/climbers_journal_test",
)

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

import climbers_journal.models  # noqa: F401 — register models with SQLModel.metadata

TEST_DB_URL = os.environ["DATABASE_URL"]


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(TEST_DB_URL, echo=False)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(autouse=True)
async def setup_db(engine):
    """Create all tables before each test, drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest_asyncio.fixture
async def session(engine):
    """Provide an async session that rolls back after each test."""
    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()
