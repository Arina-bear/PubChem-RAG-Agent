import json
import logging
import re
from functools import lru_cache
from dataclasses import dataclass, field
from typing import Any

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from app.config import Settings

_TRACE_ID_PATTERN = re.compile(r"[0-9a-f]{32}")
logger = logging.getLogger(__name__)


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
        if self.client is None:
            return
        try:
            self.client.flush()
        except Exception as exc:
            logger.warning("Langfuse flush failed", exc_info=exc)
            return


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
    trace_context = {"trace_id": trace_id} if _TRACE_ID_PATTERN.fullmatch(trace_id) else None
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


def build_langfuse_client_from_settings(settings: Settings) -> Langfuse | None:
    public_key = settings.langfuse_public_key.get_secret_value() if settings.langfuse_public_key else None
    secret_key = settings.langfuse_secret_key.get_secret_value() if settings.langfuse_secret_key else None
    if not public_key or not secret_key:
        return None
    return _build_langfuse_client(
        public_key=public_key,
        secret_key=secret_key,
        base_url=settings.langfuse_base_url,
        environment=settings.environment,
    )


def record_manual_agent_trace(
    settings: Settings,
    *,
    trace_id: str,
    name: str,
    provider: str,
    model_name: str,
    input_payload: dict[str, Any],
    output_payload: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> None:
    client = build_langfuse_client_from_settings(settings)
    if client is None:
        return

    metadata_payload = dict(metadata or {})
    session_id = metadata_payload.pop("langfuse_session_id", None)
    user_id = metadata_payload.pop("langfuse_user_id", None)
    extra_tags = metadata_payload.pop("langfuse_tags", None)
    trace_tags = ["pubchem-agent", provider]
    if isinstance(extra_tags, list):
        for tag in extra_tags:
            if isinstance(tag, str) and tag not in trace_tags:
                trace_tags.append(tag)

    trace_metadata = {
        "agent_provider": provider,
        "agent_model": model_name,
        "app_trace_id": trace_id,
        **metadata_payload,
    }
    trace_context = {"trace_id": trace_id} if _TRACE_ID_PATTERN.fullmatch(trace_id) else None

    try:
        with client.start_as_current_observation(
            trace_context=trace_context,
            name=name,
            as_type="agent",
            input=_to_json_safe(input_payload),
            output=_to_json_safe(output_payload),
            metadata=_to_json_safe(trace_metadata),
            model=model_name,
        ):
            client.update_current_trace(
                name=name,
                user_id=user_id,
                session_id=session_id,
                input=_to_json_safe(input_payload),
                output=_to_json_safe(output_payload),
                metadata=_to_json_safe(trace_metadata),
                tags=trace_tags,
            )
        client.flush()
    except Exception as exc:
        logger.warning("Manual Langfuse trace export failed", exc_info=exc)
        return


def shutdown_langfuse_client(settings: Settings) -> None:
    client = build_langfuse_client_from_settings(settings)
    if client is None:
        return
    try:
        client.shutdown()
    except Exception:
        return
