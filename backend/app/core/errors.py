"""Consistent error envelope and exception handlers.

Every error response has the shape required by Section 4:

    {"error": {"code": "...", "message": "...", "details": {...}}}
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("expense_tracker.errors")

STATUS_CODES = {
    400: "bad_request",
    401: "unauthenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
}


class APIError(Exception):
    """Raised by services/routers to produce a typed API error."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict | list | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict | list | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    payload: dict = {"code": code, "message": message, "details": details or {}}
    if request_id:
        if isinstance(details, list):
            payload["details"] = {"errors": details, "request_id": request_id}
        else:
            payload["details"] = {**(details or {}), "request_id": request_id}
    return JSONResponse(status_code=status_code, content={"error": payload})


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError):
        return error_response(
            exc.status_code, exc.code, exc.message, exc.details, _request_id(request)
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        details = [
            {
                "field": ".".join(str(part) for part in error.get("loc", []) if part != "body"),
                "message": error.get("msg", "Invalid value"),
                "type": error.get("type", "value_error"),
            }
            for error in exc.errors()
        ]
        return error_response(
            422, "validation_error", "The submitted data is invalid.", details, _request_id(request)
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        code = STATUS_CODES.get(exc.status_code, "error")
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return error_response(exc.status_code, code, message, None, _request_id(request))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Return the standard envelope instead of leaking a stack trace."""
        logger.exception(
            "rid=%s unhandled error on %s", _request_id(request), request.url.path
        )
        return error_response(
            500,
            "internal_error",
            "An unexpected error occurred.",
            None,
            _request_id(request),
        )
