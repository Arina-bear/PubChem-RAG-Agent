from __future__ import annotations

import asyncio

from langgraph.errors import GraphRecursionError
from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

from app.errors.models import AppError, ErrorCode


def normalize_agent_exception(error: Exception) -> AppError:
    if isinstance(error, GraphRecursionError):
        return AppError(
            ErrorCode.TOOL_LOOP_ABORTED,
            "Агент превысил лимит шагов tool calling и был остановлен.",
            http_status=502,
            retriable=False,
        )

    if isinstance(error, RateLimitError):
        return AppError(
            ErrorCode.RATE_LIMITED,
            "LLM временно отклонила запрос из-за rate limit. Попробуйте повторить через несколько секунд.",
            http_status=429,
            retriable=True,
        )

    if isinstance(error, APITimeoutError):
        return AppError(
            ErrorCode.UPSTREAM_TIMEOUT,
            "LLM не успела ответить вовремя.",
            http_status=504,
            retriable=True,
        )

    if isinstance(error, asyncio.TimeoutError):
        return AppError(
            ErrorCode.UPSTREAM_TIMEOUT,
            "Агент превысил допустимое время выполнения.",
            http_status=504,
            retriable=True,
        )

    if isinstance(error, APIConnectionError):
        return AppError(
            ErrorCode.UPSTREAM_UNAVAILABLE,
            "Не удалось связаться с LLM provider.",
            http_status=502,
            retriable=True,
        )

    if isinstance(error, APIStatusError):
        if error.status_code == 429:
            return AppError(
                ErrorCode.RATE_LIMITED,
                "LLM provider временно отклоняет запросы из-за rate limit.",
                http_status=429,
                retriable=True,
            )
        return AppError(
            ErrorCode.UPSTREAM_UNAVAILABLE,
            "LLM provider вернул ошибку и не смог завершить агентный запрос.",
            http_status=502,
            retriable=error.status_code >= 500,
            details={"status_code": error.status_code},
        )

    if isinstance(error, AppError):
        return error

    return AppError(
        ErrorCode.UPSTREAM_UNAVAILABLE,
        "Непредвиденная ошибка во время выполнения агента.",
        http_status=502,
        retriable=True,
    )
