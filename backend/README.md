# Backend для PubChem Agent

Backend написан на `FastAPI` и теперь поддерживает три слоя:

- `/api/query` — типизированный прямой запрос к PubChem;
- `/api/interpret` — локальная интерпретация естественного языка в кандидаты запроса;
- `/api/agent` — supervised agent поверх узких PubChem tools и OpenAI-compatible LLM providers.

Если нужен самый быстрый практический гайд по запуску и подключению API, смотрите также [readme-api.md](../readme-api.md).

## Что изменилось в agent-слое

- текущая PubChem-обёртка разрезана на узкие tools;
- добавлен pre-parse слой перед tool loop;
- реализован минимальный ReAct/tool-calling loop;
- добавлены два OpenAI-compatible провайдера:
  - `openai`
  - `modal_glm`
- добавлены retry/backoff, таймауты, rate limiting и остановка на повторяющихся tool calls.

## Доступные tools

- `search_compound_by_name`
- `search_compound_by_smiles`
- `search_compound_by_formula`
- `search_compound_by_mass_range`
- `get_compound_summary`
- `name_to_smiles`
- `search_by_synonym`
- `ask_user_for_clarification`

Все tools имеют узкую сигнатуру, docstring и JSON-friendly ответ.

## Локальный запуск

```bash
cd backend
uv sync --group dev
uv run uvicorn app.main:app --app-dir src --reload --host 0.0.0.0 --port 8000
```

Если хотите поднять сразу backend и frontend одной командой из корня репозитория:

```bash
./scripts/dev.sh
```

## Переменные окружения

Создайте `.env` по примеру `.env.example`.

```bash
cp backend/.env.example backend/.env
```

Главные настройки для agent-mode:

```env
LLM_DEFAULT_PROVIDER=modal_glm
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
MODAL_GLM_BASE_URL=https://api.us-west-2.modal.direct/v1
MODAL_GLM_API_KEY=
MODAL_GLM_MODEL=zai-org/GLM-5-FP8
MODAL_GLM_DISABLE_THINKING=true
LLM_RATE_LIMIT_PER_SECOND=2
LLM_REQUEST_TIMEOUT_SECONDS=45
AGENT_MAX_STEPS=6
```

Ключи не хардкодятся в репозиторий и должны приходить только из env.

### Куда вставлять ключи

Только в:

- `backend/.env`

Не вставляйте ключи в:

- frontend код
- React-компоненты
- `curl` команды в README
- TypeScript файлы в `frontend/src`

### Минимальная конфигурация для Modal GLM-5

```env
LLM_DEFAULT_PROVIDER=modal_glm
MODAL_GLM_BASE_URL=https://api.us-west-2.modal.direct/v1
MODAL_GLM_API_KEY=YOUR_MODAL_KEY_HERE
MODAL_GLM_MODEL=zai-org/GLM-5-FP8
MODAL_GLM_DISABLE_THINKING=true
```

Для `GLM-5` это рекомендуемая настройка agent-mode: она отключает длинный reasoning-only ответ и помогает быстрее получить обычный финальный `content`.

### Минимальная конфигурация для OpenAI

```env
LLM_DEFAULT_PROVIDER=openai
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=YOUR_OPENAI_KEY_HERE
OPENAI_MODEL=gpt-4.1-mini
```

## Примеры запросов

### Typed query

```bash
curl -X POST http://127.0.0.1:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "compound",
    "input_mode": "name",
    "identifier": "aspirin",
    "operation": "property",
    "include_raw": true
  }'
```

### Agent mode через Modal GLM-5

```bash
curl -X POST http://127.0.0.1:8000/api/agent \
  -H "Content-Type: application/json" \
  -d '{
    "text": "найди aspirin",
    "provider": "modal_glm",
    "max_steps": 6,
    "include_raw": false
  }'
```

JavaScript пример:

```ts
const response = await fetch("http://127.0.0.1:8000/api/agent", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    text: "найди молекулу по описанию и верни свойства",
    provider: "modal_glm",
    include_raw: true,
  }),
});

const data = await response.json();
```

### Agent mode через OpenAI

```bash
curl -X POST http://127.0.0.1:8000/api/agent \
  -H "Content-Type: application/json" \
  -d '{
    "text": "find a compound with molecular weight around 180",
    "provider": "openai"
  }'
```

## Что вернёт `/api/agent`

Самые полезные поля:

- `normalized.answer` — финальный ответ агента
- `normalized.parsed_query` — что удалось извлечь из естественного языка
- `normalized.compounds` — найденные compounds
- `normalized.tool_calls` — trace вызванных tools
- `warnings` — предупреждения
- `raw.steps` — сырые шаги LLM, если `include_raw=true`

Важно:

- интерфейс показывает `ход агента` и `tools trace`
- это не полный скрытый chain-of-thought модели
- для отладки используйте `parsed_query`, `tool_calls` и `raw.steps`

## Тесты

Если активная `uv`-среда уже собрана:

```bash
backend/.venv/bin/pytest backend/tests -q
```

Или стандартно через `uv`:

```bash
cd backend
uv run pytest
```

## Что сейчас поддерживается

- домен `compound`;
- режимы ввода `cid`, `name`, `smiles`, `inchikey`, `formula`;
- агентный поиск по названию, SMILES, формуле, синониму и диапазону массы;
- OpenAI-compatible providers для tool calling.

## Что пока не включено

- полноценная multi-turn memory между пользовательскими сообщениями;
- большой граф оркестрации;
- расширенный semantic retrieval по фармакологии и литературе;
- авторизация для публичного multi-tenant развёртывания.
