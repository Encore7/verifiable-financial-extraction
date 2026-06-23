"""Async token-bucket rate limiter.

EDGAR fair-access caps clients at ~10 req/s. ``acquire()`` blocks just long
enough to stay under that rate. The clock and sleep are injectable so the
behaviour is deterministically testable without real time passing.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable


class AsyncTokenBucket:
    def __init__(
        self,
        rate: float,
        capacity: float | None = None,
        *,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if rate <= 0:
            raise ValueError("rate must be positive")
        self._rate = rate
        self._capacity = capacity if capacity is not None else rate
        self._tokens = self._capacity
        self._monotonic = monotonic
        self._sleep = sleep
        self._updated = monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> None:
        async with self._lock:
            while True:
                now = self._monotonic()
                self._tokens = min(
                    self._capacity, self._tokens + (now - self._updated) * self._rate
                )
                self._updated = now
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                await self._sleep((tokens - self._tokens) / self._rate)
