# Стек

## Backend

- Python `>=3.11`
- `uv`
- `FastAPI`
- `httpx.AsyncClient`
- `Pydantic v2`
- `pydantic-settings`
- `PubChemPy`
- `orjson`
- `tenacity`
- `redis` client как задел на следующий этап
- `uvicorn`
- `pytest`

## Frontend

- `Next.js 16`
- `React 19`
- `bun`
- `Tailwind CSS 4`
- `TanStack Query v5`
- `react-hook-form`
- `zod`
- локальные примитивы в стиле `shadcn/ui`
- `lucide-react`

## Инфраструктура

- `Docker Compose`
- локальная схема из трёх сервисов:
  - `api`
  - `web`
  - `redis`
  В MVP сервис `redis` уже поднимается, но backend пока использует in-memory cache.

## Источники данных

- `PubChem PUG REST` — основной источник правды
- `PubChemPy` — удобная Python-обёртка для части запросов
- `PUG View` — следующий этап, пока не включён

## Чего здесь нет

- vector DB
- embeddings
- классической RAG-инфраструктуры
- прямого обращения браузера к PubChem
- автономного агентного выполнения
