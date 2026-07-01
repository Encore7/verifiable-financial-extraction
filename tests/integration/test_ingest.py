"""End-to-end index ingestion: mocked EDGAR transport + real Postgres."""

import json
from pathlib import Path

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Filing, RawLanding
from ingestion.edgar.client import EdgarClient
from ingestion.edgar.ingest import SUBMISSIONS_SOURCE, ingest_submissions
from ingestion.edgar.ratelimit import AsyncTokenBucket
from ingestion.landing import LandingStore

SUBMISSIONS = {
    "cik": 320193,
    "filings": {
        "recent": {
            "accessionNumber": ["0000320193-23-000106"],
            "form": ["10-K"],
            "filingDate": ["2023-11-03"],
            "reportDate": ["2023-09-30"],
            "primaryDocument": ["aapl-20230930.htm"],
        }
    },
}


async def _noop_sleep(_seconds: float) -> None:
    return None


def _client() -> EdgarClient:
    body = json.dumps(SUBMISSIONS).encode()

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body)

    return EdgarClient(
        user_agent="vfe test (test@example.com)",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        bucket=AsyncTokenBucket(rate=1000),
        sleep=_noop_sleep,
    )


async def test_ingest_lands_raw_and_indexes_filing(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    async with _client() as client:
        result = await ingest_submissions(
            client=client,
            store=LandingStore(tmp_path),
            session=db_session,
            cik=320193,
            source_version="2023q4",
        )

    assert result.filings_upserted == 1

    landing = await db_session.get(RawLanding, result.landing_id)
    assert landing is not None
    assert Path(landing.content_path).read_bytes() == json.dumps(SUBMISSIONS).encode()

    filing = await db_session.scalar(
        select(Filing).where(Filing.accession_no == "0000320193-23-000106")
    )
    assert filing is not None
    assert filing.fiscal_year == 2023


async def test_ingest_is_idempotent(db_session: AsyncSession, tmp_path: Path) -> None:
    store = LandingStore(tmp_path)
    for _ in range(2):
        async with _client() as client:
            await ingest_submissions(
                client=client,
                store=store,
                session=db_session,
                cik=320193,
                source_version="2023q4",
            )

    landings = await db_session.scalar(
        select(func.count()).select_from(RawLanding).where(RawLanding.source == SUBMISSIONS_SOURCE)
    )
    filings = await db_session.scalar(select(func.count()).select_from(Filing))
    assert landings == 1
    assert filings == 1
