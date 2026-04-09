from app.errors.models import AppError, ErrorCode
from app.errors.normalizer import build_agent_error_response, build_query_error_response


def test_query_error_response_uses_envelope_shape() -> None:
    response = build_query_error_response(
        trace_id="trace-123",
        error=AppError(
            ErrorCode.UNSUPPORTED_QUERY,
            "Not supported yet.",
            http_status=400,
        ),
    )

    assert response.status_code == 400
    assert b"trace-123" in response.body
    assert b"UNSUPPORTED_QUERY" in response.body


def test_agent_error_response_uses_agent_envelope_shape() -> None:
    response = build_agent_error_response(
        trace_id="agent-trace-123",
        error=AppError(
            ErrorCode.LLM_NOT_CONFIGURED,
            "Model is not configured.",
            http_status=500,
        ),
    )

    assert response.status_code == 500
    assert b"agent-trace-123" in response.body
    assert b"LLM_NOT_CONFIGURED" in response.body
