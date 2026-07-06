"""upsert_facts against real Postgres: insert + idempotent refresh."""

import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import XbrlFact
from ingestion.facts import upsert_facts
from ingestion.xbrl.company_facts import FactRecord


def _fact(value: str, context: str = "USD|2022-09-25|2023-09-30") -> FactRecord:
    return FactRecord(
        cik="0000320193",
        accession_no="0000320193-23-000106",
        tag="us-gaap:Revenues",
        value=Decimal(value),
        unit="USD",
        scale=None,
        period_start=datetime.date(2022, 9, 25),
        period_end=datetime.date(2023, 9, 30),
        context_ref=context,
        fiscal_year=2023,
        fiscal_period="FY",
    )


async def test_upsert_inserts_fact(db_session: AsyncSession) -> None:
    n = await upsert_facts(db_session, [_fact("383285000000")], "v1")
    assert n == 1
    row = await db_session.scalar(select(XbrlFact).where(XbrlFact.tag == "us-gaap:Revenues"))
    assert row is not None
    assert row.value == Decimal("383285000000")


async def test_upsert_is_idempotent_and_refreshes(db_session: AsyncSession) -> None:
    await upsert_facts(db_session, [_fact("1")], "v1")
    await upsert_facts(db_session, [_fact("383285000000")], "v2")  # restated value, same key

    count = await db_session.scalar(select(func.count()).select_from(XbrlFact))
    assert count == 1  # no duplicate on the natural key

    row = await db_session.scalar(select(XbrlFact).where(XbrlFact.tag == "us-gaap:Revenues"))
    assert row is not None
    assert row.value == Decimal("383285000000")
    assert row.source_version == "v2"


async def test_distinct_periods_are_separate_rows(db_session: AsyncSession) -> None:
    await upsert_facts(
        db_session,
        [
            _fact("100", context="USD|2021-09-26|2022-09-24"),
            _fact("200", context="USD|2022-09-25|2023-09-30"),
        ],
        "v1",
    )
    count = await db_session.scalar(select(func.count()).select_from(XbrlFact))
    assert count == 2
