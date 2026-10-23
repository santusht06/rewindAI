"""Main FastAPI application entrypoint for Rewind.

Implements SRS-ADM-003 (health probes), 04_API_CONTRACT, and error envelope handling.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from services.api.config import settings
from services.api.errors import AppException, ErrorEnvelope
from services.api.infrastructure.database import engine
from services.api.logging import RequestCorrelationMiddleware, current_request_id, logger


async def check_database_connectivity(database_engine: AsyncEngine) -> bool:
    """Check the configured database with a bounded, read-only query."""
    try:
        async with asyncio.timeout(2.0):
            async with database_engine.connect() as connection:
                result = await connection.execute(text("SELECT 1"))
                value = result.scalar_one()
                return isinstance(value, int) and value == 1
    except (SQLAlchemyError, TimeoutError) as exc:
        logger.warning("Readiness database check failed: %s", type(exc).__name__)
        return False


def create_app() -> FastAPI:
    """Factory creating configured FastAPI instance."""
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Rewind — Fire TV AI Story Companion Backend API",
        docs_url="/docs" if not settings.is_production() else None,
        redoc_url="/redoc" if not settings.is_production() else None,
    )

    # 1. Register Middlewares
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if not settings.is_production() else ["https://firetv.amazon.com"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestCorrelationMiddleware)

    # 2. Register Global Exception Handlers
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        req_id = current_request_id.get()
        envelope = ErrorEnvelope(
            code=exc.code,
            message=exc.message,
            request_id=req_id,
            details=exc.details,
        )
        logger.warning("Domain exception: code=%s message=%s", exc.code, exc.message)
        return JSONResponse(status_code=exc.status_code, content=envelope.model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        req_id = current_request_id.get()
        envelope = ErrorEnvelope(
            code="VALIDATION_ERROR",
            message="Request input validation failed",
            request_id=req_id,
            details={"errors": exc.errors()},
        )
        logger.warning("Validation failure: %s", exc.errors())
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=envelope.model_dump())

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        req_id = current_request_id.get()
        logger.exception("Unhandled server exception: %s", str(exc))
        envelope = ErrorEnvelope(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred. Please try again later.",
            request_id=req_id,
            details=None,
        )
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=envelope.model_dump())

    # 3. Liveness Probe (Does not depend on external services)
    @app.get("/health/live", tags=["Health"], summary="Process Liveness Probe")
    async def health_live() -> dict[str, Any]:
        return {
            "status": "alive",
            "environment": settings.environment,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    # 4. Readiness Probe (Checks critical readiness invariants)
    @app.get("/health/ready", tags=["Health"], summary="System Readiness Probe")
    async def health_ready() -> JSONResponse:
        persistence_ready = await check_database_connectivity(engine)
        is_ready = persistence_ready
        components: dict[str, str] = {
            "config": "ready",
            "persistence": "ready" if persistence_ready else "unavailable",
        }
        return JSONResponse(
            status_code=status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "ready" if is_ready else "unready",
                "timestamp": datetime.now(UTC).isoformat(),
                "components": components,
            },
        )

    # 5. Metrics & Operational Telemetry Probe (OPS-001, OPS-004)
    from services.api.telemetry import telemetry

    @app.get("/health/metrics", tags=["Health"], summary="Operational Metrics and Latency Percentiles")
    async def health_metrics() -> dict[str, Any]:
        return telemetry.get_summary()

    @app.get("/metrics", tags=["Health"], summary="Operational Metrics (Alias)", include_in_schema=False)
    async def metrics_alias() -> dict[str, Any]:
        return telemetry.get_summary()

    # 6. Mount API v1 Routers
    from services.api.api.v1 import api_v1_router
    app.include_router(api_v1_router)

    # 7. Mount 10-ft Fire TV Web Client (S1 - S9)
    from pathlib import Path

    from fastapi.responses import RedirectResponse
    from starlette.staticfiles import StaticFiles

    client_dir = Path(__file__).resolve().parent.parent.parent / "apps" / "tv-client"
    dist_dir = client_dir / "dist"
    static_dir = dist_dir if (dist_dir / "index.html").exists() else client_dir
    if static_dir.exists():
        from fastapi.responses import FileResponse
        app.mount("/tv", StaticFiles(directory=str(static_dir), html=True), name="tv-client")

        @app.get("/", include_in_schema=False)
        async def root_redirect() -> RedirectResponse:
            return RedirectResponse(url="/tv/")

        @app.get("/favicon.ico", include_in_schema=False)
        async def favicon_route() -> FileResponse:
            fav_path = static_dir / "favicon.ico"
            if not fav_path.exists():
                fav_path = client_dir / "favicon.ico"
            return FileResponse(fav_path)

    # 8. Mount Media Assets for Video Playback (REWIND-REQ-018)
    from services.api.media.storage import LocalStorageProvider, get_media_storage
    storage = get_media_storage()
    if isinstance(storage, LocalStorageProvider) and storage.base_dir.exists():
        app.mount("/media", StaticFiles(directory=str(storage.base_dir)), name="media-assets")

    return app




app = create_app()
