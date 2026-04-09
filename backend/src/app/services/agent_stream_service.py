from collections.abc import Callable
from typing import Any
import uuid

from langgraph.errors import GraphRecursionError

from app.adapter.pubchem_adapter import PubChemAdapter
from app.agent.runtime import PreparedAgentRuntime, prepare_agent_runtime
from app.config import Settings
from app.errors.models import AppError, ErrorCode
from app.schemas.agent import AgentRequest, AgentResponseEnvelope, AgentToolTraceEntry
from app.services.agent_service import build_agent_response_envelope


class AgentStreamService:
    def __init__(
        self,
        settings: Settings,
        adapter: PubChemAdapter,
        *,
        runtime_factory: Callable[..., PreparedAgentRuntime] = prepare_agent_runtime,
    ) -> None:
        self.settings = settings
        self.adapter = adapter
        self.runtime_factory = runtime_factory

    async def execute(
        self,
        request: AgentRequest,
        *,
        trace_id: str | None = None,
        extra_callbacks: list[Any] | None = None,
        metadata_overrides: dict[str, Any] | None = None,
    ) -> AgentResponseEnvelope:
        resolved_trace_id = trace_id or str(uuid.uuid4())
        runtime = self.runtime_factory(
            self.settings,
            self.adapter,
            provider=request.provider,
            trace_id=resolved_trace_id,
        )

        invoke_config = dict(runtime.invoke_config)
        callbacks = list(invoke_config.get("callbacks", []))
        if extra_callbacks:
            callbacks.extend(extra_callbacks)
        if callbacks:
            invoke_config["callbacks"] = callbacks

        metadata = dict(invoke_config.get("metadata", {}))
        if metadata_overrides:
            metadata.update(metadata_overrides)
        invoke_config["metadata"] = metadata

        try:
            result = await runtime.agent.ainvoke(
                {"messages": [{"role": "user", "content": request.text}]},
                config=invoke_config,
            )
        except GraphRecursionError as exc:
            raise AppError(
                ErrorCode.TOOL_LOOP_ABORTED,
                "Агент превысил лимит шагов tool calling и был остановлен.",
                http_status=502,
                retriable=False,
            ) from exc

        structured = result.get("structured_response")
        if structured is None:
            raise AppError(
                ErrorCode.UPSTREAM_UNAVAILABLE,
                "LLM не вернула структурированный финальный ответ.",
                http_status=502,
                retriable=True,
            )

        tool_trace = [
            AgentToolTraceEntry(
                step=event.step,
                tool_name=event.tool_name,
                arguments=event.arguments,
                result=event.result,
                error_message=event.error_message,
            )
            for event in runtime.recorder.events
        ]
        return build_agent_response_envelope(
            trace_id=resolved_trace_id,
            request=request,
            runtime=runtime,
            result=result,
            tool_trace=tool_trace,
        )
