"""Parsing of the XBRL companyfacts payload."""

import datetime
from decimal import Decimal

from ingestion.xbrl.company_facts import parse_company_facts

PAYLOAD = {
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
                        },
                        {
                            "start": "2022-06-26",
                            "end": "2023-07-01",
                            "val": 81797000000,
                            "accn": "0000320193-23-000077",
                            "fy": 2023,
                            "fp": "Q3",
                            "form": "10-Q",
                        },
                    ]
                }
            }
        },
        "dei": {  # non-us-gaap taxonomy, filtered out by default
            "EntityCommonStockSharesOutstanding": {
                "units": {"shares": [{"end": "2023-10-20", "val": 1, "accn": "x", "form": "10-K"}]}
            }
        },
    },
}


def test_keeps_only_default_form_and_taxonomy() -> None:
    records = parse_company_facts(PAYLOAD)
    assert len(records) == 1  # only the us-gaap 10-K fact
    assert records[0].tag == "us-gaap:Revenues"


def test_derives_fact_fields() -> None:
    fact = parse_company_facts(PAYLOAD)[0]
    assert fact.cik == "0000320193"
    assert fact.accession_no == "0000320193-23-000106"
    assert fact.value == Decimal("383285000000")
    assert fact.unit == "USD"
    assert fact.period_start == datetime.date(2022, 9, 25)
    assert fact.period_end == datetime.date(2023, 9, 30)
    assert fact.fiscal_year == 2023
    assert fact.fiscal_period == "FY"


def test_context_ref_is_stable_natural_key() -> None:
    fact = parse_company_facts(PAYLOAD)[0]
    assert fact.context_ref == "USD|2022-09-25|2023-09-30"


def test_can_widen_forms_and_taxonomies() -> None:
    records = parse_company_facts(
        PAYLOAD, forms=frozenset({"10-K", "10-Q"}), taxonomies=frozenset({"us-gaap", "dei"})
    )
    assert len(records) == 3
