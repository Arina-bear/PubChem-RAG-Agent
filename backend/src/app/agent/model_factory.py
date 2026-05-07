from dataclasses import dataclass

from langchain_openai import ChatOpenAI
#from langchain_community.chat_models import ChatOllama
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from app.agent.rate_limiters import get_gemini_rate_limiter
from app.config import Settings
from app.errors.models import AppError, ErrorCode
from app.schemas.agent import LLMProviderName
from langchain_core.runnables import RunnableConfig

@dataclass
class ResolvedChatModel:
    provider: LLMProviderName
    model_name: str
    instance: ChatOpenAI


def resolve_provider_model_name(settings: Settings, provider: LLMProviderName | None = None) -> tuple[LLMProviderName, str]:
    """Определяет итогового провайдера и имя модели для инициализации LLM.
    Функция реализует логику приоритетов: если провайдер передан явно, используется он; 
    в противном случае берется провайдер по умолчанию из настроек. На основе выбранного 
    провайдера извлекается соответствующее имя модели или базовый URL.
    Args:
        settings (Settings): Объект конфигурации приложения, содержащий ключи и имена моделей.
        provider (LLMProviderName | None, optional): Желаемый провайдер. Если None, 
            используется `settings.llm_default_provider`.
    Returns:
        tuple[LLMProviderName, str]: Кортеж, состоящий из:
            1. Итогового имени провайдера (например, "openai", "ollama").
            2. Технического идентификатора модели или URL (например, "gpt-4o" или адрес сервера).

    """
    resolved_provider = provider or settings.llm_default_provider

    if resolved_provider not in {"openai", "modal_glm", "ollama", "gemini"}:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            f"Неизвестный LLM provider: '{resolved_provider}'.",
            http_status=400,
        )
    if resolved_provider == "openai":
        return "openai", settings.openai_model

    if resolved_provider == "ollama":
        return "ollama", settings.ollama_base_url

    if resolved_provider == "gemini":
        return "gemini", settings.gemini_model

    return "modal_glm", settings.modal_glm_model


def build_chat_model(settings: Settings, provider: LLMProviderName | None = None) -> ResolvedChatModel:
    """
    Функция выполняет роль фабрики: она определяет провайдера, проверяет наличие необходимых 
    API-ключей и создает объект ChatModel с предустановленными параметрами (температура, 
    таймауты, лимиты конкурентности). Поддерживает интеграцию с OpenAI, Ollama и кастомными 
    сервисами через интерфейс ChatOpenAI (например, Modal GLM).

    Args:
        settings (Settings): Глобальный объект конфигурации приложения.
        provider (LLMProviderName | None, optional): Принудительный выбор провайдера. 
            Если не указан, используется значение по умолчанию из настроек.

    Returns:
        ResolvedChatModel: Контейнер, содержащий:
            - Имя провайдера.
            - Техническое имя модели.
            - Настроенный инстанс модели (Runnable), готовый к вызову в LangChain.
    """
    print("!!! ШАГ 1: Входим в build_chat_model")
    print(f"!!! ШАГ 2: Провайдер {provider}")
   # print(f"DEBUG: API Key exists: {settings.modal_glm_api_key is not None}")
    resolved_provider, model_name = resolve_provider_model_name(settings, provider)
    model_kwargs = {"parallel_tool_calls": False}

#логика выбора провайдера
    if resolved_provider == "openai":
        if settings.openai_api_key is None:
            raise AppError(
                ErrorCode.LLM_NOT_CONFIGURED,
                "OPENAI_API_KEY не настроен.",
                http_status=500,
            )
        instance = ChatOpenAI(
            model=model_name,
            api_key=settings.openai_api_key.get_secret_value(),
            base_url=settings.openai_base_url,
            timeout=settings.llm_request_timeout_seconds,
            max_retries=settings.max_retries,
            temperature=0,
            model_kwargs=model_kwargs,
            use_responses_api=False,
        )
        return ResolvedChatModel(provider="openai", 
                                 model_name=model_name, 
                                 instance=instance.with_config(RunnableConfig(max_concurrency=1)))
    if resolved_provider == "ollama":
        ollama_url = settings.ollama_base_url or "http://localhost:11434"
        instance = ChatOllama(
            model="gemma3:4b",  # например, "gemma3:4b"
            base_url=ollama_url,
            temperature=0,
            num_predict=1000,
        )

        return ResolvedChatModel(
            provider="ollama",
            model_name="gemma3:4b",
            instance=instance.with_config(RunnableConfig(max_concurrency=1))
        )

    if resolved_provider == "gemini":
        if settings.google_api_key is None:
            raise AppError(
                ErrorCode.LLM_NOT_CONFIGURED,
                "GOOGLE_API_KEY не настроен.",
                http_status=500,
            )
        instance = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=settings.google_api_key.get_secret_value(),
            temperature=0,
            timeout=settings.llm_request_timeout_seconds,
            max_retries=settings.max_retries,
            rate_limiter=get_gemini_rate_limiter(settings),
        )
        return ResolvedChatModel(
            provider="gemini",
            model_name=model_name,
            instance=instance.with_config(RunnableConfig(max_concurrency=1)),
        )

    if resolved_provider == "modal_glm":
        print("!!! ШАГ 3: Создаем ChatOpenAI")
        if settings.modal_glm_api_key is None:
            raise AppError(
                ErrorCode.LLM_NOT_CONFIGURED,
                "MODAL_GLM_API_KEY не настроен.",
                http_status=500,
            )

    extra_body: dict[str, object] | None = None##!!!!!
    if settings.modal_glm_disable_thinking:
        extra_body = {"thinking": {"type": "disabled"}}##!!!!!

    instance = ChatOpenAI(
        model=model_name,
        api_key=settings.modal_glm_api_key.get_secret_value(),
        base_url=settings.modal_glm_base_url,
        timeout=settings.llm_request_timeout_seconds,
        max_retries=settings.max_retries,
        temperature=0,
        model_kwargs=model_kwargs,
        extra_body=extra_body,##!!!!!
        use_responses_api=False,
    )

    return ResolvedChatModel(provider="modal_glm", 
                             model_name=model_name, 
                             instance = instance.with_config(RunnableConfig(max_concurrency=1)))
