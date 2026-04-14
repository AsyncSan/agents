"""Structured error codes and exception handling for the API."""

import logging
from enum import Enum

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

log = logging.getLogger("agentforge.errors")


class ErrorCode(str, Enum):
    """Machine-parseable error codes for all API errors."""

    # Auth (401, 403)
    INVALID_API_KEY = "invalid_api_key"
    ROLE_REQUIRED = "role_required"
    FORBIDDEN = "forbidden"

    # Not Found (404)
    AGENT_NOT_FOUND = "agent_not_found"
    TASK_NOT_FOUND = "task_not_found"
    PIPELINE_NOT_FOUND = "pipeline_not_found"
    SCHEDULE_NOT_FOUND = "schedule_not_found"
    WEBHOOK_NOT_FOUND = "webhook_not_found"
    SECRET_NOT_FOUND = "secret_not_found"
    PROVIDER_NOT_FOUND = "provider_not_found"
    CONSUMER_NOT_FOUND = "consumer_not_found"
    USER_NOT_FOUND = "user_not_found"
    RESULT_NOT_FOUND = "result_not_found"
    FILE_NOT_FOUND = "file_not_found"

    # Conflict (409)
    ALREADY_EXISTS = "already_exists"
    ALREADY_RATED = "already_rated"

    # Validation (400, 422)
    INVALID_INPUT = "invalid_input"
    INVALID_CRON = "invalid_cron"
    INVALID_DATE = "invalid_date"
    INVALID_SIGNATURE = "invalid_signature"
    BUDGET_EXCEEDED = "budget_exceeded"
    TASK_NOT_CANCELLABLE = "task_not_cancellable"
    TASK_NOT_COMPLETED = "task_not_completed"
    DATE_RANGE_TOO_LARGE = "date_range_too_large"
    INVALID_EVENT_TYPE = "invalid_event_type"

    # Rate Limits (429)
    RATE_LIMIT = "rate_limit"

    # Payment (400, 502, 503)
    BILLING_NOT_CONFIGURED = "billing_not_configured"
    PAYMENT_ERROR = "payment_error"
    PAYMENT_PROVIDER_ERROR = "payment_provider_error"
    INVALID_PAYMENT_RAIL = "invalid_payment_rail"
    WALLET_NOT_CONFIGURED = "wallet_not_configured"
    INVALID_WALLET = "invalid_wallet"
    CONNECT_NOT_READY = "connect_not_ready"
    SOLANA_VERIFICATION_FAILED = "solana_verification_failed"


class APIError(Exception):
    """Structured API error with machine-readable code."""

    def __init__(
        self,
        status_code: int,
        code: ErrorCode,
        message: str,
        details: dict | None = None,
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def register_error_handlers(app: FastAPI) -> None:
    """Register exception handlers on the FastAPI app."""

    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        body: dict = {
            "error": {
                "code": exc.code.value,
                "message": exc.message,
            }
        }
        if exc.details:
            body["error"]["details"] = exc.details
        if request_id:
            body["error"]["request_id"] = request_id
        return JSONResponse(
            status_code=exc.status_code,
            content=body,
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Catch-all for unhandled exceptions. Prevents stack trace leaks."""
        request_id = getattr(request.state, "request_id", None)
        log.exception(
            "Unhandled exception on %s %s (request_id=%s)",
            request.method,
            request.url.path,
            request_id,
        )
        body: dict = {
            "error": {
                "code": "internal_error",
                "message": "An unexpected error occurred",
            }
        }
        if request_id:
            body["error"]["request_id"] = request_id
        return JSONResponse(status_code=500, content=body)
