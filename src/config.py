"""12-factor application settings, env-driven via pydantic-settings.

Imported as ``from config import settings`` (flat ``src`` layout — ``src`` is on the
import path, no wrapper package). Fields here mirror ``.env.example``.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    anthropic_api_key: str = ""

    # SEC EDGAR fair-access: a descriptive UA is required by SEC.
    sec_user_agent: str = ""

    # Postgres (app data + LangGraph checkpoints + pgvector)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/vfe"

    # Observability: single OTLP endpoint (Grafana Alloy receiver)
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"

    # Filesystem root for immutable raw ELT landings.
    landing_dir: str = "data/landings"


@lru_cache
def get_settings() -> Settings:
    return Settings()
