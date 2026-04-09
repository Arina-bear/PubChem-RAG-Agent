from contextlib import asynccontextmanager
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.agent import router as agent_router
from app.api.routes.health import router as health_router
from app.api.routes.interpret import router as interpret_router
from app.api.routes.query import router as query_router
from app.config import get_settings
from app.container import AppContainer, build_container
from app.errors.models import AppError, ErrorCode
from app.errors.normalizer import build_agent_error_response, build_interpret_error_response, build_query_error_response, unknown_error


def create_app(container_override: AppContainer | None = None) -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        container = container_override or build_container(settings)
        app.state.container = container
        try:
            yield
        finally:
            close = getattr(container, "close", None)
            if callable(close):
                result = close()
                if hasattr(result, "__await__"):
                    await result

    app = FastAPI(
        title=settings.app_name,
        version=settings.api_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def attach_trace_id(request: Request, call_next):
        request.state.trace_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Trace-ID"] = request.state.trace_id
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        app_error = AppError(
            ErrorCode.VALIDATION_ERROR,
            "Запрос не прошёл валидацию.",
            http_status=422,
            details={"errors": exc.errors()},
        )
        if request.url.path.endswith("/api/agent"):
            return build_agent_error_response(trace_id=request.state.trace_id, error=app_error)
        if request.url.path.endswith("/api/interpret"):
            return build_interpret_error_response(trace_id=request.state.trace_id, error=app_error)
        return build_query_error_response(trace_id=request.state.trace_id, error=app_error)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        app_error = exc if isinstance(exc, AppError) else unknown_error()
        if request.url.path.endswith("/api/agent"):
            return build_agent_error_response(trace_id=request.state.trace_id, error=app_error)
        if request.url.path.endswith("/api/interpret"):
            return build_interpret_error_response(trace_id=request.state.trace_id, error=app_error)
        if request.url.path.endswith("/api/query"):
            return build_query_error_response(trace_id=request.state.trace_id, error=app_error)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "trace_id": request.state.trace_id,
                "error": {
                    "code": "UNHANDLED",
                    "message": f"Непредвиденная ошибка приложения: {exc}",
                },
            },
        )

    app.include_router(health_router)
    app.include_router(query_router)
    app.include_router(interpret_router)
    app.include_router(agent_router)
    return app


app = create_app()
