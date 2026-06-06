"""Health probes, split by purpose (k8s-style):

- ``/health/live``  — liveness: the process is up. No dependencies. Never flaps on
  a downstream outage, so an orchestrator does not needlessly restart the pod.
- ``/health/ready`` — readiness: dependencies (Postgres) are reachable. Returns 503
  when not, so the service is pulled from the load balancer until it recovers.
"""

from typing import Literal

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from db.engine import ping

router = APIRouter(prefix="/health", tags=["health"])


class LivenessResponse(BaseModel):
    status: Literal["alive"]


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, str]


@router.get("/live", response_model=LivenessResponse)
async def liveness() -> LivenessResponse:
    return LivenessResponse(status="alive")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
)
async def readiness(response: Response) -> ReadinessResponse:
    db_ok = await ping()
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(status="not_ready", checks={"database": "unreachable"})
    return ReadinessResponse(status="ready", checks={"database": "ok"})
