# Backend для PubChem Agent

`backend/` теперь содержит сразу два слоя:

- `FastAPI` API для `POST /api/query`, `POST /api/interpret`, `POST /api/agent`
- `Chainlit` UI runtime в [src/chainlit_app.py](/Volumes/ADATA%20SC750%20(APFS)/Time%20Management/Проекты/Стажировка%20ТГУ%20(наш%20проект)/backend/src/chainlit_app.py)

Главная идея такая:

- `PubChemTransport` и `PubChemAdapter` — единственный источник правды для доступа к PubChem
- `LangChain tools` не делают raw HTTP сами, а только делегируют в adapter
- `Chainlit` использует тот же Python runtime напрямую, а не дублирует agent orchestration через отдельный HTTP клиент

## Локальный запуск

1. Создайте локальный env:

```bash
cp .env.example .env
```

2. Заполните хотя бы:

```env
LLM_DEFAULT_PROVIDER=modal_glm
MODAL_GLM_API_KEY=...
MODAL_GLM_MODEL=zai-org/GLM-5-FP8
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

3. Запустите полный dev flow из корня репозитория:

```bash
./scripts/dev.sh
```

Или отдельно только backend API:

```bash
cd backend
uv sync
uv run uvicorn app.main:app --app-dir src --reload --host 0.0.0.0 --port 8000
```

Или отдельно основной Chainlit UI:

```bash
cd backend
uv sync
uv run chainlit run src/chainlit_app.py --headless --host 127.0.0.1 --port 3000
```

Chainlit нужно запускать именно из `backend/`, потому что рядом лежат:

- `.chainlit/config.toml`
- `public/theme.json`
- `public/custom.css`
- `public/custom.js`
- `public/elements/CompoundCard.jsx`

## Тесты

```bash
cd backend
uv run pytest -q
```

## Активные endpoints

- `GET /api/health`
- `POST /api/query`
- `POST /api/interpret`
- `POST /api/agent`

## `/api/agent`

Запрос:

```json
{
  "text": "антибиотик с бензольным кольцом и массой около 350",
  "provider": "modal_glm",
  "include_raw": true
}
```

Ответ содержит:

- `final_answer`
- `parsed_query`
- `matches`
- `compounds`
- `tool_trace`
- `referenced_cids`

## Chainlit UI

Новый UI построен через `Chainlit + LangChainCallbackHandler + cl.Step + cl.CustomElement`.

Что показывает интерфейс:

- streamed agent session
- `tool_call`-уровень chain-of-thought display
- карточку вещества `CompoundCard`
- изображения структуры из PubChem
- краткий tool trace
- ranked candidate compounds

Главные файлы UI:

- [src/chainlit_app.py](/Volumes/ADATA%20SC750%20(APFS)/Time%20Management/Проекты/Стажировка%20ТГУ%20(наш%20проект)/backend/src/chainlit_app.py)
- [public/elements/CompoundCard.jsx](/Volumes/ADATA%20SC750%20(APFS)/Time%20Management/Проекты/Стажировка%20ТГУ%20(наш%20проект)/backend/public/elements/CompoundCard.jsx)
- [.chainlit/config.toml](/Volumes/ADATA%20SC750%20(APFS)/Time%20Management/Проекты/Стажировка%20ТГУ%20(наш%20проект)/backend/.chainlit/config.toml)
- [public/theme.json](/Volumes/ADATA%20SC750%20(APFS)/Time%20Management/Проекты/Стажировка%20ТГУ%20(наш%20проект)/backend/public/theme.json)

## Canonical PubChem tools

Текущий LangChain tool set:

- `search_compound_by_name`
- `search_compound_by_smiles`
- `search_compound_by_formula`
- `search_compound_by_inchikey`
- `search_compound_by_mass_range`
- `get_compound_summary`
- `name_to_smiles`
- `search_by_synonym`
- `ask_user_for_clarification`

Все tools объявлены нативно через `langchain.tools.tool` и `args_schema`, а не через самописный loop.

## LLM providers

Сейчас поддерживаются:

- `modal_glm`
- `openai`

Оба провайдера подключаются через `ChatOpenAI` с OpenAI-compatible API. Для `modal_glm` backend использует `base_url=https://api.us-west-2.modal.direct/v1` и может отключать thinking через `MODAL_GLM_DISABLE_THINKING=true`.

## Langfuse

Если заданы `LANGFUSE_PUBLIC_KEY` и `LANGFUSE_SECRET_KEY`, backend автоматически подключает `langfuse.langchain.CallbackHandler` к каждому agent invoke и отправляет:

- `trace_id`
- provider tag
- session metadata

## Что пока не включено

- `PUG View` и тяжёлые структурные поиски
- отдельные tools для references / assay / bioactivity
- production-grade docker/orchestration polish поверх текущего local dev flow
