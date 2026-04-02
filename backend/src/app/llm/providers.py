import json
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

from app.errors.models import AppError, ErrorCode


def _normalize_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts).strip()
    return ""


def _should_retry_llm(error: BaseException) -> bool:
    if isinstance(error, (httpx.TimeoutException, httpx.NetworkError)):
        return True
    if isinstance(error, AppError):
        return error.retriable
    return False


def _sanitize_error_details(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None

    error_payload = payload.get("error")
    if not isinstance(error_payload, dict):
        return None

    sanitized: dict[str, Any] = {}
    for key in ("type", "code", "param"):
        value = error_payload.get(key)
        if isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
    return sanitized or None


@dataclass(slots=True)
class LLMToolCall:
    id: str
    name: str
    arguments_json: str

    def as_chat_completion_message(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": self.arguments_json,
            },
        }

    def parsed_arguments(self) -> dict[str, Any]:
        if not self.arguments_json:
            return {}
        try:
            payload = json.loads(self.arguments_json)
        except json.JSONDecodeError as exc:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                f"LLM вернула невалидный JSON для tool arguments: {exc.msg}.",
                http_status=502,
            ) from exc
        if not isinstance(payload, dict):
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                "LLM вернула tool arguments не в формате JSON object.",
                http_status=502,
            )
        return payload


@dataclass(slots=True)
class LLMCompletion:
    message: dict[str, Any]
    content: str
    tool_calls: list[LLMToolCall]
    model: str
    raw: dict[str, Any]


class ChatCompletionProvider(Protocol):
    provider_name: str
    default_model: str

    async def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str | None = None,
        max_output_tokens: int | None = None,
    ) -> LLMCompletion: ...

    async def close(self) -> None: ...


class OpenAICompatibleChatProvider:
    def __init__(
        self,
        *,
        provider_name: str,
        base_url: str,
        api_key: str | None,
        default_model: str,
        timeout_seconds: float,
        max_retries: int,
        request_defaults: dict[str, Any] | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model
        self.max_retries = max_retries
        self.request_defaults = request_defaults or {}
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "pubchem-compound-explorer/0.1.0",
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str | None = None,
        max_output_tokens: int | None = None,
    ) -> LLMCompletion:
        if not self.api_key:
            raise AppError(
                ErrorCode.LLM_NOT_CONFIGURED,
                f"LLM provider '{self.provider_name}' не настроен: отсутствует API key.",
                http_status=500,
            )

        selected_model = model or self.default_model
        if not selected_model:
            raise AppError(
                ErrorCode.LLM_NOT_CONFIGURED,
                f"LLM provider '{self.provider_name}' не настроен: отсутствует имя модели.",
                http_status=500,
            )

        payload: dict[str, Any] = {
            "model": selected_model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "parallel_tool_calls": False,
        }
        if self.request_defaults:
            payload.update(self.request_defaults)
        if max_output_tokens is not None:
            payload["max_tokens"] = max_output_tokens

        response_payload = await self._post_json("/chat/completions", payload)
        choices = response_payload.get("choices", [])
        if not choices:
            raise AppError(
                ErrorCode.UPSTREAM_UNAVAILABLE,
                f"LLM provider '{self.provider_name}' вернул пустой ответ без choices.",
                http_status=502,
                retriable=True,
            )

        message = choices[0].get("message", {})
        reasoning_content = _normalize_message_content(message.get("reasoning_content"))
        tool_calls_raw = message.get("tool_calls") or []
        tool_calls = [
            LLMToolCall(
                id=item.get("id", ""),
                name=item.get("function", {}).get("name", ""),
                arguments_json=item.get("function", {}).get("arguments", "") or "",
            )
            for item in tool_calls_raw
            if isinstance(item, dict)
        ]
        normalized_content = _normalize_message_content(message.get("content")) or reasoning_content

        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": message.get("content") if message.get("content") is not None else normalized_content,
        }
        if reasoning_content:
            assistant_message["reasoning_content"] = message.get("reasoning_content") if message.get("reasoning_content") is not None else reasoning_content
        if tool_calls:
            assistant_message["tool_calls"] = [tool_call.as_chat_completion_message() for tool_call in tool_calls]

        return LLMCompletion(
            message=assistant_message,
            content=normalized_content,
            tool_calls=tool_calls,
            model=response_payload.get("model", selected_model),
            raw=response_payload,
        )

    async def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.max_retries),
                wait=wait_exponential(multiplier=0.25, min=0.25, max=2),
                retry=retry_if_exception(_should_retry_llm),
                reraise=True,
            ):
                with attempt:
                    response = await self._client.post(url, json=payload, headers=headers)

                    if response.status_code == 401:
                        raise AppError(
                            ErrorCode.LLM_NOT_CONFIGURED,
                            f"LLM provider '{self.provider_name}' отклонил API key.",
                            http_status=502,
                        )
                    if response.status_code == 429:
                        raise AppError(
                            ErrorCode.RATE_LIMITED,
                            f"LLM provider '{self.provider_name}' достиг лимита запросов.",
                            http_status=429,
                            retriable=True,
                        )
                    if response.status_code >= 500:
                        raise AppError(
                            ErrorCode.UPSTREAM_UNAVAILABLE,
                            f"LLM provider '{self.provider_name}' временно недоступен.",
                            http_status=502,
                            retriable=True,
                        )
                    if response.status_code >= 400:
                        details = None
                        try:
                            details = _sanitize_error_details(response.json())
                        except ValueError:
                            details = None
                        raise AppError(
                            ErrorCode.VALIDATION_ERROR,
                            f"LLM provider '{self.provider_name}' отклонил запрос.",
                            http_status=400,
                            details=details,
                        )

                    try:
                        return response.json()
                    except ValueError as exc:
                        raise AppError(
                            ErrorCode.UPSTREAM_UNAVAILABLE,
                            f"LLM provider '{self.provider_name}' вернул не-JSON ответ.",
                            http_status=502,
                            retriable=True,
                        ) from exc
        except httpx.TimeoutException as exc:
            raise AppError(
                ErrorCode.UPSTREAM_TIMEOUT,
                f"LLM provider '{self.provider_name}' не успел ответить вовремя.",
                http_status=504,
                retriable=True,
            ) from exc
        except httpx.NetworkError as exc:
            raise AppError(
                ErrorCode.UPSTREAM_UNAVAILABLE,
                f"Сетевая ошибка при обращении к provider '{self.provider_name}'.",
                http_status=503,
                retriable=True,
            ) from exc
