# Backend для интерфейса запросов к PubChem

Backend написан на `FastAPI` и отвечает за две вещи:

- выполнение типизированных запросов к PubChem;
- интерпретацию текстового запроса в структурированный запрос.

## Локальный запуск

```bash
uv sync
uv run uvicorn app.main:app --app-dir src --reload --host 0.0.0.0 --port 8000
```

## Тесты

```bash
uv run pytest
```

## Что сейчас поддерживается

- домен `compound`;
- режимы ввода `cid`, `name`, `smiles`, `inchikey`, `formula`;
- операции `property`, `record`, `synonyms`.

## Что пока не включено

- `autocomplete`;
- `bundle`;
- `jobs`;
- `PUG View` и тяжёлые структурные поиски.
