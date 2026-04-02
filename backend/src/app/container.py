from dataclasses import dataclass

from app.adapter.pubchem_adapter import PubChemAdapter
from app.config import Settings, get_settings
from app.llm.providers import OpenAICompatibleChatProvider
from app.services.cache import TTLCache
from app.services.agent_service import AgentService
from app.services.interpret_service import InterpretService
from app.services.pubchem_tools import PubChemToolbox
from app.services.query_parser import QueryParserService
from app.services.query_service import QueryService
from app.services.rate_limit import SlidingWindowRateLimiter
from app.transport.pubchem import PubChemTransport


@dataclass
class AppContainer:
    settings: Settings
    cache: TTLCache
    rate_limiter: SlidingWindowRateLimiter
    transport: PubChemTransport
    adapter: PubChemAdapter
    query_service: QueryService
    interpret_service: InterpretService
    agent_service: AgentService

    async def close(self) -> None:
        await self.transport.close()
        await self.agent_service.close()


def build_container(settings: Settings | None = None) -> AppContainer:
    resolved_settings = settings or get_settings()
    cache = TTLCache()
    rate_limiter = SlidingWindowRateLimiter(limit=resolved_settings.query_rate_limit_per_second)
    llm_rate_limiter = SlidingWindowRateLimiter(limit=resolved_settings.llm_rate_limit_per_second)
    transport = PubChemTransport(resolved_settings, rate_limiter)
    adapter = PubChemAdapter(resolved_settings, transport, cache)
    tools = PubChemToolbox(adapter)
    query_parser = QueryParserService()

    openai_provider = OpenAICompatibleChatProvider(
        provider_name="openai",
        base_url=resolved_settings.openai_base_url,
        api_key=resolved_settings.openai_api_key.get_secret_value() if resolved_settings.openai_api_key else None,
        default_model=resolved_settings.openai_model,
        timeout_seconds=resolved_settings.llm_request_timeout_seconds,
        max_retries=resolved_settings.max_retries,
    )
    modal_provider = OpenAICompatibleChatProvider(
        provider_name="modal_glm",
        base_url=resolved_settings.modal_glm_base_url,
        api_key=resolved_settings.modal_glm_api_key.get_secret_value() if resolved_settings.modal_glm_api_key else None,
        default_model=resolved_settings.modal_glm_model,
        timeout_seconds=resolved_settings.llm_request_timeout_seconds,
        max_retries=resolved_settings.max_retries,
        request_defaults={"thinking": {"type": "disabled"}} if resolved_settings.modal_glm_disable_thinking else None,
    )
    agent_service = AgentService(
        resolved_settings,
        tools,
        providers={
            "openai": openai_provider,
            "modal_glm": modal_provider,
        },
        query_parser=query_parser,
        llm_rate_limiter=llm_rate_limiter,
    )

    return AppContainer(
        settings=resolved_settings,
        cache=cache,
        rate_limiter=rate_limiter,
        transport=transport,
        adapter=adapter,
        query_service=QueryService(resolved_settings, adapter),
        interpret_service=InterpretService(),
        agent_service=agent_service,
    )
