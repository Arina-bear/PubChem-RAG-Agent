# Infra

## Local Langfuse (tracing)

`langfuse-compose.yml` запускает локальный self-hosted Langfuse v2
(Postgres + Langfuse web) для просмотра трейсов агента и LLM-вызовов.

### Запуск

```bash
docker compose -f infra/langfuse-compose.yml up -d
```

Через ~30 секунд:

1. Открой <http://localhost:3030>
2. **Sign up** (любой email/password — это локальный dev, не настоящая
   почта)
3. Создай **Organization** → **Project**
4. Перейди в **Settings → API keys** → **Create new API keys**
5. Скопируй `Public Key` (начинается с `pk-lf-...`) и `Secret Key`
   (начинается с `sk-lf-...`)
6. Открой `backend/.env` и заполни:

   ```env
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   LANGFUSE_BASE_URL=http://localhost:3030
   ```

7. Перезапусти `./scripts/dev.sh`. Каждый запрос к агенту теперь
   будет создавать трейс в Langfuse → раздел **Traces**.

### Остановка

```bash
docker compose -f infra/langfuse-compose.yml down
```

Чтобы удалить ещё и Postgres-данные (свежий старт):

```bash
docker compose -f infra/langfuse-compose.yml down -v
```

### Что увидишь в Langfuse UI

- **Trace** на каждый POST `/api/agent` — со всем cycle: разбор
  запроса → MCP tool call (`search_compound_by_name`) → ответ
  Gemini-3-flash-preview.
- **Tags**: `pubchem-agent`, `mcp-architecture`, провайдер
  (`gemini`/`openai`/`ollama`).
- **Latency / token usage** для каждой LLM-итерации.
- **Tool inputs/outputs** — фактические JSON-payload'ы от PubChem REST.

### Ports / volumes

| Сервис | Host | Container | Volume |
|---|---|---|---|
| Langfuse web | `127.0.0.1:3030` | `:3000` | — |
| Langfuse Postgres | `127.0.0.1:5433` | `:5432` | `langfuse_postgres_data` |

Bind на `127.0.0.1` чтобы Postgres не торчал на 0.0.0.0.

### Почему v2, а не v3

Langfuse v3 (текущий релиз) требует пять сервисов: Postgres,
ClickHouse, Redis, MinIO, langfuse-web, langfuse-worker — это
~6 GB RAM и долгий первый запуск. Для локального dev одного
контейнера v2 + Postgres достаточно. Для production self-host
переходи на v3 по [официальной инструкции](https://langfuse.com/docs/deployment/self-host).

## Основной dev-стек (`docker-compose.yml`)

`docker-compose.yml` (соседний файл) собирает образ FastAPI +
Chainlit из `backend/` и поднимает Redis. **Этот compose не
обязателен для локального dev** — `./scripts/dev.sh` запускает
оба процесса напрямую через `uv run` без Docker. Используй
`docker-compose.yml` только для production-подобной проверки.
