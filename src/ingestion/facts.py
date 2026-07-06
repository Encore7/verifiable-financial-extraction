"""XBRL fact upsert — load parsed FactRecords into ``xbrl_facts``.

Idempotent by the natural key (accession_no, tag, context_ref): re-running
refreshes the value/period fields without duplicating rows. Caller owns the
transaction.
"""

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import XbrlFact
from ingestion.xbrl.company_facts import FactRecord

# Refreshed on conflict (everything except the natural key + created_at).
_MUTABLE = (
    "cik",
    "value",
    "unit",
    "scale",
    "period_start",
    "period_end",
    "fiscal_year",
    "fiscal_period",
    "source_version",
)


async def upsert_facts(
    session: AsyncSession, records: list[FactRecord], source_version: str
) -> int:
    if not records:
        return 0

    rows = [
        {
            "cik": r.cik,
            "accession_no": r.accession_no,
            "tag": r.tag,
            "value": r.value,
            "unit": r.unit,
            "scale": r.scale,
            "period_start": r.period_start,
            "period_end": r.period_end,
            "context_ref": r.context_ref,
            "fiscal_year": r.fiscal_year,
            "fiscal_period": r.fiscal_period,
            "source_version": source_version,
        }
        for r in records
    ]

    stmt = pg_insert(XbrlFact)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_xbrl_facts_fact",
        set_={col: stmt.excluded[col] for col in _MUTABLE},
    )
    await session.execute(stmt, rows)
    await session.flush()
    return len(rows)
