from collections import OrderedDict
from collections.abc import Callable
import asyncio
from typing import Any
import uuid

from langchain_core.messages import AIMessage

from app.adapter.pubchem_adapter import PubChemAdapter
from app.agent.error_mapper import normalize_agent_exception
from app.agent.meta import build_capability_response, is_capability_question
from app.agent.model_factory import resolve_provider_model_name
from app.agent.runtime import PreparedAgentRuntime, prepare_agent_runtime
from app.agent.tracing import record_manual_agent_trace
from app.config import Settings
from app.errors.models import AppError, ErrorCode
from app.schemas.agent import (
    AgentExecutionInfo,
    AgentNormalizedPayload,
    AgentRequest,
    AgentResponseEnvelope,
    AgentToolTraceEntry,
    ParsedAgentQuery,
    ParsedMassRange,
)
from app.schemas.common import CompoundMatchCard, CompoundOverview, PresentationHints, WarningMessage


class AgentService:
    def __init__(
        self,
        settings: Settings,
        adapter: PubChemAdapter,
        *,
        runtime_factory: Callable[..., PreparedAgentRuntime] = prepare_agent_runtime,
        manual_trace_recorder: Callable[..., None] = record_manual_agent_trace,
    ) -> None:
        self.settings = settings
        self.adapter = adapter
        self.runtime_factory = runtime_factory
        self.manual_trace_recorder = manual_trace_recorder

    async def execute(self, request: AgentRequest, *, trace_id: str | None = None) -> AgentResponseEnvelope:
        resolved_trace_id = trace_id or uuid.uuid4().hex
        if is_capability_question(request.text):
            provider_name, model_name = resolve_provider_model_name(self.settings, request.provider)
            response = build_capability_response(
                trace_id=resolved_trace_id,
                request_text=request.text,
                provider=provider_name,
                model_name=model_name,
            )
            self.manual_trace_recorder(
                self.settings,
                trace_id=resolved_trace_id,
                name="pubchem-agent-capabilities",
                provider=provider_name,
                model_name=model_name,
                input_payload={
                    "text": request.text,
                    "provider": provider_name,
                },
                output_payload=response.model_dump(mode="json"),
            )
            return response
        runtime = self.runtime_factory(
            self.settings,
            self.adapter,
            provider=request.provider,
            trace_id=resolved_trace_id,
        )
        try:
            result = await asyncio.wait_for(
                runtime.agent.ainvoke(
                    {"messages": [{"role": "user", "content": request.text}]},
                    config=runtime.invoke_config,
                ),
                timeout=max(
                    self.settings.agent_run_timeout_seconds,
                    self.settings.llm_request_timeout_seconds,
                    30.0,
                ),
            )
        except Exception as exc:
            raise normalize_agent_exception(exc) from exc
        finally:
            runtime.tracing.flush()

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
    matches, compounds = _collect_compounds(tool_trace)
    structured = result.get("structured_response")

    if structured is not None:
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
        raw_payload = None
        if request.include_raw:
            raw_payload = {
                "structured_response": structured.model_dump(mode="json"),
                "message_count": len(result.get("messages", [])),
            }
    else:
        final_answer = _fallback_answer(result)
        if not final_answer.strip():
            final_answer = _fallback_compound_answer(request.text, matches, compounds)
        parsed_query = _infer_parsed_query(request.text, tool_trace)
        needs_clarification, clarification_question = _infer_clarification(final_answer, matches, compounds)
        referenced_cids = _collect_referenced_cids(matches, compounds)
        normalized = AgentNormalizedPayload(
            request=AgentExecutionInfo(
                provider=runtime.provider,
                model=runtime.model_name,
                text=request.text,
            ),
            parsed_query=parsed_query,
            final_answer=final_answer,
            explanation=_infer_explanation(
                request.text,
                parsed_query=parsed_query,
                matches=matches,
                compounds=compounds,
                tool_trace=tool_trace,
                needs_clarification=needs_clarification,
            ),
            needs_clarification=needs_clarification,
            clarification_question=clarification_question,
            matches=matches,
            compounds=compounds,
            tool_trace=tool_trace,
            referenced_cids=referenced_cids,
        )
        raw_payload = None
        if request.include_raw:
            raw_payload = {
                "structured_response": None,
                "message_count": len(result.get("messages", [])),
                "final_answer_source": "messages",
            }

    warnings = _build_warnings(normalized)

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
            content = message.content
            if isinstance(content, str) and content.strip():
                return content.strip()
    return "Агент завершил работу, но не сформировал отдельный текстовый ответ."


def _contains_cyrillic(text: str) -> bool:
    lowered = text.casefold()
    return any("а" <= char <= "я" or char == "ё" for char in lowered)


def _fallback_compound_answer(
    request_text: str,
    matches: list[CompoundMatchCard],
    compounds: list[CompoundOverview],
) -> str:
    primary_compound = compounds[0] if compounds else None
    primary_match = matches[0] if matches else None
    is_russian = _contains_cyrillic(request_text)

    if primary_compound is not None:
        title = primary_compound.title or f"CID {primary_compound.cid}"
        formula = primary_compound.molecular_formula or "—"
        weight = primary_compound.molecular_weight
        if is_russian:
            weight_block = f", молекулярная масса {weight:.4f} г/моль" if weight is not None else ""
            return (
                f"Наиболее подходящее вещество в PubChem — {title} (CID {primary_compound.cid}). "
                f"Формула: {formula}{weight_block}."
            )
        weight_block = f", molecular weight {weight:.4f} g/mol" if weight is not None else ""
        return f"The best PubChem match is {title} (CID {primary_compound.cid}). Formula: {formula}{weight_block}."

    if primary_match is not None:
        title = primary_match.title or f"CID {primary_match.cid}"
        formula = primary_match.molecular_formula or "—"
        if is_russian:
            return f"Наиболее подходящий кандидат в PubChem — {title} (CID {primary_match.cid}). Формула: {formula}."
        return f"The best PubChem candidate is {title} (CID {primary_match.cid}). Formula: {formula}."

    if is_russian:
        return "Мне не удалось уверенно подобрать вещество по текущему запросу."
    return "I could not confidently identify a matching compound for the current request."


def _infer_parsed_query(
    request_text: str,
    tool_trace: list[AgentToolTraceEntry],
) -> ParsedAgentQuery:
    language = "ru" if _contains_cyrillic(request_text) else "en"
    parsed = ParsedAgentQuery(
        intent="find compound from natural-language description",
        language=language,
    )

    for event in tool_trace:
        args = event.arguments
        if parsed.requested_limit is None and isinstance(args.get("limit"), int):
            parsed.requested_limit = args["limit"]

        if event.tool_name == "search_compound_by_name":
            parsed.intent = "lookup compound by name"
            parsed.compound_name = args.get("name")
        elif event.tool_name == "search_compound_by_smiles":
            parsed.intent = "lookup compound by SMILES"
            parsed.smiles = args.get("smiles")
        elif event.tool_name == "search_compound_by_formula":
            parsed.intent = "lookup compound by molecular formula"
            parsed.formula = args.get("formula")
        elif event.tool_name == "search_compound_by_inchikey":
            parsed.intent = "lookup compound by InChIKey"
        elif event.tool_name == "search_by_synonym":
            parsed.intent = "lookup compound by synonym"
            parsed.synonym_hint = args.get("synonym")
        elif event.tool_name == "search_compound_by_mass_range":
            parsed.intent = "filter compounds by mass range"
            min_mass = args.get("min_mass")
            max_mass = args.get("max_mass")
            if isinstance(min_mass, (int, float)) and isinstance(max_mass, (int, float)):
                parsed.mass_range = ParsedMassRange(
                    min_mass=float(min_mass),
                    max_mass=float(max_mass),
                    mass_type=args.get("mass_type", "molecular_weight"),
                )
        elif event.tool_name == "name_to_smiles":
            parsed.intent = "resolve compound name to SMILES"
            if parsed.compound_name is None:
                parsed.compound_name = args.get("name")

    return parsed


def _infer_clarification(
    final_answer: str,
    matches: list[CompoundMatchCard],
    compounds: list[CompoundOverview],
) -> tuple[bool, str | None]:
    lowered = final_answer.casefold()
    clarification_markers = (
        "уточ",
        "укажите",
        "какой именно",
        "please clarify",
        "could you clarify",
        "can you clarify",
        "please specify",
        "which one do you mean",
    )
    needs_clarification = not matches and not compounds and (
        final_answer.strip().endswith("?") or any(marker in lowered for marker in clarification_markers)
    )
    return needs_clarification, final_answer if needs_clarification else None


def _collect_referenced_cids(
    matches: list[CompoundMatchCard],
    compounds: list[CompoundOverview],
) -> list[int]:
    seen: OrderedDict[int, None] = OrderedDict()
    for compound in compounds:
        seen.setdefault(compound.cid, None)
    for match in matches:
        seen.setdefault(match.cid, None)
    return list(seen.keys())


def _infer_explanation(
    request_text: str,
    *,
    parsed_query: ParsedAgentQuery,
    matches: list[CompoundMatchCard],
    compounds: list[CompoundOverview],
    tool_trace: list[AgentToolTraceEntry],
    needs_clarification: bool,
) -> list[str]:
    if needs_clarification:
        return []

    is_russian = _contains_cyrillic(request_text)
    primary = compounds[0] if compounds else None
    explanation: list[str] = []

    if parsed_query.compound_name:
        if is_russian:
            explanation.append(f"Запрос содержал явное название вещества: {parsed_query.compound_name}.")
        else:
            explanation.append(f"The request contained an explicit compound name: {parsed_query.compound_name}.")

    if parsed_query.synonym_hint:
        if is_russian:
            explanation.append(f"Поиск использовал синоним или альтернативное имя: {parsed_query.synonym_hint}.")
        else:
            explanation.append(f"The lookup used a synonym or alternate name: {parsed_query.synonym_hint}.")

    if parsed_query.smiles:
        if is_russian:
            explanation.append("Поиск опирался на точное структурное совпадение по SMILES.")
        else:
            explanation.append("The lookup relied on an exact structural match by SMILES.")

    if parsed_query.formula:
        if is_russian:
            explanation.append(f"Кандидаты фильтровались по молекулярной формуле {parsed_query.formula}.")
        else:
            explanation.append(f"Candidates were filtered by molecular formula {parsed_query.formula}.")

    if parsed_query.mass_range and primary and primary.molecular_weight is not None:
        if is_russian:
            explanation.append(
                f"Молекулярная масса {primary.molecular_weight:.4f} г/моль попадает в запрошенный диапазон "
                f"{parsed_query.mass_range.min_mass:.4f}-{parsed_query.mass_range.max_mass:.4f}."
            )
        else:
            explanation.append(
                f"The molecular weight {primary.molecular_weight:.4f} g/mol falls within the requested range "
                f"{parsed_query.mass_range.min_mass:.4f}-{parsed_query.mass_range.max_mass:.4f}."
            )

    if primary is not None:
        title = primary.title or f"CID {primary.cid}"
        formula = primary.molecular_formula or "—"
        if is_russian:
            explanation.append(f"Итоговый кандидат — {title} (CID {primary.cid}) с формулой {formula}.")
        else:
            explanation.append(f"The selected candidate is {title} (CID {primary.cid}) with formula {formula}.")
    elif matches:
        title = matches[0].title or f"CID {matches[0].cid}"
        if is_russian:
            explanation.append(f"PubChem вернул кандидат {title} (CID {matches[0].cid}) как лучший доступный матч.")
        else:
            explanation.append(f"PubChem returned {title} (CID {matches[0].cid}) as the best available match.")

    if any(event.tool_name == "get_compound_summary" for event in tool_trace):
        if is_russian:
            explanation.append("Для финального ответа были дозапрошены свойства выбранного CID.")
        else:
            explanation.append("The final answer is grounded in a PubChem summary fetched for the selected CID.")

    deduped = list(OrderedDict((item, None) for item in explanation).keys())
    return deduped[:4]


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
