"""ORM models package.

Importing this module registers every table on ``Base.metadata`` so that
Alembic autogeneration and ``create_all`` see the full fixed schema.
"""

from __future__ import annotations

from app.models.audit import AuditLog
from app.models.automation import Automation
from app.models.base import Base
from app.models.event import Event
from app.models.health_raw import (
    ClinicalDocument,
    ClinicalObservation,
    EcgRecord,
    HealthSample,
    ImportJob,
    RouteFile,
    Workout,
)
from app.models.mapping import IngestMapping
from app.models.measurement import Measurement
from app.models.metric import MetricDefinition
from app.models.photo import Photo, PhotoAnalysis
from app.models.report import Report
from app.models.session import AuthSession
from app.models.token import ApiToken
from app.models.user import User

__all__ = [
    "ApiToken",
    "AuditLog",
    "Automation",
    "AuthSession",
    "Base",
    "ClinicalDocument",
    "ClinicalObservation",
    "EcgRecord",
    "Event",
    "HealthSample",
    "ImportJob",
    "IngestMapping",
    "Measurement",
    "MetricDefinition",
    "Photo",
    "PhotoAnalysis",
    "Report",
    "RouteFile",
    "User",
    "Workout",
]
