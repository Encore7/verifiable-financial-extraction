"""Index ingestion ELT: fetch submissions -> land raw -> parse -> upsert filings.

One re-runnable unit. Lands the verbatim response immutably (idempotent), then
loads the parsed filing index. The caller commits the transaction.
"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from ingestion.edgar.client import EdgarClient
from ingestion.edgar.submissions import DEFAULT_FORMS, parse_filings
from ingestion.filings import upsert_filings
from ingestion.landing import LandingStore

SUBMISSIONS_SOURCE = "edgar.submissions"


@dataclass(frozen=True, slots=True)
class IngestResult:
    landing_id: int
    filings_upserted: int


async def ingest_submissions(
    *,
    client: EdgarClient,
    store: LandingStore,
    session: AsyncSession,
    cik: str | int,
    source_version: str,
    forms: frozenset[str] = DEFAULT_FORMS,
) -> IngestResult:
    url = client.submissions_url(cik)
    response = await client.get(url)

    landing = await store.land(
        session,
        source=SUBMISSIONS_SOURCE,
        source_url=url,
        content=response.content,
        source_version=source_version,
    )
    records = parse_filings(response.json(), forms=forms)
    count = await upsert_filings(session, records, source_version)
    return IngestResult(landing_id=landing.id, filings_upserted=count)
