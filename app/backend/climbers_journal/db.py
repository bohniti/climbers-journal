import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://localhost:5432/climbers_journal"
)

engine = create_async_engine(DATABASE_URL, echo=False)


async def get_session() -> AsyncGenerator[SQLModelAsyncSession, None]:
    async with SQLModelAsyncSession(engine) as session:
        yield session
