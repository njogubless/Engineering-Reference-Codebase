"""Liveness and readiness probes. Same semantics as the Django version."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


class Liveness(BaseModel):
    status: Literal["ok"] = "ok"


class Readiness(BaseModel):
    status: Literal["ok", "unavailable"]
    checks: dict[str, Literal["ok", "fail"]]


async def check_database(request: Request) -> None:
    engine: AsyncEngine = request.app.state.engine
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def check_redis(request: Request) -> None:
    redis: Redis = request.app.state.redis
    await redis.ping()


# Only dependencies without which this process cannot serve requests.
READINESS_CHECKS: dict[str, Callable[[Request], Awaitable[None]]] = {
    "database": check_database,
    "redis": check_redis,
}


@router.get("/live", operation_id="getLiveness")
async def liveness() -> Liveness:
    """Process is running. Never checks dependencies."""
    return Liveness()


@router.get(
    "/ready",
    operation_id="getReadiness",
    responses={503: {"model": Readiness, "description": "A dependency check failed."}},
)
async def readiness(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Readiness:
    """Process can serve traffic. Checks run concurrently, each with a timeout."""
    timeout = settings.readiness_timeout_seconds

    async def run(name: str, check: Callable[[Request], Awaitable[None]]) -> Literal["ok", "fail"]:
        try:
            await asyncio.wait_for(check(request), timeout=timeout)
        except Exception:
            # Broad catch is deliberate: any failure (including timeout) means
            # "not ready". Details go to logs only — this endpoint is public.
            logger.warning("readiness_check_failed", extra={"check": name}, exc_info=True)
            return "fail"
        return "ok"

    names = list(READINESS_CHECKS)
    results = await asyncio.gather(*(run(name, READINESS_CHECKS[name]) for name in names))
    checks = dict(zip(names, results, strict=True))
    ready = all(result == "ok" for result in results)
    response.status_code = 200 if ready else 503
    return Readiness(status="ok" if ready else "unavailable", checks=checks)
