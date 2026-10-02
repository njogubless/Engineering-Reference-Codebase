"""Application factory.

`create_app()` instead of a module-level app with side effects: tests build a
fresh app per test, and nothing connects to anything at import time.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.health.router import router as health_router
from app.meta.router import router as meta_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_format)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Shared clients are created once per process and closed on shutdown.
        app.state.engine = create_async_engine(
            settings.async_database_url,
            pool_pre_ping=True,
            connect_args={"timeout": 5},  # fail fast when the database is unreachable
        )
        app.state.redis = Redis.from_url(
            str(settings.redis_url),
            socket_timeout=settings.readiness_timeout_seconds,
            socket_connect_timeout=settings.readiness_timeout_seconds,
        )
        try:
            yield
        finally:
            await app.state.redis.aclose()
            await app.state.engine.dispose()

    app = FastAPI(
        title="Reference API (FastAPI)",
        version="1.0.0",
        debug=settings.debug,
        lifespan=lifespan,
    )
    # Everything that reads settings through `Depends(get_settings)` sees the
    # same object this app was built with (matters when tests pass their own).
    app.dependency_overrides[get_settings] = lambda: settings
    # add_middleware wraps: the LAST added is the OUTERMOST. CORS must be
    # outermost so that even the 500 responses RequestContextMiddleware builds
    # get CORS headers — otherwise the browser hides the error from the app.
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Idempotency-Key"],
        # Browsers hide response headers from JavaScript unless exposed.
        expose_headers=["X-Request-ID", "Retry-After"],
        max_age=600,
    )
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(meta_router)
    return app
