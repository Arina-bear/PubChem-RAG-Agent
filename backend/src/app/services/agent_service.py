from collections import OrderedDict
from collections.abc import Callable
from typing import Any
import uuid

from langchain_core.messages import AIMessage
from langgraph.errors import GraphRecursionError

from app.adapter.pubchem_adapter import PubChemAdapter
from app.agent.runtime import PreparedAgentRuntime, prepare_agent_runtime
from app.config import Settings
from app.errors.models import AppError, ErrorCode
from app.schemas.agent import (
    AgentExecutionInfo,
    AgentNormalizedPayload,
    AgentRequest,
    AgentResponseEnvelope,
    AgentToolTraceEntry,
)
from app.schemas.common import CompoundMatchCard, CompoundOverview, PresentationHints, WarningMessage


class AgentService:
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

    async def execute(self, request: AgentRequest, *, trace_id: str | None = None) -> AgentResponseEnvelope:
        resolved_trace_id = trace_id or str(uuid.uuid4())
        runtime = self.runtime_factory(
            self.settings,
            self.adapter,
            provider=request.provider,
            trace_id=resolved_trace_id,
        )
        try:
            result = await runtime.agent.ainvoke(
                {"messages": [{"role": "user", "content": request.text}]},
                config=runtime.invoke_config,
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


def build_agent_response_envelope(
    *,
    trace_id: str,
    request: AgentRequest,
    runtime: PreparedAgentRuntime,
    result: dict[str, Any],
    tool_trace: list[AgentToolTraceEntry],
) -> AgentResponseEnvelope:
    structured = result["structured_response"]
    matches, compounds = _collect_compounds(tool_trace)

    normalized = AgentNormalizedPayload(
        request=AgentExecutionInfo(
            provider=runtime.provider,
            model=runtime.model_name,
            text=request.text,
        ),
        parsed_query=structured.parsed_query,
        final_answer=structured.final_answer or _fallback_answer(result),
        explanation=structured.explanation,
        needs_clarification=structured.needs_clarification,
        clarification_question=structured.clarification_question,
        matches=matches,
        compounds=compounds,
        tool_trace=tool_trace,
        referenced_cids=structured.referenced_cids,
    )

    warnings = _build_warnings(normalized)
    raw_payload = None
    if request.include_raw:
        raw_payload = {
            "structured_response": structured.model_dump(mode="json"),
            "message_count": len(result.get("messages", [])),
        }

    return AgentResponseEnvelope(
        trace_id=trace_id,
        source="langchain-agent",
        status="success",
        raw=raw_payload,
        normalized=normalized,
        presentation_hints=PresentationHints(
            active_tab="answer",
            available_tabs=["answer", "compounds", "analysis", "tools", "json"],
        ),
        warnings=warnings,
        error=None,
    )


def _fallback_answer(result: dict[str, Any]) -> str:
    messages = result.get("messages", [])
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            content = message.text() if hasattr(message, "text") else message.content
            if isinstance(content, str) and content.strip():
                return content.strip()
    return "Агент завершил работу, но не сформировал отдельный текстовый ответ."


def _collect_compounds(tool_trace: list[AgentToolTraceEntry]) -> tuple[list[CompoundMatchCard], list[CompoundOverview]]:
    match_map: "OrderedDict[int, CompoundMatchCard]" = OrderedDict()
    compound_map: "OrderedDict[int, CompoundOverview]" = OrderedDict()

    for event in tool_trace:
        if event.result is None or not event.result.get("ok", False):
            continue

        for match in event.result.get("matches", []) or []:
            try:
                validated = CompoundMatchCard.model_validate(match)
            except Exception:
                continue
            match_map.setdefault(validated.cid, validated)

        compound = event.result.get("compound")
        if compound:
            try:
                validated = CompoundOverview.model_validate(compound)
            except Exception:
                validated = None
            if validated is not None:
                compound_map.setdefault(validated.cid, validated)

        name_to_smiles_cid = event.result.get("cid")
        if name_to_smiles_cid and event.tool_name == "name_to_smiles":
            try:
                match_map.setdefault(
                    int(name_to_smiles_cid),
                    CompoundMatchCard(
                        cid=int(name_to_smiles_cid),
                        title=event.result.get("resolved_title"),
                        molecular_formula=event.result.get("molecular_formula"),
                        molecular_weight=event.result.get("molecular_weight"),
                    ),
                )
            except Exception:
                continue

    return list(match_map.values()), list(compound_map.values())


def _build_warnings(normalized: AgentNormalizedPayload) -> list[WarningMessage]:
    warnings: list[WarningMessage] = []
    if normalized.needs_clarification:
        warnings.append(
            WarningMessage(
                code="NEEDS_CLARIFICATION",
                message="Запрос требует уточнения перед надёжным поиском в PubChem.",
            )
        )
    if not normalized.tool_trace:
        warnings.append(
            WarningMessage(
                code="NO_TOOL_USAGE",
                message="Агент не вызвал PubChem tools. Ответ мог остановиться на этапе уточнения.",
            )
        )
    return warnings
