"""Health probe contracts. The DB ping is monkeypatched so readiness is deterministic
regardless of whether Postgres happens to be running locally."""

import pytest
from fastapi.testclient import TestClient

import api.routes.health as health
from main import create_app


def test_liveness_is_always_alive() -> None:
    client = TestClient(create_app())
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "alive"}


def test_readiness_ok_when_db_reachable(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _ok() -> bool:
        return True

    monkeypatch.setattr(health, "ping", _ok)
    resp = TestClient(create_app()).get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready", "checks": {"database": "ok"}}


def test_readiness_503_when_db_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _bad() -> bool:
        return False

    monkeypatch.setattr(health, "ping", _bad)
    resp = TestClient(create_app()).get("/health/ready")
    assert resp.status_code == 503
    assert resp.json() == {"status": "not_ready", "checks": {"database": "unreachable"}}
