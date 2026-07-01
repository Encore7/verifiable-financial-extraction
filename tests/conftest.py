"""Shared test fixtures.

`db_session` runs each test inside a transaction that is rolled back afterward
(no committed state leaks between tests) and skips cleanly when Postgres is not
reachable — so the offline unit suite still runs anywhere.
"""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from config import get_settings
from db.models import Base


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(get_settings().database_url)
    try:
        async with engine.connect() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.commit()
    except (SQLAlchemyError, OSError):
        await engine.dispose()
        pytest.skip("Postgres not available")

    conn = await engine.connect()
    trans = await conn.begin()
    session = AsyncSession(bind=conn, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        if trans.is_active:
            await trans.rollback()
        await conn.close()
        await engine.dispose()
