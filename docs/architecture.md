# Архитектура

## Общая идея

- `Ручной режим` — основной и самый надёжный путь.
- `агентный режим` — теперь это отдельный backend runtime на `LangChain`, который сам выбирает PubChem tools и возвращает final answer, candidates и tool trace.
- В текущей версии поддерживается только домен `compound`.

## Структура репозитория

- `backend/`
  - FastAPI backend
  - Chainlit UI runtime
  - transport и adapter для PubChem
  - normalizers
  - services
  - `agent/` с LangChain runtime, tools, tracing и prompts
  - tests
- `frontend/`
  - legacy Next.js shell из раннего MVP
  - не считается целевым UI для новой agent-версии
- `infra/`
  - `docker-compose` для `chainlit`, `api`, `redis`
  - `redis` уже подготовлен в инфраструктуре, но ещё не подключён к MVP runtime
- `docs/`
  - основные knowledge files проекта

## Backend

### Конфигурация

- Все настройки читаются из окружения.
- Здесь задаются таймауты, лимиты, TTL кэша и базовые URL PubChem.

### Доступ к PubChem

- `PubChemTransport`
  - использует общий `httpx.AsyncClient`
  - умеет retry/backoff
  - переводит ошибки PubChem в понятные ошибки приложения
- `PubChemAdapter`
  - использует `PubChemPy`, где это удобно
  - для остальных случаев ходит напрямую в `PUG REST`
  - остаётся единственным источником правды для доступа к PubChem

### LangChain agent layer

- `app/agent/tools.py`
  - объявляет LangChain-native tools через `@tool(args_schema=...)`
  - не делает raw `requests`
  - делегирует всю PubChem логику в `PubChemAdapter`
- `app/agent/model_factory.py`
  - собирает `ChatOpenAI` для `modal_glm` и `openai`
- `app/agent/runtime.py`
  - создаёт `create_agent(...)`
  - подключает structured output через `ToolStrategy(...)`
- `app/agent/tracing.py`
  - подключает `Langfuse CallbackHandler`
  - пишет компактный `tool_trace` для UI и API
- `app/services/agent_service.py`
  - запускает agent runtime
  - собирает финальный envelope для `POST /api/agent`
- `app/services/agent_stream_service.py`
  - использует тот же runtime для UI-сценариев
  - умеет добавлять Chainlit callbacks и tracing metadata без дублирования логики
- `app/presenters/compound_card.py`
  - собирает компактный UI-friendly payload для карточки вещества и trace blocks

### Сервисный слой

- `QueryService`
  - принимает типизированный запрос
  - находит кандидатов
  - гидрирует карточки соединений
  - возвращает нормализованный ответ
- `InterpretService`
  - разбирает текст
  - предлагает кандидаты запросов
  - всегда требует подтверждение перед запуском
- `AgentService`
  - принимает natural-language запрос
  - даёт LangChain agent право выбирать tools
  - возвращает `final_answer`, `parsed_query`, `matches`, `compounds`, `tool_trace`

### Вспомогательные механизмы

- in-process rate limiter
- in-memory cache
- нормализованные ошибки и warnings
- Langfuse tracing для agent invoke path

## UI

- Исторически в репозитории остался Next.js экран раннего MVP.
- Текущий основной UI — `Chainlit`, а не старый interpret-confirm flow.
- Chainlit сейчас реализован в [backend/src/chainlit_app.py](/Volumes/ADATA%20SC750%20(APFS)/Time%20Management/Проекты/Стажировка%20ТГУ%20(наш%20проект)/backend/src/chainlit_app.py).
- Он использует service layer напрямую, а не ходит в `/api/agent` через HTTP.
- Правильная интеграция для нового UI:
  - ввод natural-language запроса
  - показ `final_answer`
  - streaming tool activity через `LangchainCallbackHandler`
  - явные `cl.Step()` для интерпретации и выбора результата
  - `cl.CustomElement("CompoundCard")` для rich-карточки вещества
  - показ `tool_trace`
  - показ candidate compounds и базовых свойств
  - без показа raw chain-of-thought

## Активные endpoints

- `GET /api/health`
- `POST /api/query`
- `POST /api/interpret`
- `POST /api/agent`

## Что заложено на будущее, но пока не включено

- `GET /api/autocomplete`
- `GET /api/compound/{cid}/bundle`
- `GET /api/jobs/{job_id}`
- `PUG View`
- тяжёлые структурные поиски
- richer tools для description / references / xrefs
