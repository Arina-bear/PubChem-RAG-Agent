# API и запуск PubChem Agent

Этот файл нужен как практическая инструкция: что именно заполнять, куда вставлять ключи, какой endpoint использовать и как запустить весь проект одной командой.

Сейчас в проекте есть два режима:

- `Ручной режим` для точного PubChem-запроса по `name`, `cid` или `smiles`
- `Агентный режим` для natural-language поиска через `tool calling`

Это не классический векторный RAG. Текущая версия делает прямые запросы к PubChem и использует LLM как маршрутизатор поверх узких tools.

## Быстрый старт

### 1. Создать backend env

Если файла ещё нет:

```bash
cp backend/.env.example backend/.env
```

### 2. Вставить API ключи в `backend/.env`

Главный файл конфигурации:

- `backend/.env`

Минимально для работы через ваш `Modal GLM-5`:

```env
LLM_DEFAULT_PROVIDER=modal_glm
MODAL_GLM_BASE_URL=https://api.us-west-2.modal.direct/v1
MODAL_GLM_API_KEY=YOUR_MODAL_KEY_HERE
MODAL_GLM_MODEL=zai-org/GLM-5-FP8
MODAL_GLM_DISABLE_THINKING=true
```

`MODAL_GLM_DISABLE_THINKING=true` рекомендуется оставить включённым для agent-mode: так GLM-5 быстрее отдаёт финальный ответ и не зависает на длинном reasoning вместо обычного `content`.

Если хотите использовать OpenAI:

```env
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=YOUR_OPENAI_KEY_HERE
OPENAI_MODEL=gpt-4.1-mini
```

### 3. Запустить проект одной командой

Из корня репозитория:

```bash
./scripts/dev.sh
```

После запуска:

- frontend: `http://localhost:3000`
- backend: `http://127.0.0.1:8000`

Если в dev-режиме открываете сайт через `127.0.0.1`, а не через `localhost`, после изменения `frontend/next.config.ts` нужно один раз перезапустить `./scripts/dev.sh`.

## Куда что вставлять

### LLM ключи

Вставляются только в:

- `backend/.env`

Не вставляйте ключи в:

- `frontend/.env`
- React-компоненты
- `src/lib/api.ts`
- `curl` примеры в репозитории

### Как выбрать провайдера по умолчанию

В `backend/.env`:

```env
LLM_DEFAULT_PROVIDER=modal_glm
```

или

```env
LLM_DEFAULT_PROVIDER=openai
```

### Как выбрать провайдера на один конкретный запрос

Через поле `provider` в `POST /api/agent`:

```json
{
  "text": "acetone",
  "provider": "modal_glm"
}
```

## Что уже подключено в проекте

### Backend

- `backend/src/app/api/routes/agent.py` — endpoint `POST /api/agent`
- `backend/src/app/llm/providers.py` — OpenAI-compatible слой для `openai` и `modal_glm`
- `backend/src/app/services/agent_service.py` — agent loop
- `backend/src/app/services/pubchem_tools.py` — узкие PubChem tools
- `backend/src/app/services/query_parser.py` — pre-parse естественного языка

### Frontend

- `frontend/src/app/api/agent/route.ts` — same-origin proxy в backend
- `frontend/src/components/agent-query-form.tsx` — natural-language форма агента
- `frontend/src/components/agent-result-panel.tsx` — ответ, кандидаты, parsed intent, tools, JSON

## Как использовать API

### 1. Проверка, что backend поднялся

```bash
curl http://127.0.0.1:8000/api/health
```

### 2. Ручной точный запрос

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

### 3. Агентный natural-language запрос

```bash
curl -X POST http://127.0.0.1:8000/api/agent \
  -H "Content-Type: application/json" \
  -d '{
    "text": "антибиотик с бензольным кольцом, молекулярная масса около 350",
    "provider": "modal_glm",
    "max_steps": 6,
    "max_output_tokens": 900,
    "include_raw": true
  }'
```

## Как использовать API из JavaScript / frontend

Если другой frontend ходит напрямую в backend:

```ts
const response = await fetch("http://127.0.0.1:8000/api/agent", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    text: "соединение похоже на aspirin",
    provider: "modal_glm",
    include_raw: true,
  }),
});

const data = await response.json();
```

Если код живёт внутри текущего Next.js frontend, используйте same-origin маршрут:

```ts
const response = await fetch("/api/agent", {
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

## Как использовать API из Python

```python
import requests

response = requests.post(
    "http://127.0.0.1:8000/api/agent",
    json={
        "text": "acetone",
        "provider": "modal_glm",
        "include_raw": True,
    },
    timeout=60,
)

print(response.json())
```

## Что вернёт `POST /api/agent`

Нормализованный ответ содержит:

- `normalized.answer` — финальный текстовый ответ агента
- `normalized.parsed_query` — что агент извлёк из естественного языка
- `normalized.compounds` — найденные compounds
- `normalized.tool_calls` — trace вызванных tools
- `warnings` — предупреждения
- `raw.steps` — сырые шаги LLM, если `include_raw=true`

Важно:

- UI показывает `ход агента`, parsed signals и trace tools
- UI не показывает скрытый chain-of-thought модели
- для дебага используйте `tool_calls` и `raw.steps`

## Какие tools доступны агенту

- `search_compound_by_name`
- `search_compound_by_smiles`
- `search_compound_by_formula`
- `search_compound_by_mass_range`
- `get_compound_summary`
- `name_to_smiles`
- `search_by_synonym`
- `ask_user_for_clarification`

## Типичный workflow

1. Заполнить `backend/.env`
2. Запустить `./scripts/dev.sh`
3. Открыть `http://localhost:3000`
4. В режиме `Агент` написать запрос обычным языком
5. Смотреть `Ответ`, `Кандидаты`, `Ход агента`, `Tools`

## Что сейчас уже работает

- `GET /api/health`
- `POST /api/query`
- `POST /api/interpret`
- `POST /api/agent`
- ручной поиск по `name`, `cid`, `smiles`
- агентный поиск через `modal_glm` и `openai`
- natural-language UI с parsed intent, tool trace и JSON

## Что пока не включено

- `autocomplete`
- `bundle`
- `jobs`
- `PUG View`
- тяжёлые структурные поиски в UI
- полноценная multi-turn memory
