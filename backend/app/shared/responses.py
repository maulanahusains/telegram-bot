from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SuccessResponse(BaseModel):
    ok: Literal[True] = True
    status: str = "processed"


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str | None = None


class ErrorResponse(BaseModel):
    ok: Literal[False] = False
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    database: Literal["healthy", "unhealthy"]
    uptime: int = Field(ge=0)
    version: str
    registered_modules: int = Field(ge=0)
    enabled_bots: int = Field(ge=0)
    healthy_bots: int = Field(ge=0)
    unhealthy_bots: int = Field(ge=0)


def success(status: str = "processed") -> dict[str, Any]:
    return SuccessResponse(status=status).model_dump()

