"""XBRL facts — the ground truth.

Loaded from the SEC XBRL Financial Statement Data Sets. A fact is uniquely
identified within a filing by (accession_no, tag, context_ref). The
(cik, tag, fiscal_year) index serves the M2 retrieval lookup.
"""

import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin


class XbrlFact(Base, TimestampMixin):
    __tablename__ = "xbrl_facts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cik: Mapped[str] = mapped_column(String(10))
    accession_no: Mapped[str] = mapped_column(String(20))
    tag: Mapped[str] = mapped_column(String(128))
    value: Mapped[Decimal | None] = mapped_column(Numeric)
    unit: Mapped[str | None] = mapped_column(String(32))
    scale: Mapped[int | None] = mapped_column(Integer)
    period_start: Mapped[datetime.date | None] = mapped_column(Date)
    period_end: Mapped[datetime.date | None] = mapped_column(Date)
    context_ref: Mapped[str | None] = mapped_column(String(128))
    fiscal_year: Mapped[int | None] = mapped_column(Integer)
    fiscal_period: Mapped[str | None] = mapped_column(String(2))
    source_version: Mapped[str] = mapped_column(String(64))

    __table_args__ = (
        UniqueConstraint("accession_no", "tag", "context_ref", name="uq_xbrl_facts_fact"),
        Index("ix_xbrl_facts_lookup", "cik", "tag", "fiscal_year"),
    )
