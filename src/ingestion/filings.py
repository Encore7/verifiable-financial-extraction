"""Filing index upsert — load parsed FilingRecords into ``filings``.

Idempotent by accession_no: re-running refreshes the mutable fields to the
latest fetch (handles restatement-style metadata changes) without creating
duplicate rows. The caller owns the transaction.
"""

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Filing
from ingestion.edgar.submissions import FilingRecord

# Columns refreshed on conflict (everything except the natural key + created_at).
_MUTABLE = (
    "cik",
    "form",
    "fiscal_year",
    "fiscal_period",
    "period_end",
    "filing_date",
    "primary_doc",
    "source_version",
)


async def upsert_filings(
    session: AsyncSession, records: list[FilingRecord], source_version: str
) -> int:
    if not records:
        return 0

    rows = [
        {
            "cik": r.cik,
            "accession_no": r.accession_no,
            "form": r.form,
            "fiscal_year": r.fiscal_year,
            "fiscal_period": r.fiscal_period,
            "period_end": r.period_end,
            "filing_date": r.filing_date,
            "primary_doc": r.primary_doc,
            "source_version": source_version,
        }
        for r in records
    ]

    stmt = pg_insert(Filing)
    stmt = stmt.on_conflict_do_update(
        index_elements=["accession_no"],
        set_={col: stmt.excluded[col] for col in _MUTABLE},
    )
    await session.execute(stmt, rows)
    await session.flush()
    return len(rows)
