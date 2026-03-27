from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.errors.models import AppError
from app.errors.normalizer import build_query_error_response, unknown_error
from app.schemas.query import ManualQuerySpec


router = APIRouter(tags=["query"])


@router.post("/api/query")
async def query_compounds(spec: ManualQuerySpec, request: Request) -> JSONResponse:
    container = request.app.state.container
    try:
        response = await container.query_service.execute(spec)
    except AppError as error:
        return build_query_error_response(trace_id=request.state.trace_id, error=error)
    except Exception:
        return build_query_error_response(trace_id=request.state.trace_id, error=unknown_error())

    return JSONResponse(status_code=200, content=response.model_dump(mode="json"))
