"""FastAPI application factory and wiring.

Assembles middleware, error handling and the versioned router. Import
``app`` for ASGI servers (``uvicorn app.main:app``).
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import health
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging
from app.core.middleware import SecurityHeadersMiddleware

settings = get_settings()

TAGS = [
    {"name": "auth", "description": "Login, refresh and profile."},
    {"name": "tokens", "description": "Scoped machine API tokens."},
    {"name": "metrics", "description": "Dynamic metric registry."},
    {"name": "measurements", "description": "Facts and aggregates."},
    {"name": "events", "description": "Grouped measurement contexts."},
    {"name": "ingest", "description": "Apple Watch / CPAP ingestion."},
    {"name": "capture", "description": "Mode B capture sessions."},
    {"name": "photos", "description": "Photo pipeline and AI analysis."},
    {"name": "dashboard", "description": "Per-domain plottable series."},
    {"name": "health", "description": "Liveness and readiness."},
]


def _register_errors(app: FastAPI) -> None:
    """Map domain errors to consistent JSON responses."""

    @app.exception_handler(AppError)
    async def _handle(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "detail": exc.message},
        )


def _add_cors(app: FastAPI) -> None:
    """Enable a restricted CORS policy when origins are configured."""
    if not settings.cors_origins:
        return
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    configure_logging()
    prefix = settings.api_v1_prefix
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        summary="Self-hosted personal health & training hub.",
        openapi_tags=TAGS,
        openapi_url=f"{prefix}/openapi.json",
        docs_url=f"{prefix}/docs",
        redoc_url=f"{prefix}/redoc",
    )
    app.add_middleware(SecurityHeadersMiddleware)
    _add_cors(app)
    _register_errors(app)
    app.include_router(health.router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
