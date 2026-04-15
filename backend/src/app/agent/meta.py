from __future__ import annotations

from app.agent.tools import PUBCHEM_TOOL_CATALOG
from app.schemas.agent import (
    AgentExecutionInfo,
    AgentNormalizedPayload,
    AgentResponseEnvelope,
    LLMProviderName,
    ParsedAgentQuery,
)
from app.schemas.common import PresentationHints


_RUSSIAN_MARKERS = (
    "какие инструменты",
    "какие у тебя инструменты",
    "какие у вас инструменты",
    "что ты умеешь",
    "что умеешь",
    "чем ты можешь помочь",
    "какие возможности",
    "покажи инструменты",
    "список инструментов",
)

_ENGLISH_MARKERS = (
    "what tools",
    "which tools",
    "what can you do",
    "your capabilities",
    "available tools",
    "list your tools",
)


def is_capability_question(text: str) -> bool:
    normalized = " ".join(text.casefold().split())
    return any(marker in normalized for marker in (*_RUSSIAN_MARKERS, *_ENGLISH_MARKERS))


def build_capability_response(
    *,
    trace_id: str,
    request_text: str,
    provider: LLMProviderName,
    model_name: str,
) -> AgentResponseEnvelope:
    is_russian = any("а" <= char <= "я" or char == "ё" for char in request_text.casefold())
    lines = [
        "У меня есть такие PubChem-инструменты:" if is_russian else "I have these PubChem tools:",
    ]
    for item in PUBCHEM_TOOL_CATALOG:
        lines.append(f"- `{item['name']}` — {item['summary']}")

    if is_russian:
        lines.extend(
            [
                "",
                "Как я работаю:",
                "1. Сначала выделяю признаки из запроса: название, синоним, SMILES, формулу или диапазон массы.",
                "2. Потом выбираю минимально необходимый инструмент, а не запускаю всё подряд.",
                "3. Если нахожу кандидатов, дозапрашиваю сводку по нужным CID и объясняю, почему результат подходит.",
                "4. Если данных не хватает, сразу задаю один уточняющий вопрос без лишних вызовов PubChem tools.",
            ]
        )
        final_answer = "\n".join(lines)
        intent = "описание возможностей PubChem-агента"
        language = "ru"
    else:
        lines.extend(
            [
                "",
                "How I work:",
                "1. I first extract useful constraints from your request: name, synonym, SMILES, formula, or mass range.",
                "2. Then I choose the minimum necessary tool instead of calling everything at once.",
                "3. If I find good candidates, I fetch summaries for the relevant CIDs and explain why they match.",
                "4. If the request is underspecified, I ask one concise clarification question instead of guessing.",
            ]
        )
        final_answer = "\n".join(lines)
        intent = "describe PubChem agent capabilities"
        language = "en"

    normalized = AgentNormalizedPayload(
        request=AgentExecutionInfo(
            provider=provider,
            model=model_name,
            text=request_text,
        ),
        parsed_query=ParsedAgentQuery(
            intent=intent,
            language=language,
        ),
        final_answer=final_answer,
        explanation=[],
        needs_clarification=False,
        clarification_question=None,
        matches=[],
        compounds=[],
        tool_trace=[],
        referenced_cids=[],
    )

    return AgentResponseEnvelope(
        trace_id=trace_id,
        source="langchain-agent",
        status="success",
        raw=None,
        normalized=normalized,
        presentation_hints=PresentationHints(
            active_tab="answer",
            available_tabs=["answer", "analysis", "json"],
        ),
        warnings=[],
        error=None,
    )
