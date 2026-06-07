"""Filing index + segmented sections.

`filings` is the (CIK, accession, form, period) index built from EDGAR
submissions. `filing_sections` holds the segmented narrative (MD&A, statements)
whose (accession, section, char_span) is the re-fetchable locator the verifier
later re-resolves against.
"""

import datetime

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, TimestampMixin


class Filing(Base, TimestampMixin):
    __tablename__ = "filings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cik: Mapped[str] = mapped_column(String(10), index=True)
    accession_no: Mapped[str] = mapped_column(String(20), unique=True)
    form: Mapped[str] = mapped_column(String(10))
    fiscal_year: Mapped[int] = mapped_column(Integer)
    fiscal_period: Mapped[str | None] = mapped_column(String(2))
    period_end: Mapped[datetime.date | None] = mapped_column(Date)
    filing_date: Mapped[datetime.date | None] = mapped_column(Date)
    primary_doc: Mapped[str | None] = mapped_column(String(255))
    source_version: Mapped[str] = mapped_column(String(64))

    sections: Mapped[list["FilingSection"]] = relationship(
        back_populates="filing", cascade="all, delete-orphan"
    )


class FilingSection(Base, TimestampMixin):
    __tablename__ = "filing_sections"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    filing_id: Mapped[int] = mapped_column(ForeignKey("filings.id", ondelete="CASCADE"), index=True)
    section: Mapped[str] = mapped_column(String(64))
    char_start: Mapped[int] = mapped_column(Integer)
    char_end: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)

    filing: Mapped["Filing"] = relationship(back_populates="sections")
