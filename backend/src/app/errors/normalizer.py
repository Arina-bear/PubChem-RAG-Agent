from fastapi.responses import JSONResponse

from app.errors.models import AppError, ErrorCode
from app.schemas.agent import AgentResponseEnvelope
from app.schemas.common import ErrorPayload, PresentationHints, WarningMessage
from app.schemas.interpret import InterpretResponseEnvelope
from app.schemas.query import QueryResponseEnvelope


def normalize_error_payload(error: AppError) -> ErrorPayload:
    return ErrorPayload(
        code=error.code.value,
        message=error.message,
        retriable=error.retriable,
        details=error.details or None,
    )


def build_query_error_response(
    *,
    trace_id: str,
    error: AppError,
    source: str = "pubchem-pug-rest",
    warnings: list[WarningMessage] | None = None,
    presentation_hints: PresentationHints | None = None,
) -> JSONResponse:
    envelope = QueryResponseEnvelope(
        trace_id=trace_id,
        source=source,  # type: ignore[arg-type]
        status="error",
        normalized=None,
        raw=None,
        presentation_hints=presentation_hints or PresentationHints(),
        warnings=warnings or [],
        error=normalize_error_payload(error),
    )
    return JSONResponse(status_code=error.http_status, content=envelope.model_dump(mode="json"))


def build_interpret_error_response(
    *,
    trace_id: str,
    error: AppError,
    warnings: list[WarningMessage] | None = None,
) -> JSONResponse:
    envelope = InterpretResponseEnvelope(
        trace_id=trace_id,
        status="error",
        normalized=None,
        raw=None,
        warnings=warnings or [],
        error=normalize_error_payload(error),
    )
    return JSONResponse(status_code=error.http_status, content=envelope.model_dump(mode="json"))


def build_agent_error_response(
    *,
    trace_id: str,
    error: AppError,
    warnings: list[WarningMessage] | None = None,
    presentation_hints: PresentationHints | None = None,
) -> JSONResponse:
    envelope = AgentResponseEnvelope(
        trace_id=trace_id,
        status="error",
        normalized=None,
        raw=None,
        warnings=warnings or [],
        presentation_hints=presentation_hints
        or PresentationHints(active_tab="answer", available_tabs=["answer", "compounds", "analysis", "tools", "json"]),
        error=normalize_error_payload(error),
    )
    return JSONResponse(status_code=error.http_status, content=envelope.model_dump(mode="json"))


def unknown_error() -> AppError:
    return AppError(
        ErrorCode.UPSTREAM_UNAVAILABLE,
        "Непредвиденная ошибка приложения.",
        http_status=500,
        retriable=True,
    )
