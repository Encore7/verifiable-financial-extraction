"""upsert_filings against real Postgres: insert + idempotent refresh."""

import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Filing
from ingestion.edgar.submissions import FilingRecord
from ingestion.filings import upsert_filings


def _record(accession: str, primary: str = "doc.htm") -> FilingRecord:
    return FilingRecord(
        cik="0000320193",
        accession_no=accession,
        form="10-K",
        fiscal_year=2023,
        fiscal_period="FY",
        period_end=datetime.date(2023, 9, 30),
        filing_date=datetime.date(2023, 11, 3),
        primary_doc=primary,
    )


async def test_upsert_inserts_new_filing(db_session: AsyncSession) -> None:
    n = await upsert_filings(db_session, [_record("0000320193-23-000106")], "v1")
    assert n == 1
    row = await db_session.scalar(
        select(Filing).where(Filing.accession_no == "0000320193-23-000106")
    )
    assert row is not None
    assert row.fiscal_year == 2023


async def test_upsert_is_idempotent_and_refreshes(db_session: AsyncSession) -> None:
    acc = "0000320193-23-000106"
    await upsert_filings(db_session, [_record(acc, primary="old.htm")], "v1")
    await upsert_filings(db_session, [_record(acc, primary="new.htm")], "v2")

    count = await db_session.scalar(
        select(func.count()).select_from(Filing).where(Filing.accession_no == acc)
    )
    assert count == 1  # no duplicate

    row = await db_session.scalar(select(Filing).where(Filing.accession_no == acc))
    assert row is not None
    assert row.primary_doc == "new.htm"  # mutable field refreshed
    assert row.source_version == "v2"
