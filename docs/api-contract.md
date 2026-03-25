# API-контракт

## `GET /api/health`

Возвращает базовый статус сервиса и информацию о настроенных upstream-URL.

## `POST /api/query`

Принимает `ManualQuerySpec`.

### Пример запроса

```json
{
  "domain": "compound",
  "input_mode": "name",
  "identifier": "aspirin",
  "operation": "property",
  "properties": [],
  "filters": {},
  "pagination": null,
  "output": "json",
  "include_raw": true
}
```

### Поддерживаемые режимы ввода backend

- `cid`
- `name`
- `smiles`
- `inchikey`
- `formula`

В ручном UI сейчас показаны только `cid`, `name` и `smiles`.

### Поддерживаемые операции

- `property`
- `record`
- `synonyms`

Остальные имена операций уже зарезервированы в схеме, но в этой версии ещё не включены.

### Ответ

Общий envelope содержит:

- `trace_id`
- `source`
- `status`
- `raw`
- `normalized`
- `presentation_hints`
- `warnings`
- `error`

### Что находится в `normalized`

- `query`
- `matches[]`
- `primary_result`
- `synonyms[]`

## `POST /api/interpret`

Возвращает кандидаты структурированных запросов.

### Основные поля ответа

- `candidates[]`
- `confidence`
- `ambiguities[]`
- `assumptions[]`
- `warnings[]`
- `recommended_candidate_index`
- `needs_confirmation`

`recommended_candidate_index` нужен только для выбора кандидата по умолчанию. В интерфейсе он не показывается как “рекомендация”, а используется как техническое поле.

## Коды ошибок

- `VALIDATION_ERROR`
- `NO_MATCH`
- `AMBIGUOUS_QUERY`
- `ASYNC_PENDING`
- `RATE_LIMITED`
- `UPSTREAM_TIMEOUT`
- `UPSTREAM_UNAVAILABLE`
- `UNSUPPORTED_QUERY`
- `INTERPRETATION_LOW_CONFIDENCE`

## Следующий слой API

- `GET /api/autocomplete`
- `GET /api/compound/{cid}/bundle`
- `GET /api/jobs/{job_id}`
