import json
import uuid
from typing import Any

from app.config import Settings
from app.errors.models import AppError, ErrorCode
from app.llm.providers import ChatCompletionProvider, LLMCompletion, LLMToolCall
from app.schemas.agent import AgentNormalizedPayload, AgentParsedQuery, AgentRequest, AgentResponseEnvelope, AgentToolCallTrace, LLMProviderName
from app.schemas.common import CompoundOverview, WarningMessage
from app.services.pubchem_tools import PubChemToolbox
from app.services.query_parser import QueryParserService
from app.services.rate_limit import SlidingWindowRateLimiter


SYSTEM_PROMPT = """You are a supervised PubChem agent.

Your job is to answer molecule search requests by using the available PubChem tools instead of guessing.

Rules:
- Read the parsed_query block before choosing tools.
- Use the narrowest tool that fits the user request.
- Never invent PubChem facts or properties.
- If the request is ambiguous, underspecified, or too semantic for a safe lookup, call ask_user_for_clarification.
- Prefer search_compound_by_name when the user explicitly names a compound.
- Prefer search_compound_by_smiles when you already have an exact SMILES string.
- Prefer search_compound_by_formula for exact formulas.
- Prefer search_compound_by_mass_range for approximate mass constraints.
- Use get_compound_summary after candidate search when you need more detail for the final answer.
- Use name_to_smiles when the user gives a name but structure search is likely to be more precise.
- Stop after ask_user_for_clarification. Do not continue calling tools afterwards.
- Do not repeat the same tool call with the same arguments.
- Respond in the same language as the user.
- In the final answer, briefly explain why the selected result matches the request.
"""


class AgentService:
    def __init__(
        self,
        settings: Settings,
        tools: PubChemToolbox,
        providers: dict[LLMProviderName, ChatCompletionProvider],
        query_parser: QueryParserService,
        llm_rate_limiter: SlidingWindowRateLimiter,
    ) -> None:
        self.settings = settings
        self.tools = tools
        self.providers = providers
        self.query_parser = query_parser
        self.llm_rate_limiter = llm_rate_limiter

    async def close(self) -> None:
        for provider in self.providers.values():
            await provider.close()

    async def execute(self, request: AgentRequest) -> AgentResponseEnvelope:
        provider_name = request.provider or self.settings.llm_default_provider
        provider = self.providers.get(provider_name)  # type: ignore[arg-type]
        if provider is None:
            raise AppError(
                ErrorCode.UNSUPPORTED_QUERY,
                f"LLM provider '{provider_name}' не поддерживается.",
                http_status=400,
            )

        parsed_query = self.query_parser.parse(request.text)
        if parsed_query.recommended_search_mode == "clarify":
            clarification_question = self.query_parser.build_clarification_question(parsed_query)
            return self._build_response(
                trace_id=str(uuid.uuid4()),
                request=request,
                parsed_query=parsed_query,
                provider_name=provider.provider_name,  # type: ignore[arg-type]
                model=request.model or provider.default_model,
                final_answer=clarification_question,
                clarification_question=clarification_question,
                tool_traces=[],
                compounds=[],
                raw_steps=[],
            )

        trace_id = str(uuid.uuid4())
        selected_model = request.model or provider.default_model
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": self._parsed_query_message(parsed_query)},
            {"role": "user", "content": request.text},
        ]
        tool_definitions = self.tools.tool_definitions()
        tool_traces: list[AgentToolCallTrace] = []
        raw_steps: list[dict[str, Any]] = []
        collected_compounds: dict[int, CompoundOverview] = {}
        seen_tool_signatures: set[str] = set()
        clarification_question: str | None = None
        final_answer = ""
        consecutive_tool_errors = 0
        completion: LLMCompletion | None = None
        stop_after_tool = False
        max_steps = min(request.max_steps, self.settings.agent_max_steps)

        for _ in range(max_steps):
            await self.llm_rate_limiter.acquire()
            completion = await provider.complete(
                messages=messages,
                tools=tool_definitions,
                model=selected_model,
                max_output_tokens=request.max_output_tokens,
            )
            if request.include_raw:
                raw_steps.append(completion.raw)

            messages.append(completion.message)
            if not completion.tool_calls:
                final_answer = completion.content.strip()
                break

            for tool_call in completion.tool_calls:
                trace, result_payload = await self._execute_tool(tool_call, seen_tool_signatures)
                tool_traces.append(trace)

                if trace.status == "success":
                    consecutive_tool_errors = 0
                    clarification_question = clarification_question or result_payload.get("question")
                    for compound in self._extract_compounds(result_payload):
                        collected_compounds[compound.cid] = compound
                else:
                    consecutive_tool_errors += 1

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": trace.id,
                        "content": json.dumps(result_payload, ensure_ascii=False),
                    }
                )

                if result_payload.get("error", {}).get("code") == "REPEATED_TOOL_CALL":
                    clarification_question = clarification_question or self.query_parser.build_clarification_question(parsed_query)
                    final_answer = clarification_question
                    stop_after_tool = True
                    break

                if tool_call.name == "ask_user_for_clarification" and trace.status == "success":
                    clarification_question = result_payload.get("question") or self.query_parser.build_clarification_question(parsed_query)
                    final_answer = clarification_question
                    stop_after_tool = True
                    break

                if consecutive_tool_errors >= 2:
                    clarification_question = clarification_question or self.query_parser.build_clarification_question(parsed_query)
                    final_answer = clarification_question
                    stop_after_tool = True
                    break

            if stop_after_tool:
                break
        else:
            raise AppError(
                ErrorCode.TOOL_LOOP_ABORTED,
                "LLM agent не смог завершить reasoning loop в допустимое число шагов.",
                http_status=502,
            )

        if not final_answer and clarification_question:
            final_answer = clarification_question

        if not final_answer:
            raise AppError(
                ErrorCode.UPSTREAM_UNAVAILABLE,
                "LLM agent не вернул итоговый ответ.",
                http_status=502,
            )

        return self._build_response(
            trace_id=trace_id,
            request=request,
            parsed_query=parsed_query,
            provider_name=provider.provider_name,  # type: ignore[arg-type]
            model=completion.model if completion is not None else selected_model,
            final_answer=final_answer,
            clarification_question=clarification_question,
            tool_traces=tool_traces,
            compounds=list(collected_compounds.values()),
            raw_steps=raw_steps,
        )

    async def _execute_tool(
        self,
        tool_call: LLMToolCall,
        seen_tool_signatures: set[str],
    ) -> tuple[AgentToolCallTrace, dict[str, Any]]:
        try:
            arguments = tool_call.parsed_arguments()
        except AppError as error:
            return (
                AgentToolCallTrace(
                    id=tool_call.id,
                    name=tool_call.name,
                    arguments={},
                    status="error",
                    result={"code": error.code.value},
                    error_message=error.message,
                ),
                {
                    "ok": False,
                    "error": {
                        "code": error.code.value,
                        "message": error.message,
                    },
                },
            )

        signature = self._tool_signature(tool_call.name, arguments)
        if signature in seen_tool_signatures:
            error_message = "LLM повторно вызвала тот же tool с теми же аргументами."
            result_payload = {
                "ok": False,
                "error": {
                    "code": "REPEATED_TOOL_CALL",
                    "message": error_message,
                },
            }
            return (
                AgentToolCallTrace(
                    id=tool_call.id,
                    name=tool_call.name,
                    arguments=arguments,
                    status="error",
                    result={"code": "REPEATED_TOOL_CALL"},
                    error_message=error_message,
                ),
                result_payload,
            )

        seen_tool_signatures.add(signature)
        result_payload = await self.tools.execute(tool_call.name, arguments)
        status = "success" if not (isinstance(result_payload, dict) and result_payload.get("ok") is False) else "error"
        return (
            AgentToolCallTrace(
                id=tool_call.id,
                name=tool_call.name,
                arguments=arguments,
                status=status,
                result=self._compress_tool_result(result_payload),
                error_message=result_payload.get("error", {}).get("message") if status == "error" and isinstance(result_payload, dict) else None,
            ),
            result_payload,
        )

    def _build_response(
        self,
        *,
        trace_id: str,
        request: AgentRequest,
        parsed_query: AgentParsedQuery,
        provider_name: LLMProviderName,
        model: str,
        final_answer: str,
        clarification_question: str | None,
        tool_traces: list[AgentToolCallTrace],
        compounds: list[CompoundOverview],
        raw_steps: list[dict[str, Any]],
    ) -> AgentResponseEnvelope:
        needs_clarification = clarification_question is not None
        warnings: list[WarningMessage] = []
        if parsed_query.confidence < 0.65:
            warnings.append(
                WarningMessage(
                    code="LOW_PARSE_CONFIDENCE",
                    message="Предварительный парсер нашёл неоднозначности. Agent ответил в щадящем режиме.",
                )
            )
        if not compounds and not needs_clarification:
            warnings.append(
                WarningMessage(
                    code="NO_COMPOUND_IN_TOOL_TRACE",
                    message="LLM агент ответил без извлечённых compound summaries. Проверьте prompt и tool selection.",
                )
            )

        normalized = AgentNormalizedPayload(
            user_text=request.text,
            answer=final_answer,
            provider=provider_name,
            model=model,
            parsed_query=parsed_query,
            needs_clarification=needs_clarification,
            clarification_question=clarification_question,
            compounds=compounds,
            tool_calls=tool_traces,
        )
        return AgentResponseEnvelope(
            trace_id=trace_id,
            status="needs_clarification" if needs_clarification else "success",
            normalized=normalized,
            raw={"steps": raw_steps} if request.include_raw else None,
            warnings=warnings,
        )

    def _parsed_query_message(self, parsed_query: AgentParsedQuery) -> str:
        return (
            "parsed_query:\n"
            f"{json.dumps(parsed_query.model_dump(mode='json'), ensure_ascii=False, indent=2)}\n"
            "Treat this as a first-pass structured parse. Prefer matching tools to these fields instead of free-form guessing."
        )

    def _compress_tool_result(self, tool_result: dict[str, Any]) -> dict[str, Any]:
        if tool_result.get("ok") is False:
            error_payload = tool_result.get("error", {})
            if not isinstance(error_payload, dict):
                return {"ok": False}
            return {
                "ok": False,
                "error": {
                    "code": error_payload.get("code"),
                    "message": error_payload.get("message"),
                },
            }

        summary: dict[str, Any] = {"ok": True}
        if "query" in tool_result:
            summary["query"] = tool_result["query"]
        if "count" in tool_result:
            summary["count"] = tool_result["count"]
        if "cid" in tool_result:
            summary["cid"] = tool_result["cid"]
        if "resolved_title" in tool_result:
            summary["resolved_title"] = tool_result["resolved_title"]
        if "canonical_smiles" in tool_result:
            summary["canonical_smiles"] = tool_result["canonical_smiles"]
        if "question" in tool_result:
            summary["question"] = tool_result["question"]
        if isinstance(tool_result.get("compound"), dict):
            compound = tool_result["compound"]
            summary["compound"] = {
                "cid": compound.get("cid"),
                "title": compound.get("title"),
                "molecular_formula": compound.get("molecular_formula"),
            }
        if isinstance(tool_result.get("matches"), list):
            summary["match_cids"] = [
                item.get("cid")
                for item in tool_result["matches"]
                if isinstance(item, dict) and isinstance(item.get("cid"), int)
            ][:5]
        return summary

    def _tool_signature(self, tool_name: str, arguments: dict[str, Any]) -> str:
        normalized_arguments = json.dumps(arguments, ensure_ascii=False, sort_keys=True)
        return f"{tool_name}:{normalized_arguments}"

    def _extract_compounds(self, tool_result: dict[str, Any]) -> list[CompoundOverview]:
        compounds: list[CompoundOverview] = []
        compound_payload = tool_result.get("compound")
        if isinstance(compound_payload, dict):
            compounds.append(CompoundOverview.model_validate(compound_payload))

        matches_payload = tool_result.get("matches")
        if isinstance(matches_payload, list):
            for item in matches_payload:
                if not isinstance(item, dict):
                    continue
                compounds.append(CompoundOverview.model_validate(item))
        return compounds
