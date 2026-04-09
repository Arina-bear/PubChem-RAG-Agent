from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.errors.models import AppError
from app.errors.normalizer import build_agent_error_response, unknown_error
from app.schemas.agent import AgentRequest


router = APIRouter(tags=["agent"])


@router.post("/api/agent")
async def run_agent(payload: AgentRequest, request: Request) -> JSONResponse:
    container = request.app.state.container
    try:
        response = await container.agent_service.execute(payload, trace_id=request.state.trace_id)
    except AppError as error:
        return build_agent_error_response(trace_id=request.state.trace_id, error=error)
    except Exception:
        return build_agent_error_response(trace_id=request.state.trace_id, error=unknown_error())

    return JSONResponse(status_code=200, content=response.model_dump(mode="json"))
