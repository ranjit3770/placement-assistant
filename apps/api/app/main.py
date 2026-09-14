import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException

from app.core.config import Settings
from app.core.logging import configure_logging
from app.core.security import Principal, current_principal
from app.infrastructure.dependencies import Dependencies
from sqlalchemy.exc import IntegrityError, ProgrammingError
import psycopg.errors


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()  # type: ignore[call-arg]
    configure_logging()
    logger = logging.getLogger("placement")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.dependencies = Dependencies(config)
        try:
            yield
        finally:
            await app.state.dependencies.close()

    app = FastAPI(
        title="Placement Intelligence API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/v1/docs" if config.app_env in {"development", "test"} else None,
        openapi_url="/api/v1/openapi.json" if config.app_env in {"development", "test"} else None,
        redoc_url=None,
    )
    app.state.settings = config

    def error(request: Request, code: str, status: int) -> JSONResponse:
        return JSONResponse(
            {"error": {"code": code, "request_id": request.state.request_id}}, status_code=status
        )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.request_id = str(uuid4())
        start = perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            import traceback

            traceback.print_exc()
            logger.error(
                "request_failed",
                extra={
                    "fields": {
                        "request_id": request.state.request_id,
                        "exception_type": type(exc).__name__,
                    }
                },
            )
            response = error(request, "INTERNAL_ERROR", 500)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        logger.info(
            "request",
            extra={
                "fields": {
                    "request_id": request.state.request_id,
                    "trace_id": request.state.request_id,
                    "method": request.method,
                    "route": getattr(request.scope.get("route"), "path", "unmatched"),
                    "status": response.status_code,
                    "latency_ms": round((perf_counter() - start) * 1000, 2),
                }
            },
        )
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        codes = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
        }
        code = codes.get(exc.status_code, "REQUEST_ERROR")
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            code = exc.detail["code"]
        response = error(request, code, exc.status_code)
        if exc.headers:
            response.headers.update(exc.headers)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error(request, "VALIDATION_ERROR", 422)

    @app.exception_handler(IntegrityError)
    async def db_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        return error(request, "CONFLICT", 409)

    @app.exception_handler(ProgrammingError)
    async def db_programming_error(request: Request, exc: ProgrammingError) -> JSONResponse:
        if isinstance(exc.orig, psycopg.errors.RaiseException):
            return error(request, "INVALID_OPERATION", 400)
        raise exc


    @app.get("/metrics")
    async def metrics(request: Request) -> JSONResponse:
        # Vendor-neutral metrics contract
        # Standard collector scrapes this endpoint
        return JSONResponse(
            {
                "service": "placement-api",
                "version": "0.1.0",
                "metrics": {
                    # Example placeholders for scraper
                    "requests_total": 0,
                    "errors_total": 0,
                    "active_connections": 0
                }
            },
            status_code=200
        )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "placement-api"}

    @app.get("/ready")
    async def ready(request: Request) -> JSONResponse:
        checks = await request.app.state.dependencies.check()
        # PostgreSQL is critical to decisions; AI/vector/cache outages must not disable them.
        ready = checks["postgres"] == "up"
        return JSONResponse(
            {
                "status": "ready" if ready else "not_ready",
                "dependencies": checks,
                "degraded": any(state != "up" for state in checks.values()),
            },
            status_code=200 if ready else 503,
        )

    @app.get("/api/v1/auth/me", response_model=Principal)
    async def me(principal: Annotated[Principal, Depends(current_principal)]) -> Principal:
        return principal

    from app.api.routers import (
        companies,
        opportunities,
        requirements,
        policies,
        eligibility,
            copilot,
        agent,
    )

    app.include_router(companies.router, prefix="/api/v1")
    app.include_router(opportunities.router, prefix="/api/v1")
    app.include_router(requirements.router, prefix="/api/v1")
    app.include_router(policies.router, prefix="/api/v1")
    app.include_router(eligibility.router, prefix="/api/v1")
    app.include_router(copilot.router, prefix="/api/v1")
    app.include_router(agent.router, prefix="/api/v1")

    return app
