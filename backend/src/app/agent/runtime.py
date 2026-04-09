import json
from dataclasses import dataclass
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware, wrap_tool_call
from langchain_core.messages import ToolMessage

from app.adapter.pubchem_adapter import PubChemAdapter
from app.agent.model_factory import build_chat_model
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import build_pubchem_tools
from app.agent.tracing import LangChainTracingConfig, ToolTraceRecorder, build_langchain_tracing_config
from app.config import Settings
from app.schemas.agent import LLMProviderName


@dataclass
class PreparedAgentRuntime:
    agent: Any
    recorder: ToolTraceRecorder
    invoke_config: dict[str, Any]
    provider: LLMProviderName
    model_name: str
    tracing: LangChainTracingConfig


def _build_duplicate_tool_call_guard() -> Any:
    seen_signatures: set[str] = set()

    @wrap_tool_call(name="deduplicate_pubchem_tool_calls")
    async def deduplicate_pubchem_tool_calls(request, handler):  # noqa: ANN001
        signature = json.dumps(
            {
                "name": request.tool_call["name"],
                "args": request.tool_call.get("args", {}),
            },
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
        if signature in seen_signatures:
            return ToolMessage(
                content=json.dumps(
                    {
                        "ok": False,
                        "error": {
                            "code": "DUPLICATE_TOOL_CALL",
                            "message": "The same PubChem tool call was already executed in this run. Reuse the previous result or answer the user directly.",
                            "retriable": False,
                            "details": None,
                        },
                    },
                    ensure_ascii=False,
                ),
                name=request.tool_call["name"],
                tool_call_id=request.tool_call["id"],
                status="error",
            )

        seen_signatures.add(signature)
        return await handler(request)

    return deduplicate_pubchem_tool_calls


def prepare_agent_runtime(
    settings: Settings,
    adapter: PubChemAdapter,
    *,
    provider: LLMProviderName | None,
    trace_id: str,
) -> PreparedAgentRuntime:
    resolved_model = build_chat_model(settings, provider=provider)
    recorder = ToolTraceRecorder()
    tools = build_pubchem_tools(adapter, recorder)
    middleware = [
        _build_duplicate_tool_call_guard(),
        ToolCallLimitMiddleware(run_limit=max(1, settings.agent_max_steps)),
    ]
    tracing = build_langchain_tracing_config(
        settings,
        trace_id=trace_id,
        provider=resolved_model.provider,
    )

    agent = create_agent(
        model=resolved_model.instance,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=middleware,
        name="pubchem-agent",
    )
    invoke_config: dict[str, Any] = {
        "recursion_limit": max(8, settings.agent_max_steps * 2 + 2),
        "metadata": tracing.metadata,
    }
    if tracing.callbacks:
        invoke_config["callbacks"] = tracing.callbacks

    return PreparedAgentRuntime(
        agent=agent,
        recorder=recorder,
        invoke_config=invoke_config,
        provider=resolved_model.provider,
        model_name=resolved_model.model_name,
        tracing=tracing,
    )
