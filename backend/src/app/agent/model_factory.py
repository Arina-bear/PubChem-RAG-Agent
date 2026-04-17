from dataclasses import dataclass

from langchain_openai import ChatOpenAI

from app.config import Settings
from app.errors.models import AppError, ErrorCode
from app.schemas.agent import LLMProviderName


@dataclass
class ResolvedChatModel:
    provider: LLMProviderName
    model_name: str
    instance: ChatOpenAI


def resolve_provider_model_name(settings: Settings, provider: LLMProviderName | None = None) -> tuple[LLMProviderName, str]:
    """ """
    resolved_provider = provider or settings.llm_default_provider

    if resolved_provider not in {"openai", "modal_glm"}:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            f"Неизвестный LLM provider: '{resolved_provider}'.",
            http_status=400,
        )
    if resolved_provider == "openai":
        return "openai", settings.openai_model
    
    return "modal_glm", settings.modal_glm_model


def build_chat_model(settings: Settings, provider: LLMProviderName | None = None) -> ResolvedChatModel:
    """ """
    resolved_provider, model_name = resolve_provider_model_name(settings, provider)
    model_kwargs = {"parallel_tool_calls": False}

    if resolved_provider == "openai":
        if settings.openai_api_key is None:
            raise AppError(
                ErrorCode.LLM_NOT_CONFIGURED,
                "OPENAI_API_KEY не настроен.",
                http_status=500,
            )
        instance = ChatOpenAI(
            model=model_name,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            timeout=settings.llm_request_timeout_seconds,
            max_retries=settings.max_retries,
            temperature=0,
            model_kwargs=model_kwargs,
            use_responses_api=False,
        )
        return ResolvedChatModel(provider="openai", model_name=model_name, instance=instance)

    if settings.modal_glm_api_key is None:
        raise AppError(
            ErrorCode.LLM_NOT_CONFIGURED,
            "MODAL_GLM_API_KEY не настроен.",
            http_status=500,
        )

    extra_body: dict[str, object] | None = None
    if settings.modal_glm_disable_thinking:
        extra_body = {"thinking": {"type": "disabled"}}

    instance = ChatOpenAI(
        model=model_name,
        api_key=settings.modal_glm_api_key,
        base_url=settings.modal_glm_base_url,
        timeout=settings.llm_request_timeout_seconds,
        max_retries=settings.max_retries,
        temperature=0,
        model_kwargs=model_kwargs,
        extra_body=extra_body,
        use_responses_api=False,
    )
    return ResolvedChatModel(provider="modal_glm", model_name=model_name, instance=instance)
