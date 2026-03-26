from dataclasses import dataclass

from app.adapter.pubchem_adapter import PubChemAdapter
from app.config import Settings, get_settings
from app.services.cache import TTLCache
from app.services.interpret_service import InterpretService
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

    async def close(self) -> None:
        await self.transport.close()


def build_container(settings: Settings | None = None) -> AppContainer:
    resolved_settings = settings or get_settings()
    cache = TTLCache()
    rate_limiter = SlidingWindowRateLimiter(limit=resolved_settings.query_rate_limit_per_second)
    transport = PubChemTransport(resolved_settings, rate_limiter)
    adapter = PubChemAdapter(resolved_settings, transport, cache)

    return AppContainer(
        settings=resolved_settings,
        cache=cache,
        rate_limiter=rate_limiter,
        transport=transport,
        adapter=adapter,
        query_service=QueryService(resolved_settings, adapter),
        interpret_service=InterpretService(),
    )
