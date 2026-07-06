"""Parse an SEC XBRL ``companyfacts`` payload into fact records — the ground truth.

Shape: ``facts -> taxonomy -> concept -> units -> uom -> [ {val, accn, fy, fp,
form, start?, end}, ... ]``. companyfacts carries no raw XBRL contextRef, so we
synthesize a stable natural key from (unit, period_start, period_end) — the same
tuple the bulk num.txt uses to disambiguate a fact within an accession + tag.
Values keep full precision via Decimal.
"""

import datetime
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

DEFAULT_FORMS = frozenset({"10-K"})
DEFAULT_TAXONOMIES = frozenset({"us-gaap"})


@dataclass(frozen=True, slots=True)
class FactRecord:
    cik: str
    accession_no: str
    tag: str
    value: Decimal | None
    unit: str
    scale: int | None
    period_start: datetime.date | None
    period_end: datetime.date | None
    context_ref: str
    fiscal_year: int | None
    fiscal_period: str | None


def _parse_date(value: str | None) -> datetime.date | None:
    return datetime.date.fromisoformat(value) if value else None


def parse_company_facts(
    payload: dict[str, Any],
    forms: frozenset[str] = DEFAULT_FORMS,
    taxonomies: frozenset[str] = DEFAULT_TAXONOMIES,
) -> list[FactRecord]:
    cik = f"{int(payload['cik']):010d}"
    records: list[FactRecord] = []

    for taxonomy, concepts in payload.get("facts", {}).items():
        if taxonomy not in taxonomies:
            continue
        for concept, body in concepts.items():
            tag = f"{taxonomy}:{concept}"
            for uom, entries in body.get("units", {}).items():
                for entry in entries:
                    if entry.get("form") not in forms:
                        continue
                    start, end = entry.get("start"), entry.get("end")
                    records.append(
                        FactRecord(
                            cik=cik,
                            accession_no=entry["accn"],
                            tag=tag,
                            value=Decimal(str(entry["val"])) if "val" in entry else None,
                            unit=uom,
                            scale=None,
                            period_start=_parse_date(start),
                            period_end=_parse_date(end),
                            context_ref=f"{uom}|{start or ''}|{end or ''}",
                            fiscal_year=entry.get("fy"),
                            fiscal_period=entry.get("fp"),
                        )
                    )
    return records
