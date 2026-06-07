"""Guards the schema registry: importing db.models must register exactly the M1
tables on Base.metadata, and the load-bearing constraints must exist. Pure
metadata assertions — no database required."""

from sqlalchemy import UniqueConstraint

from db.models import Base


def _unique_column_sets(table_name: str) -> set[tuple[str, ...]]:
    return {
        tuple(c.name for c in con.columns)
        for con in Base.metadata.tables[table_name].constraints
        if isinstance(con, UniqueConstraint)
    }


def test_expected_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == {
        "filings",
        "filing_sections",
        "xbrl_facts",
        "raw_landings",
    }


def test_xbrl_fact_natural_key_is_unique() -> None:
    # The verifier relies on a fact being unique per (accession, tag, context).
    assert ("accession_no", "tag", "context_ref") in _unique_column_sets("xbrl_facts")


def test_raw_landing_dedup_constraint_enforces_idempotency() -> None:
    assert ("source", "content_hash") in _unique_column_sets("raw_landings")
