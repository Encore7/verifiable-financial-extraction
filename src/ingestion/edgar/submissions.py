"""Parse an EDGAR ``submissions.json`` payload into filing index records.

submissions.json stores the recent filings as parallel arrays under
``filings.recent``. We zip them into typed records, keeping only the requested
forms. v1 targets 10-K (annual); 10-Q is added in M6.
"""

import datetime
from dataclasses import dataclass
from typing import Any

DEFAULT_FORMS = frozenset({"10-K"})


@dataclass(frozen=True, slots=True)
class FilingRecord:
    cik: str
    accession_no: str
    form: str
    fiscal_year: int
    fiscal_period: str | None
    period_end: datetime.date | None
    filing_date: datetime.date | None
    primary_doc: str | None


def _parse_date(value: str) -> datetime.date | None:
    return datetime.date.fromisoformat(value) if value else None


def parse_filings(
    payload: dict[str, Any], forms: frozenset[str] = DEFAULT_FORMS
) -> list[FilingRecord]:
    cik = f"{int(payload['cik']):010d}"
    recent = payload["filings"]["recent"]

    records: list[FilingRecord] = []
    for accession, form, filing_date, report_date, primary in zip(
        recent["accessionNumber"],
        recent["form"],
        recent["filingDate"],
        recent["reportDate"],
        recent["primaryDocument"],
        strict=True,
    ):
        if form not in forms:
            continue
        period_end = _parse_date(report_date)
        filed = _parse_date(filing_date)
        anchor = period_end or filed
        if anchor is None:
            # No date to place the fiscal year — can't index it; skip.
            continue
        records.append(
            FilingRecord(
                cik=cik,
                accession_no=accession,
                form=form,
                fiscal_year=anchor.year,
                fiscal_period="FY" if form == "10-K" else None,
                period_end=period_end,
                filing_date=filed,
                primary_doc=primary or None,
            )
        )
    return records
