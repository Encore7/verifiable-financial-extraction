"""Raw landings — the immutable first stage of the ELT pipeline.

Every fetched payload is landed verbatim before normalization. (source,
content_hash) is unique so re-running ingestion is a no-op (idempotency is a
correctness property here, not an optimization).
"""

from sqlalchemy import BigInteger, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin


class RawLanding(Base, TimestampMixin):
    __tablename__ = "raw_landings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    source_url: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    content_path: Mapped[str] = mapped_column(Text)
    byte_size: Mapped[int] = mapped_column(Integer)
    source_version: Mapped[str] = mapped_column(String(64))

    __table_args__ = (UniqueConstraint("source", "content_hash", name="uq_raw_landings_dedup"),)
