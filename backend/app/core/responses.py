"""A model already built and validated, written as JSON in one pass.

FastAPI turns a returned model back into a dict and validates it again
against ``response_model`` before writing it: for a dashboard of 14 600
points that is most of the answer's time (docs/performance.md). The
routes that return large series write their model directly; the
``response_model`` stays on the route and documents the same shape.
"""

from __future__ import annotations

from fastapi import Response
from pydantic import BaseModel


def model_json(model: BaseModel) -> Response:
    """``model`` as its JSON answer (the same fields, the same values)."""
    return Response(model.model_dump_json(), media_type="application/json")
