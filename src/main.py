"""FastAPI application factory + lifespan.

Flat ``src`` layout: imported as ``main:app`` (e.g. ``uvicorn main:app``).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes import health
from db.engine import dispose_engine


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield
    # Clean shutdown of the DB pool. Telemetry/checkpointer wiring lands in later milestones.
    await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(title="Verifiable Financial Extraction", version="0.1.0", lifespan=lifespan)
    app.include_router(health.router)
    return app


app = create_app()
