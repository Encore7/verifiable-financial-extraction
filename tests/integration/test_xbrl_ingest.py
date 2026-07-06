"""End-to-end XBRL ingestion: mocked EDGAR transport + real Postgres."""

import json
from pathlib import Path

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import RawLanding, XbrlFact
from ingestion.edgar.client import EdgarClient
from ingestion.edgar.ratelimit import AsyncTokenBucket
from ingestion.landing import LandingStore
from ingestion.xbrl.ingest import COMPANY_FACTS_SOURCE, ingest_company_facts

COMPANY_FACTS = {
    "cik": 320193,
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        {
                            "start": "2022-09-25",
                            "end": "2023-09-30",
                            "val": 383285000000,
                            "accn": "0000320193-23-000106",
                            "fy": 2023,
                            "fp": "FY",
                            "form": "10-K",
                        }
                    ]
                }
            }
        }
    },
}


async def _noop_sleep(_seconds: float) -> None:
    return None


def _client() -> EdgarClient:
    body = json.dumps(COMPANY_FACTS).encode()

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body)

    return EdgarClient(
        user_agent="vfe test (test@example.com)",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        bucket=AsyncTokenBucket(rate=1000),
        sleep=_noop_sleep,
    )


async def test_ingest_lands_raw_and_loads_facts(db_session: AsyncSession, tmp_path: Path) -> None:
    async with _client() as client:
        result = await ingest_company_facts(
            client=client,
            store=LandingStore(tmp_path),
            session=db_session,
            cik=320193,
            source_version="2023q4",
        )

    assert result.facts_upserted == 1
    landing = await db_session.get(RawLanding, result.landing_id)
    assert landing is not None
    assert landing.source == COMPANY_FACTS_SOURCE

    fact = await db_session.scalar(select(XbrlFact).where(XbrlFact.tag == "us-gaap:Revenues"))
    assert fact is not None
    assert fact.accession_no == "0000320193-23-000106"


async def test_ingest_is_idempotent(db_session: AsyncSession, tmp_path: Path) -> None:
    store = LandingStore(tmp_path)
    for _ in range(2):
        async with _client() as client:
            await ingest_company_facts(
                client=client,
                store=store,
                session=db_session,
                cik=320193,
                source_version="2023q4",
            )

    landings = await db_session.scalar(
        select(func.count())
        .select_from(RawLanding)
        .where(RawLanding.source == COMPANY_FACTS_SOURCE)
    )
    facts = await db_session.scalar(select(func.count()).select_from(XbrlFact))
    assert landings == 1
    assert facts == 1
