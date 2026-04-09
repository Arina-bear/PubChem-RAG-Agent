# MVP-архив и API-заметки для PubChem

Этот файл теперь служит как переходная заметка между старым MVP и новой Chainlit-версией.

Этот файл вынесен из корня проекта в `readme-api.md`, чтобы при встраивании в другой репозиторий не перезаписывать его основной `README.md`.
Текущая структура проекта остаётся изолированной: основная реализация лежит в отдельных папках и может переноситься поверх чужой ветки без удаления уже существующих файлов.

Сейчас важно различать два состояния:

- `legacy MVP` на `frontend/` с `Next.js`
- `текущий основной UI` на `Chainlit`

Это не классический векторный RAG. Текущая версия делает grounded-запросы к PubChem через adapter/tools и показывает результат либо через API, либо через Chainlit UI.

## Актуальная структура проекта

- `backend/` — FastAPI backend, адаптер PubChem, нормализация ответов, тесты.
- `backend/src/chainlit_app.py` — текущий основной UI entrypoint.
- `frontend/` — legacy Next.js интерфейс из раннего MVP.
- `infra/` — `docker-compose` для `api`, `chainlit` и `redis`.
  Сейчас `redis` уже подготовлен в инфраструктуре, но в MVP рантайм всё ещё использует in-memory cache.
- `docs/` — краткая документация по архитектуре, API, стеку и текущим ограничениям.

## Локальный запуск

### Основной dev flow

```bash
./scripts/dev.sh
```

После этого:

- Chainlit UI: `http://127.0.0.1:3000`
- FastAPI API: `http://127.0.0.1:8000`

Если нужен только API:

```bash
cd backend
uv sync
uv run uvicorn app.main:app --app-dir src --reload --host 0.0.0.0 --port 8000
```

Если нужен только Chainlit UI:

```bash
cd backend
uv sync
uv run chainlit run src/chainlit_app.py --headless --host 127.0.0.1 --port 3000
```

## Что уже работает

- `GET /api/health`
- `POST /api/query`
- `POST /api/interpret`
- `POST /api/agent`
- LangChain tools для `name`, `smiles`, `formula`, `inchikey`, `mass_range`, `synonym`, `name_to_smiles`, `compound_summary`, `clarification`
- Chainlit UI с `CompoundCard`, `tool trace`, streaming steps и Langfuse-ready tracing

## Что пока не включено

- `autocomplete`
- `bundle`
- `jobs`
- `PUG View`
- тяжёлые структурные поиски в UI
- полный вывод bioactivity / assay / reference tools
