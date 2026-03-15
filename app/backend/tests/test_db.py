from sqlalchemy import text


async def test_db_connectivity(session):
    """Smoke test: verify we can connect to the test database."""
    result = await session.exec(text("SELECT 1"))
    assert result.scalar() == 1
