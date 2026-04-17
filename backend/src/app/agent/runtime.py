"""
MODULE: AI Agent Runtime Orchestrator
-------------------------------------
PURPOSE:
Responsible for assembling and configuring the AI agent lifecycle. Acts as an MCP client, connecting the language model (LLM) to the tool server.

MAIN FUNCTIONS:
- Initialization and connection to remote MCP tool servers.
- Configuring "circuit breakers" (Middleware): loop protection and step limits.
- Configuring the monitoring system (Tracing) for debugging reasoning chains.
- Assembling the final agent object, ready to execute user tasks.

This file separates the infrastructure startup logic from the implementation of the tools themselves.
"""
import json, logging
from dataclasses import dataclass
from typing import Any
from langchain_mcp_adapters.client import MultiServerMCPClient

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware, wrap_tool_call
from langchain_core.messages import ToolMessage


from app.agent.model_factory import build_chat_model
from app.agent.prompts import SYSTEM_PROMPT
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
    async def stop(self):
        try:
            await self.mcp_client.disconnect()
            if self.tracing.client:
                self.tracing.flush()
            logging.info("MCP runtime successfully shut down.")

        except Exception as e:
            logging.error(f"Error during MCP runtime shutdown: {e}")
        


def _build_duplicate_tool_call_guard() -> Any:

    """The mechanism intercepts tool calls and checks whether an identical call (name + arguments) has been executed previously.
        If a duplicate is detected, tool execution is blocked,
        and the agent is instructed to use the results of the previous call.
        Returns:
        Callable: Middleware-функция для LangChain агента.
        """
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
                name = request.tool_call["name"],
                tool_call_id = request.tool_call["id"],
                status = "error",
            )

        seen_signatures.add(signature)
        return await handler(request)

    return deduplicate_pubchem_tool_calls


async def prepare_agent_runtime(
    settings: Settings,
    trace_id: str,
) -> PreparedAgentRuntime:
    """
    Initializes and assembles the AI ​​agent's runtime environment, configuring connections to MCP servers, language model (LLM) parameters, 
    loop protection, and tracing configuration. This is the central hub that transforms disparate components into a ready-to-run agent instance.
    Args: 
        settings (Settings): A global application settings object containing agent step limits, API connection parameters, provider keys, and paths to MCP scripts.

        trace_id (str): A unique trace session identifier used for monitoring agent operation and debugging call chains in LangSmith or other logging systems.
    
    Return:

    PreparedAgentRuntime: A data class (container) containing:

        agent: A constructed agent object with attached MCP tools.
        recorder: A tool for recording execution logs.
        invoke_config: Invocation settings (recursion limits, callback functions).
        provider/model_name: Metadata about the neural network used.
        tracing: Configuration for the monitoring system. 
    """
    mcp_client = MultiServerMCPClient({
        "pubchem": {
            "command": "python",
            "args": ["mcp_server.py"],
            "transport": "stdio",
        }
    })
    try:
     await mcp_client.connect()

    except Exception as e:
        import traceback
        traceback.print_exc(f"MCP Server failed to start: {e}")

    mcp_tools = await mcp_client.get_tools()

    resolved_model = build_chat_model(settings)
    recorder = ToolTraceRecorder()

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
        tools=mcp_tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=middleware,
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
        mcp_client=mcp_client
    )
