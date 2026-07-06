"""XBRL ground-truth ELT: fetch companyfacts -> land raw -> parse -> upsert facts.

One re-runnable unit. Lands the verbatim response immutably (idempotent), then
loads the parsed facts. The caller commits the transaction.
"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from ingestion.edgar.client import EdgarClient
from ingestion.facts import upsert_facts
from ingestion.landing import LandingStore
from ingestion.xbrl.company_facts import DEFAULT_FORMS, DEFAULT_TAXONOMIES, parse_company_facts

COMPANY_FACTS_SOURCE = "xbrl.companyfacts"


@dataclass(frozen=True, slots=True)
class FactsIngestResult:
    landing_id: int
    facts_upserted: int


async def ingest_company_facts(
    *,
    client: EdgarClient,
    store: LandingStore,
    session: AsyncSession,
    cik: str | int,
    source_version: str,
    forms: frozenset[str] = DEFAULT_FORMS,
    taxonomies: frozenset[str] = DEFAULT_TAXONOMIES,
) -> FactsIngestResult:
    url = client.company_facts_url(cik)
    response = await client.get(url)

    landing = await store.land(
        session,
        source=COMPANY_FACTS_SOURCE,
        source_url=url,
        content=response.content,
        source_version=source_version,
    )
    records = parse_company_facts(response.json(), forms=forms, taxonomies=taxonomies)
    count = await upsert_facts(session, records, source_version)
    return FactsIngestResult(landing_id=landing.id, facts_upserted=count)
