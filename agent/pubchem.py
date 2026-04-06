from typing import Any
import httpx
import logging
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

from backend.src.app.config import Settings
from backend.src.app.errors.models import AppError, ErrorCode
from backend.src.app.services.rate_limit import SlidingWindowRateLimiter

logger = logging.getLogger(__name__)

class PubChemTransport:
    def __init__(self, settings: Settings, rate_limiter: SlidingWindowRateLimiter) -> None:
        self.settings = settings
        self.rate_limiter = rate_limiter
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.request_timeout_seconds),
            headers={"Accept": "application/json", "User-Agent": "pubchem-compound-explorer/0.1.0"},
        )

    ##
    async def close(self) -> None:
        await self._client.aclose()

    ##
    async def request_json(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        base_url: str | None = None,
    ) -> dict[str, Any]:
        
        response = await self._request(path, params=params, method=method, base_url=base_url)

        try:
            return response.json()
        
        except ValueError as exc:
           raise AppError(
                ErrorCode.UPSTREAM_UNAVAILABLE,
                "PubChem вернул ответ не в формате JSON.",
                http_status=502,
                retriable=True,
            ) from exc

# получение бинарных данных
    async def request_bytes(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        base_url: str | None = None,
        accept: str | None = None,
    ) -> bytes:
        
        response = await self._request(path, params=params, method=method, base_url=base_url, accept=accept)

        return response.content
##
    async def _request(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        base_url: str | None = None,
        accept: str | None = None,
    ) -> httpx.Response:
        
        logger.info(f"PubChem API request: {method} {path}")

        url = f"{base_url or self.settings.pubchem_rest_base_url}{path}"

        headers = {"Accept": accept} if accept else None

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.settings.max_retries),
                wait=wait_exponential(multiplier=0.25, min=0.25, max=2),
                retry=retry_if_exception(_should_retry),
                reraise=True,
            ):
                with attempt:
                    await self.rate_limiter.acquire()
                    response = await self._client.request(method, url, params=params, headers=headers)

                    if response.status_code == 429:
                        raise AppError(
                            ErrorCode.RATE_LIMITED,
                            "Достигнут лимит PubChem. Попробуйте ещё раз чуть позже.",
                            http_status=429,
                            retriable=True,
                        )
                    
                    if response.status_code in {503, 504}:
                        raise AppError(
                            ErrorCode.UPSTREAM_UNAVAILABLE if response.status_code == 503 else ErrorCode.UPSTREAM_TIMEOUT,
                            "PubChem временно недоступен." if response.status_code == 503 else "PubChem не успел ответить вовремя.",
                            http_status=response.status_code,
                            retriable=True,
                        )
                    
                    if response.status_code == 404:
                        raise AppError(
                            ErrorCode.NO_MATCH,
                            "Подходящая запись PubChem не найдена.",
                            http_status=404,
                        )
                    if response.status_code == 400:
                        raise AppError(
                            ErrorCode.VALIDATION_ERROR,
                            "PubChem отклонил параметры запроса.",
                            http_status=400,
                        )
                    if response.status_code >= 500:
                        raise AppError(
                            ErrorCode.UPSTREAM_UNAVAILABLE,
                            "PubChem вернул серверную ошибку.",
                            http_status=502,
                            retriable=True,
                        )
                    response.raise_for_status()
                    return response
                
        except httpx.TimeoutException as exc:
            raise AppError(
                ErrorCode.UPSTREAM_TIMEOUT,
                "Превышено время ожидания ответа от PubChem.",
                http_status=504,
                retriable=True,
            ) from exc
        
        except httpx.NetworkError as exc:
            raise AppError(
                ErrorCode.UPSTREAM_UNAVAILABLE,
                "Сетевая ошибка при обращении к PubChem.",
                http_status=503,
                retriable=True,
            ) from exc

##
def _should_retry(error: BaseException) -> bool:

    if isinstance(error, (httpx.TimeoutException, httpx.NetworkError)):
        return True
    
    if isinstance(error, AppError):
        return error.retriable
    
    return False