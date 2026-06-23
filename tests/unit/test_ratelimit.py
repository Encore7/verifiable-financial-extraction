"""Token bucket behaviour, made deterministic with an injected clock + sleep."""

import pytest

from ingestion.edgar.ratelimit import AsyncTokenBucket


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def time(self) -> float:
        return self.t

    async def sleep(self, seconds: float) -> None:
        self.t += seconds


async def test_burst_up_to_capacity_is_immediate() -> None:
    clock = FakeClock()
    bucket = AsyncTokenBucket(rate=10, capacity=10, monotonic=clock.time, sleep=clock.sleep)
    for _ in range(10):
        await bucket.acquire()
    assert clock.t == 0.0  # no waiting while tokens remain


async def test_exceeding_capacity_waits_for_refill() -> None:
    clock = FakeClock()
    bucket = AsyncTokenBucket(rate=10, capacity=10, monotonic=clock.time, sleep=clock.sleep)
    for _ in range(10):
        await bucket.acquire()
    await bucket.acquire()  # 11th token must wait one refill interval
    assert clock.t == pytest.approx(0.1)  # 1 token / 10 per second


def test_non_positive_rate_rejected() -> None:
    with pytest.raises(ValueError):
        AsyncTokenBucket(rate=0)
