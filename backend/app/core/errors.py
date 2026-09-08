"""Typed application errors mapped to HTTP responses.

Services raise these domain errors; a single exception handler turns
them into consistent JSON payloads, keeping HTTP concerns out of the
service layer.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for domain errors carrying an HTTP status code."""

    status_code: int = 400
    code: str = "error"

    def __init__(self, message: str) -> None:
        """Store the human-readable ``message``."""
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    """Requested entity does not exist or is not visible."""

    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    """Request conflicts with the current state (e.g. duplicate)."""

    status_code = 409
    code = "conflict"


class InvalidInputError(AppError):
    """Input is well-formed but violates a domain rule."""

    status_code = 422
    code = "invalid_input"


class AuthError(AppError):
    """Authentication failed or credentials are missing."""

    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppError):
    """Principal is authenticated but lacks the required scope."""

    status_code = 403
    code = "forbidden"
