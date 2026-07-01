"""Async EDGAR client.

Enforces the two SEC fair-access requirements — a descriptive ``User-Agent`` and
a request rate ceiling — and retries transient failures (429/5xx, transport
errors) with exponential backoff. The httpx client, rate bucket, and sleep are
injected so the client is fully unit-testable offline.
"""

import asyncio
from collections.abc import Awaitable, Callable
from types import TracebackType
from typing import Any

import httpx

from config import Settings, get_settings
from ingestion.edgar.ratelimit import AsyncTokenBucket

#: SEC fair-access ceiling.
EDGAR_MAX_RPS = 10.0

#: Status codes worth retrying (rate-limit + transient server errors).
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"


class EdgarClient:
    def __init__(
        self,
        *,
        user_agent: str,
        client: httpx.AsyncClient,
        bucket: AsyncTokenBucket,
        max_retries: int = 3,
        backoff_base: float = 0.5,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if not user_agent.strip():
            raise ValueError("SEC_USER_AGENT is required for EDGAR fair-access")
        self._user_agent = user_agent
        self._client = client
        self._bucket = bucket
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._sleep = sleep

    async def _get(self, url: str) -> httpx.Response:
        for attempt in range(self._max_retries + 1):
            await self._bucket.acquire()
            try:
                resp = await self._client.get(url, headers={"User-Agent": self._user_agent})
            except httpx.TransportError:
                if attempt >= self._max_retries:
                    raise
                await self._sleep(self._backoff_base * 2**attempt)
                continue
            if resp.status_code in RETRYABLE_STATUS and attempt < self._max_retries:
                await self._sleep(self._backoff_base * 2**attempt)
                continue
            resp.raise_for_status()
            return resp
        raise RuntimeError("unreachable")  # pragma: no cover

    @staticmethod
    def submissions_url(cik: str | int) -> str:
        return SUBMISSIONS_URL.format(cik=int(cik))

    async def get(self, url: str) -> httpx.Response:
        """Rate-limited, retrying GET. Exposes the raw response (for ELT landing)."""
        return await self._get(url)

    async def get_submissions(self, cik: str | int) -> dict[str, Any]:
        """Fetch the EDGAR submissions index for a CIK (zero-padded to 10 digits)."""
        resp = await self._get(self.submissions_url(cik))
        return resp.json()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "EdgarClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()


def build_edgar_client(
    settings: Settings | None = None, *, rate: float = EDGAR_MAX_RPS
) -> EdgarClient:
    settings = settings or get_settings()
    return EdgarClient(
        user_agent=settings.sec_user_agent,
        client=httpx.AsyncClient(timeout=30.0),
        bucket=AsyncTokenBucket(rate=rate),
    )
