"""EDGAR client: UA enforcement, URL shape, and retry/backoff — all via
httpx.MockTransport, no network."""

import httpx
import pytest

from ingestion.edgar.client import EdgarClient
from ingestion.edgar.ratelimit import AsyncTokenBucket


async def _noop_sleep(_seconds: float) -> None:
    return None


def _client(handler: httpx.MockTransport, **kwargs: object) -> EdgarClient:
    return EdgarClient(
        user_agent="vfe test (test@example.com)",
        client=httpx.AsyncClient(transport=handler),
        bucket=AsyncTokenBucket(rate=1000),
        sleep=_noop_sleep,
        **kwargs,  # type: ignore[arg-type]
    )


def test_blank_user_agent_rejected() -> None:
    with pytest.raises(ValueError):
        EdgarClient(
            user_agent="  ",
            client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))),
            bucket=AsyncTokenBucket(rate=1000),
        )


async def test_get_submissions_pads_cik_and_sends_user_agent() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["ua"] = request.headers["User-Agent"]
        return httpx.Response(200, json={"cik": "320193"})

    async with _client(httpx.MockTransport(handler)) as client:
        payload = await client.get_submissions("320193")

    assert seen["url"] == "https://data.sec.gov/submissions/CIK0000320193.json"
    assert seen["ua"] == "vfe test (test@example.com)"
    assert payload == {"cik": "320193"}


async def test_retries_transient_5xx_then_succeeds() -> None:
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    async with _client(httpx.MockTransport(handler), max_retries=3, backoff_base=0.0) as client:
        payload = await client.get_submissions(320193)

    assert attempts["n"] == 3
    assert payload == {"ok": True}


async def test_raises_after_exhausting_retries() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    async with _client(httpx.MockTransport(handler), max_retries=2, backoff_base=0.0) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_submissions(320193)


async def test_does_not_retry_client_error() -> None:
    attempts = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        return httpx.Response(404)

    async with _client(httpx.MockTransport(handler), max_retries=3, backoff_base=0.0) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_submissions(320193)

    assert attempts["n"] == 1  # 404 is not retryable
