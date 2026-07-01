"""Raw landing store — stage 1 of ELT.

Every fetched payload is written immutably to the filesystem and recorded in
``raw_landings``. Idempotent by (source, content_hash): re-landing identical
bytes is a no-op and returns the existing row. The caller owns the transaction.
"""

import asyncio
import hashlib
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import RawLanding


def _write_if_absent(path: Path, content: bytes) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


class LandingStore:
    def __init__(self, root: Path) -> None:
        self._root = root

    async def land(
        self,
        session: AsyncSession,
        *,
        source: str,
        source_url: str,
        content: bytes,
        source_version: str,
    ) -> RawLanding:
        digest = hashlib.sha256(content).hexdigest()

        path = self._root / source / f"{digest}.bin"
        # Keep blocking filesystem I/O off the event loop.
        await asyncio.to_thread(_write_if_absent, path, content)

        stmt = (
            pg_insert(RawLanding)
            .values(
                source=source,
                source_url=source_url,
                content_hash=digest,
                content_path=str(path),
                byte_size=len(content),
                source_version=source_version,
            )
            .on_conflict_do_nothing(index_elements=["source", "content_hash"])
        )
        await session.execute(stmt)
        await session.flush()

        row = await session.scalar(
            select(RawLanding).where(RawLanding.source == source, RawLanding.content_hash == digest)
        )
        if row is None:  # pragma: no cover - just inserted or pre-existing
            raise RuntimeError("raw_landings row missing immediately after upsert")
        return row
