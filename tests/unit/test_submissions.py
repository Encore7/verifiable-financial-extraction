"""Parsing of the submissions.json filing index."""

import datetime

from ingestion.edgar.submissions import parse_filings

PAYLOAD = {
    "cik": 320193,
    "filings": {
        "recent": {
            "accessionNumber": [
                "0000320193-23-000106",
                "0000320193-23-000077",
                "0000320193-22-000108",
            ],
            "form": ["10-K", "10-Q", "10-K"],
            "filingDate": ["2023-11-03", "2023-08-04", "2022-10-28"],
            "reportDate": ["2023-09-30", "2023-07-01", "2022-09-24"],
            "primaryDocument": ["aapl-20230930.htm", "aapl-20230701.htm", ""],
        }
    },
}


def test_filters_to_requested_forms_by_default_10k() -> None:
    records = parse_filings(PAYLOAD)
    assert [r.form for r in records] == ["10-K", "10-K"]


def test_derives_fields() -> None:
    record = parse_filings(PAYLOAD)[0]
    assert record.cik == "0000320193"  # zero-padded
    assert record.accession_no == "0000320193-23-000106"
    assert record.fiscal_year == 2023  # from reportDate
    assert record.fiscal_period == "FY"
    assert record.period_end == datetime.date(2023, 9, 30)
    assert record.filing_date == datetime.date(2023, 11, 3)
    assert record.primary_doc == "aapl-20230930.htm"


def test_empty_primary_doc_becomes_none() -> None:
    older_10k = parse_filings(PAYLOAD)[1]
    assert older_10k.primary_doc is None


def test_can_request_multiple_forms() -> None:
    records = parse_filings(PAYLOAD, forms=frozenset({"10-K", "10-Q"}))
    assert {r.form for r in records} == {"10-K", "10-Q"}
