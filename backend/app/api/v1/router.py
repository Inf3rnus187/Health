"""Aggregate router mounting every v1 endpoint group."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    capture,
    events,
    ingest,
    measurements,
    metrics,
    tokens,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(tokens.router)
api_router.include_router(metrics.router)
api_router.include_router(measurements.router)
api_router.include_router(events.router)
api_router.include_router(ingest.router)
api_router.include_router(capture.router)
