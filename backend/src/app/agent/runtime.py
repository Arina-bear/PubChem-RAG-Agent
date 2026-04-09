from dataclasses import dataclass
from typing import Any

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from app.adapter.pubchem_adapter import PubChemAdapter
from app.agent.model_factory import build_chat_model
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import build_pubchem_tools
from app.agent.tracing import LangChainTracingConfig, ToolTraceRecorder, build_langchain_tracing_config
from app.config import Settings
from app.schemas.agent import AgentFinalStructuredResponse, LLMProviderName


@dataclass
class PreparedAgentRuntime:
    agent: Any
    recorder: ToolTraceRecorder
    invoke_config: dict[str, Any]
    provider: LLMProviderName
    model_name: str
    tracing: LangChainTracingConfig


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
    tracing = build_langchain_tracing_config(
        settings,
        trace_id=trace_id,
        provider=resolved_model.provider,
    )

    agent = create_agent(
        model=resolved_model.instance,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        response_format=ToolStrategy(AgentFinalStructuredResponse),
        name="pubchem-agent",
    )
    invoke_config: dict[str, Any] = {
        "recursion_limit": max(12, settings.agent_max_steps * 3),
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
