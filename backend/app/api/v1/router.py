"""Aggregate router mounting every v1 endpoint group."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    automations,
    automations_run,
    capture,
    dashboard,
    events,
    export,
    ingest,
    measurements,
    metrics,
    photos,
    photos_media,
    reports,
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
api_router.include_router(photos.router)
api_router.include_router(photos_media.router)
api_router.include_router(dashboard.router)
api_router.include_router(export.router)
api_router.include_router(reports.router)
api_router.include_router(automations.router)
api_router.include_router(automations_run.router)
