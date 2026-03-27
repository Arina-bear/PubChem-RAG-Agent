from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.errors.models import AppError
from app.errors.normalizer import build_interpret_error_response, unknown_error
from app.schemas.interpret import InterpretRequest


router = APIRouter(tags=["interpret"])


@router.post("/api/interpret")
async def interpret_query(payload: InterpretRequest, request: Request) -> JSONResponse:
    container = request.app.state.container
    try:
        response = container.interpret_service.execute(payload)
    except AppError as error:
        return build_interpret_error_response(trace_id=request.state.trace_id, error=error)
    except Exception:
        return build_interpret_error_response(trace_id=request.state.trace_id, error=unknown_error())

    return JSONResponse(status_code=200, content=response.model_dump(mode="json"))
