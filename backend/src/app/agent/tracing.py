import json
import re
from functools import lru_cache
from dataclasses import dataclass, field
from typing import Any

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from app.config import Settings


def _to_json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


@dataclass
class ToolTraceEvent:
    step: int
    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any] | None = None
    error_message: str | None = None


@dataclass
class ToolTraceRecorder:
    events: list[ToolTraceEvent] = field(default_factory=list)

    def record(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        result: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> None:
        self.events.append(
            ToolTraceEvent(
                step=len(self.events) + 1,
                tool_name=tool_name,
                arguments=_to_json_safe(arguments),
                result=_to_json_safe(result) if result is not None else None,
                error_message=error_message,
            )
        )


@dataclass
class LangChainTracingConfig:
    callbacks: list[Any] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    client: Langfuse | None = None

    def flush(self) -> None:
        if self.client is not None:
            self.client.flush()


@lru_cache(maxsize=1)
def _build_langfuse_client(
    public_key: str,
    secret_key: str,
    base_url: str,
    environment: str,
) -> Langfuse:
    return Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        base_url=base_url,
        environment=environment,
    )


def build_langchain_tracing_config(
    settings: Settings,
    *,
    trace_id: str,
    provider: str,
) -> LangChainTracingConfig:
    metadata = {
        "langfuse_session_id": trace_id,
        "langfuse_tags": ["pubchem-agent", provider],
        "agent_provider": provider,
        "app_trace_id": trace_id,
    }

    public_key = settings.langfuse_public_key.get_secret_value() if settings.langfuse_public_key else None
    secret_key = settings.langfuse_secret_key.get_secret_value() if settings.langfuse_secret_key else None
    if not public_key or not secret_key:
        return LangChainTracingConfig(metadata=metadata)

    client = _build_langfuse_client(
        public_key=public_key,
        secret_key=secret_key,
        base_url=settings.langfuse_base_url,
        environment=settings.environment,
    )
    trace_context = {"trace_id": trace_id} if re.fullmatch(r"[0-9a-f]{32}", trace_id) else None
    handler = CallbackHandler(
        public_key=public_key,
        update_trace=True,
        trace_context=trace_context,
    )
    return LangChainTracingConfig(
        callbacks=[handler],
        metadata=metadata,
        client=client,
    )
