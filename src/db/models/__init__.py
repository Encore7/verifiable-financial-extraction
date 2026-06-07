"""Model registry. Importing this package registers every table on
``Base.metadata`` — Alembic's ``env.py`` imports it for autogenerate.
"""

from db.base import Base
from db.models.filing import Filing, FilingSection
from db.models.landing import RawLanding
from db.models.xbrl import XbrlFact

__all__ = ["Base", "Filing", "FilingSection", "RawLanding", "XbrlFact"]
