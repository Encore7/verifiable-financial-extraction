"""Async SQLAlchemy engine (lazy singleton) + a lightweight connectivity ping.

The ping backs the readiness probe — it must fail *closed* (return False) on any
connection error rather than raise, so an unreachable DB yields 503, not a 500.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from config import get_settings

_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    return _engine


async def ping() -> bool:
    """Return True iff a trivial round-trip to Postgres succeeds."""
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        return False
    return True


async def dispose_engine() -> None:
    """Dispose the pool on shutdown (idempotent)."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
