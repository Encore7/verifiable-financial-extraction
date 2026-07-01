"""LandingStore against real Postgres: persistence + idempotency."""

import hashlib
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import RawLanding
from ingestion.landing import LandingStore


async def test_land_persists_row_and_immutable_file(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    store = LandingStore(tmp_path)
    row = await store.land(
        db_session,
        source="edgar.submissions",
        source_url="https://data.sec.gov/x",
        content=b"hello",
        source_version="2023q4",
    )
    assert row.id is not None
    assert row.content_hash == hashlib.sha256(b"hello").hexdigest()
    assert row.byte_size == 5
    assert Path(row.content_path).read_bytes() == b"hello"


async def test_land_is_idempotent(db_session: AsyncSession, tmp_path: Path) -> None:
    store = LandingStore(tmp_path)
    kwargs = {
        "source": "edgar.submissions",
        "source_url": "https://data.sec.gov/x",
        "content": b"same-bytes",
        "source_version": "2023q4",
    }
    first = await store.land(db_session, **kwargs)  # type: ignore[arg-type]
    second = await store.land(db_session, **kwargs)  # type: ignore[arg-type]

    assert first.id == second.id
    count = await db_session.scalar(
        select(func.count())
        .select_from(RawLanding)
        .where(RawLanding.content_hash == first.content_hash)
    )
    assert count == 1
