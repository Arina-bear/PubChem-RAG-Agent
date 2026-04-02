# Архитектура

## Статус ветки

- Состояние на `2026-04-02` отдельно сохранено в ветке `MVP_tools_calling`.
- Этот срез нужно считать архивным MVP, а не целевой архитектурой.
- В нём tools/orchestration реализованы вручную; следующий правильный этап должен опираться на готовые инструменты вроде `LangChain` и `Langfuse`.
- Детальная пометка лежит в `docs/mvp-tools-calling-2026-04-02.md`.

## Общая идея

- `Ручной режим` — точный typed путь для проверки PubChem API без участия LLM.
- `агентный режим` — основной natural-language путь: пользователь пишет запрос обычным языком, agent-layer сам выделяет признаки, вызывает tools и возвращает объяснимый ответ.
- В текущей версии поддерживается только домен `compound`.

## Структура репозитория

- `backend/`
  - FastAPI backend
  - transport и adapter для PubChem
  - normalizers
  - services
  - tests
- `frontend/`
  - Next.js App Router
  - экран с двумя режимами
  - same-origin маршруты `/api/*`, которые проксируют запросы в backend
- `infra/`
  - `docker-compose` для `web`, `api`, `redis`
  - `redis` уже подготовлен в инфраструктуре, но ещё не подключён к MVP runtime
- `docs/`
  - основные knowledge files проекта
  - `pubchem-agent-meeting-notes/` содержит тематические части meeting notes по PubChem-агенту
- `pubchem-agent-meeting-notes.md`
  - входной индекс для разбитых meeting notes по PubChem-агенту

## Backend

### Конфигурация

- Все настройки читаются из окружения.
- Здесь задаются таймауты, лимиты, TTL кэша, базовые URL PubChem и настройки LLM providers.
- Для agent-layer предусмотрены отдельные переменные:
  - `LLM_DEFAULT_PROVIDER`
  - `OPENAI_*`
  - `MODAL_GLM_*`
  - `LLM_RATE_LIMIT_PER_SECOND`
  - `AGENT_MAX_STEPS`

### Доступ к PubChem

- `PubChemTransport`
  - использует общий `httpx.AsyncClient`
  - умеет retry/backoff
  - переводит ошибки PubChem в понятные ошибки приложения
- `PubChemAdapter`
  - использует `PubChemPy`, где это удобно
  - для остальных случаев ходит напрямую в `PUG REST`

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
- `QueryParserService`
  - делает первый структурированный разбор естественного языка
  - пытается выделить название, SMILES, формулу, диапазон массы и смысловые дескрипторы
  - решает, можно ли идти в tool loop или лучше сразу задать уточнение
- `PubChemToolbox`
  - содержит узкие agent tools
  - каждый tool делает одну операцию и возвращает JSON-friendly payload
- `AgentService`
  - запускает supervised tool-calling loop
  - использует pre-parse слой до LLM
  - ограничивает число шагов
  - останавливается на повторяющихся tool calls и на уточняющем вопросе

### Вспомогательные механизмы

- in-process rate limiter
- in-memory cache
- нормализованные ошибки и warnings
- отдельный limiter для LLM-запросов

### Agent tools

- `search_compound_by_name`
- `search_compound_by_smiles`
- `search_compound_by_formula`
- `search_compound_by_mass_range`
- `get_compound_summary`
- `name_to_smiles`
- `search_by_synonym`
- `ask_user_for_clarification`

### LLM providers

- используется OpenAI-compatible слой поверх `/chat/completions`
- сейчас поддерживаются два провайдера:
  - `openai`
  - `modal_glm`
- tool calling реализован через описание tools и автоматический выбор функцией модели
- ключи не хардкодятся в репозиторий и должны приходить только из env

## Frontend

- Одна главная страница.
- Слева формы `Ручной режим` и `агентный режим`.
- Для `агентного режима` UI работает поверх `POST /api/agent`, а не поверх старого подтверждения кандидатов.
- Справа для agent UI доступны вкладки:
  - `Ответ`
  - `Кандидаты`
  - `Ход агента`
  - `Tools`
  - `JSON`
- `Ход агента` показывает extracted signals, выбранную стратегию поиска и trace шагов без жёсткой ручной маршрутизации во фронтенде.
- `Tools` показывает аргументы и укороченные результаты каждого tool call.
- Браузер не ходит в PubChem напрямую.
- same-origin маршруты фронтенда проксируют:
  - `/api/query`
  - `/api/interpret`
  - `/api/agent`

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
- полноценная multi-turn memory
- auth и multi-tenant защита для публичного agent endpoint
