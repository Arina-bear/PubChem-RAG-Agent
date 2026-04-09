from __future__ import annotations

from typing import cast
import json
import uuid

import chainlit as cl

from app.container import AppContainer, build_container
from app.presenters.compound_card import (
    build_candidates_markdown,
    build_compound_card_props,
    build_pending_compound_card_props,
    build_structure_image_url,
    build_tool_trace_markdown,
    extract_primary_synonyms,
    select_primary_compound,
)
from app.schemas.agent import AgentRequest, AgentResponseEnvelope

WELCOME_MESSAGE = """
PubChem Agent готов к поиску по естественному языку.

Примеры запросов:
- антибиотик с бензольным кольцом, молекулярная масса около 350
- соединение похоже на aspirin
- найди молекулу по описанию и верни свойства
""".strip()


def _get_or_create_container() -> AppContainer:
    container = cl.user_session.get("container")
    if container is None:
        container = build_container()
        cl.user_session.set("container", container)
    return cast(AppContainer, container)


def _get_session_id() -> str:
    session_id = cl.user_session.get("pubchem_session_id")
    if session_id is None:
        session_id = uuid.uuid4().hex
        cl.user_session.set("pubchem_session_id", session_id)
    return cast(str, session_id)


def _build_details_markdown(response: AgentResponseEnvelope) -> str:
    normalized = response.normalized
    if normalized is None:
        return "Подробные сведения недоступны."

    primary = select_primary_compound(response)
    if primary is None:
        return build_tool_trace_markdown(response)

    lines = ["### Подробности"]
    if primary.iupac_name:
        lines.append(f"- IUPAC: {primary.iupac_name}")
    if primary.canonical_smiles:
        lines.append(f"- Canonical SMILES: `{primary.canonical_smiles}`")
    if primary.exact_mass is not None:
        lines.append(f"- Exact mass: {primary.exact_mass:.4f}")
    if primary.xlogp is not None:
        lines.append(f"- XLogP: {primary.xlogp}")
    if primary.tpsa is not None:
        lines.append(f"- TPSA: {primary.tpsa}")
    if primary.complexity is not None:
        lines.append(f"- Complexity: {primary.complexity}")
    if primary.hbond_donor_count is not None or primary.hbond_acceptor_count is not None:
        donor = primary.hbond_donor_count if primary.hbond_donor_count is not None else "—"
        acceptor = primary.hbond_acceptor_count if primary.hbond_acceptor_count is not None else "—"
        lines.append(f"- H-bond donors / acceptors: {donor} / {acceptor}")
    if primary.description:
        lines.append("")
        lines.append(primary.description)
    return "\n".join(lines)


@cl.on_chat_start
async def on_chat_start() -> None:
    container = _get_or_create_container()
    _get_session_id()
    cl.user_session.set("llm_provider", container.settings.llm_default_provider)
    await cl.Message(content=WELCOME_MESSAGE, author="PubChem Agent").send()


@cl.on_chat_end
async def on_chat_end() -> None:
    container = cl.user_session.get("container")
    if container is not None:
        await cast(AppContainer, container).close()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    container = _get_or_create_container()
    session_id = _get_session_id()
    provider = cast(str, cl.user_session.get("llm_provider") or container.settings.llm_default_provider)
    trace_id = uuid.uuid4().hex

    pending_card = cl.CustomElement(
        name="CompoundCard",
        props=build_pending_compound_card_props(message.content),
        display="inline",
    )
    await cl.Message(
        content="Понял запрос. Ищу кандидатов и собираю свойства из PubChem...",
        elements=[pending_card],
        author="PubChem Agent",
    ).send()

    callback = cl.LangchainCallbackHandler()
    response = await container.agent_stream_service.execute(
        AgentRequest(
            text=message.content,
            provider=provider,
            include_raw=True,
        ),
        trace_id=trace_id,
        extra_callbacks=[callback],
        metadata_overrides={
            "surface": "chainlit",
            "chainlit_session_id": session_id,
            "agent_provider": provider,
        },
    )

    normalized = response.normalized
    if normalized is None:
        pending_card.props = {
            "loading": False,
            "status": "Не удалось получить нормализованный ответ агента.",
        }
        await pending_card.update()
        await cl.Message(content="Не удалось получить итоговый ответ от агента.", author="PubChem Agent").send()
        return

    parsed_query_payload = normalized.parsed_query.model_dump(mode="json", exclude_none=True)
    async with cl.Step(name="Интерпретация запроса", type="tool", show_input="json") as step:
        step.input = {"query": message.content}
        step.output = json.dumps(parsed_query_payload, ensure_ascii=False, indent=2)

    primary = select_primary_compound(response)
    side_elements: list[cl.Element] = []
    if primary is not None:
        synonyms = extract_primary_synonyms(response, primary.cid)
        pending_card.props = build_compound_card_props(
            primary,
            explanation=normalized.explanation,
            synonyms=synonyms,
        )
        await pending_card.update()
        side_elements.append(
            cl.Image(
                name=f"CID {primary.cid} structure",
                url=build_structure_image_url(primary.cid),
                display="side",
            )
        )
        side_elements.append(
            cl.Text(
                name="Подробности вещества",
                content=_build_details_markdown(response),
                display="side",
            )
        )
    else:
        pending_card.props = {
            "loading": False,
            "status": normalized.clarification_question or "Подходящее вещество не выбрано.",
        }
        await pending_card.update()

    if normalized.tool_trace:
        side_elements.append(
            cl.Text(
                name="Ход поиска",
                content=build_tool_trace_markdown(response),
                display="side",
            )
        )

    if len(normalized.matches) > 1:
        side_elements.append(
            cl.Text(
                name="Другие кандидаты",
                content=build_candidates_markdown(normalized.matches[1:]),
                display="side",
            )
        )

    explanation_block = ""
    if normalized.explanation:
        explanation_block = "\n\nПочему результат подходит:\n" + "\n".join(
            f"- {item}" for item in normalized.explanation[:4]
        )

    clarification_block = ""
    if normalized.needs_clarification and normalized.clarification_question:
        clarification_block = f"\n\nУточнение:\n{normalized.clarification_question}"

    async with cl.Step(name="Отбор результата", type="tool") as step:
        step.output = "\n".join(normalized.explanation[:4]) or (
            normalized.clarification_question or "Агент завершил поиск без дополнительного пояснения."
        )

    await cl.Message(
        content=f"{normalized.final_answer}{explanation_block}{clarification_block}",
        elements=side_elements,
        author="PubChem Agent",
    ).send()
