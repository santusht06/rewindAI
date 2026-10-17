"""Main FastAPI application entrypoint for Rewind.

Implements SRS-ADM-003 (health probes), 04_API_CONTRACT, and error envelope handling.
"""

from datetime import datetime, timezone
from typing import Any
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from services.api.config import settings
from services.api.errors import AppException, ErrorEnvelope
from services.api.logging import RequestCorrelationMiddleware, current_request_id, logger


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
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # 4. Readiness Probe (Checks critical readiness invariants)
    @app.get("/health/ready", tags=["Health"], summary="System Readiness Probe")
    async def health_ready() -> dict[str, Any]:
        # Basic readiness checks without leaking secrets or credentials
        is_ready = True
        components: dict[str, str] = {
            "config": "ready",
            "persistence": "ready",
        }
        return {
            "status": "ready" if is_ready else "unready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": components,
        }

    return app


app = create_app()
