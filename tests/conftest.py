from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.main import app
from core import settings
from database.session import SessionFactory, db_session, engine

assert str(settings.DB_URL).endswith("_test"), "Use `make test`."


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession]:
    """One session per test, rolled back afterwards; commits become savepoints."""
    async with engine.connect() as connection:
        transaction = await connection.begin()
        async with SessionFactory(
            bind=connection,
            join_transaction_mode="create_savepoint",
        ) as test_session:
            yield test_session
        await transaction.rollback()


@pytest.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """HTTP client that calls the app in-process, on the test's session."""
    app.dependency_overrides[db_session] = lambda: session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def persist(session: AsyncSession):
    """Save objects built by the factories."""

    async def _persist(*objects):
        session.add_all(objects)
        await session.flush()
        return objects if len(objects) > 1 else objects[0]

    return _persist
