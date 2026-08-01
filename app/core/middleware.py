from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from app.core.logging import (
    bind_contextvars,
    clear_contextvars,
    get_logger,
)
from app.shared.exceptions import PlatformError
from app.shared.responses import ErrorDetail, ErrorResponse

logger = get_logger(__name__)
RequestHandler = Callable[[Request], Awaitable[Response]]


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestHandler) -> Response:
        clear_contextvars()
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        bind_contextvars(request_id=request_id)
        request.state.request_id = request_id
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            await logger.ainfo(
                "http_request_completed",
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                execution_time_ms=elapsed_ms,
            )
            clear_contextvars()


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(PlatformError)
    async def platform_error_handler(
        request: Request, error: PlatformError
    ) -> JSONResponse:
        await logger.awarning(
            "platform_request_error",
            error_code=error.code,
            status_code=error.status_code,
        )
        return _error_response(
            request, error.status_code, error.code, error.public_message
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, _error: RequestValidationError
    ) -> JSONResponse:
        return _error_response(
            request, 422, "request_validation_error", "Request data is invalid."
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request, error: StarletteHTTPException
    ) -> JSONResponse:
        messages = {
            400: "Request is invalid.",
            404: "Resource was not found.",
            405: "Method is not allowed.",
            413: "Request body is too large.",
        }
        return _error_response(
            request,
            error.status_code,
            f"http_{error.status_code}",
            messages.get(error.status_code, "Request could not be processed."),
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(
        request: Request, error: Exception
    ) -> JSONResponse:
        await logger.aexception(
            "unexpected_request_error", error_type=type(error).__name__
        )
        return _error_response(
            request, 500, "internal_server_error", "An internal error occurred."
        )


def _error_response(
    request: Request, status_code: int, code: str, message: str
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    body = ErrorResponse(
        error=ErrorDetail(code=code, message=message, request_id=request_id)
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())
