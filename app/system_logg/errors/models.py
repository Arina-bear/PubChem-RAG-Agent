from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NO_MATCH = "NO_MATCH"
    AMBIGUOUS_QUERY = "AMBIGUOUS_QUERY"
    ASYNC_PENDING = "ASYNC_PENDING"
    RATE_LIMITED = "RATE_LIMITED"
    UPSTREAM_TIMEOUT = "UPSTREAM_TIMEOUT"
    UPSTREAM_UNAVAILABLE = "UPSTREAM_UNAVAILABLE"
    UNSUPPORTED_QUERY = "UNSUPPORTED_QUERY"
    INTERPRETATION_LOW_CONFIDENCE = "INTERPRETATION_LOW_CONFIDENCE"


class AppError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        http_status: int,
        retriable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.retriable = retriable
        self.details = details or {}
