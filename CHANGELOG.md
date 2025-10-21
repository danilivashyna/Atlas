# v0.4 — Router v0: Path-Aware Routing + Hierarchical Memory

Path-aware routing via 5D encoding with hierarchical node scoring and soft child activation.

## Summary

- **Router**: POST `/router/route` (score nodes), POST `/router/activate` (soft-activate children)
- **Nodes Table**: SQLite table for hierarchical nodes (path, parent, vec5, label, weight, meta)
- **Scoring**: score = α·cosine + β·prior + γ·child_bonus (configurable weights)
- **Activation**: Softmax-based soft activation with temperature τ
- **Feature flags**:
  - `ATLAS_ROUTER_MODE = on | off` (default: on)
  - `ATLAS_ROUTER_ALPHA=0.7`, `ATLAS_ROUTER_BETA=0.2`, `ATLAS_ROUTER_GAMMA=0.1`, `ATLAS_ROUTER_TAU=0.5`

## New Files

- `src/atlas/router/path_router.py` — PathRouter class
- `src/atlas/api/router_routes.py` — FastAPI routes
- `tests/test_router_api.py` — Test suite
- `docs/v0.4_ROUTER.md` — Full documentation

## New Endpoints

### POST /router/route
Route text to top-k hierarchical nodes.
- Request: `{ "text": "...", "top_k": 3 }`
- Response: `{ "items": [{"path": "...", "score": 0.83, "label": "...", "meta": null}], "trace_id": "..." }`

### POST /router/activate
Soft-activate children of a node.
- Request: `{ "path": "dim2/dim2.4", "text": "..." }`
- Response: `{ "children": [{"path": "...", "p": 0.62}, ...], "trace_id": "..." }`

## Database Extension

Added `nodes` table to SQLite (same DB as items table):

```sql
CREATE TABLE nodes (
    path TEXT PRIMARY KEY,
    parent TEXT,
    v1..v5 REAL,
    label TEXT,
    weight REAL DEFAULT 0.5,
    meta JSON
);
CREATE INDEX idx_nodes_parent ON nodes(parent);
CREATE INDEX idx_nodes_path ON nodes(path);
```

## Backward Compatibility

- ✅ All v0.3 endpoints unchanged
- ✅ All v0.2 endpoints unchanged
- ✅ Router optional (can be disabled via `ATLAS_ROUTER_MODE=off`)
- ✅ No breaking changes to /encode, /decode, /explain, /summarize, /memory/*, /encode_h, /decode_h, /manipulate_h

---

# v0.3 — Memory Persistence

Persistent memory backends (SQLite), extended management API, unified factory.

## Summary

- **Backends**: in-process (MappaMemory) or SQLite (PersistentMemory)
- **Factory**: `get_memory()` returns singleton based on `ATLAS_MEMORY_BACKEND` env
- **API**: `/memory/flush`, `/memory/load`, `/memory/stats` (new)
- **Summarize**: Integration unchanged; works with both backends transparently
- **Feature flags**:
  - `ATLAS_MEMORY_BACKEND = inproc | sqlite` (default: inproc)
  - `ATLAS_MEMORY_MODE = on | off` (default: on)
  - `ATLAS_SUMMARY_MODE = proportional | off` (default: proportional)

## New Endpoints

### POST /memory/flush
Delete all records. Response: `{ "removed": <int> }`

### POST /memory/load
Bulk load from JSONL file. Request: `{ "path": "<file>" }`. Response: `{ "loaded": <int> }`

### GET /memory/stats
Statistics. Response: `{ "backend": "sqlite|inproc", "count": <int>, "path": "...", "size_bytes": <int> }`

## Database (SQLite)

Table: `items(id TEXT PRIMARY KEY, v1..v5 REAL, meta JSON)`

Similarity: cosine, computed on-the-fly (no index yet).

---

# v0.2 — Summarization & Memory Blending

Этот документ описывает `POST /summarize` и легковесную память (MappaMemory) с возможностью блендинга
содержания при суммаризации.

## Сводка

- Алгоритм: **пропорциональная суммаризация** с сохранением 5D семантических долей и контролем KL-дивергенции.
- Режимы: `compress` (сжатие) / `expand` (расширение).
- Фича-флаги:
  - `ATLAS_SUMMARY_MODE = proportional | off`
  - `ATLAS_MEMORY_MODE = on | off`
- Память: `/memory/write`, `/memory/query` (in-process mock, cosine-similarity).
- Блендинг: `use_memory`, `memory_top_k`, `memory_weight`.

---

## Endpoint: POST /summarize

### Request (SummarizeRequest)
```json
{
  "text": "string, min 1, max 50000",
  "target_tokens": 120,
  "mode": "compress | expand",
  "epsilon": 0.05,
  "preserve_order": true,
  "use_memory": true,
  "memory_top_k": 3,
  "memory_weight": 0.25
}
```

- `target_tokens`: целевая длина (10..5000)
- `epsilon`: допуск по KL-дивергенции (0..1)
- `use_memory`: включить блендинг с памятью
- `memory_top_k`: брать top-K результатов из памяти (по cosine)
- `memory_weight`: доля влияния памяти в блендинге (0..1)

### Response (SummarizeResponse)
```json
{
  "summary": "string",
  "length": 118,
  "ratio_target": [0.28, 0.07, 0.35, 0.10, 0.20],
  "ratio_actual": [0.27, 0.08, 0.34, 0.11, 0.20],
  "kl_div": 0.012,
  "trace_id": "string",
  "timestamp": "ISO8601 UTC"
}
```

### Пример cURL
```bash
# сервер:
ATLAS_SUMMARY_MODE=proportional uvicorn src.atlas.api.app:app --port 8010

# запись в память:
curl -sS http://127.0.0.1:8010/memory/write \
  -H 'Content-Type: application/json' \
  --data-binary '{"id":"doc1","vector":[0.1,0.0,0.8,0.0,0.2],"meta":{"title":"hello world"}}' | jq .

# запрос к памяти:
curl -sS http://127.0.0.1:8010/memory/query \
  -H 'Content-Type: application/json' \
  --data-binary '{"vector":[0.1,0.0,0.7,0.0,0.2],"top_k":3}' | jq .

# суммаризация c блендингом памяти:
curl -sS http://127.0.0.1:8010/summarize \
  -H 'Content-Type: application/json' \
  --data-binary '{"text":"AI is transforming industries. Machine learning helps computers learn.",
                  "target_tokens":30,"mode":"compress","epsilon":0.05,"preserve_order":true,
                  "use_memory":true,"memory_top_k":3,"memory_weight":0.3}' | jq .
```

---

## Память: MappaMemory (mock)

### POST /memory/write
```json
{
  "id": "string",
  "vector": [v1, v2, v3, v4, v5],
  "meta": { "title": "optional" }
}
```
Ответ:
```json
{ "ok": true, "trace_id": null }
```

### POST /memory/query
```json
{
  "vector": [v1, v2, v3, v4, v5],
  "top_k": 3
}
```
Ответ (схема упрощена):
```json
{
  "items": [
    { "id": "doc1", "score": 0.99, "vector": [..], "meta": { "title": "..." } }
  ],
  "trace_id": null
}
```

---

## Флаги окружения

- `ATLAS_SUMMARY_MODE`:
  - `proportional` — включен эндпоинт `/summarize`
  - `off` — эндпоинт может быть отключён (см. тесты; по умолчанию включён)
- `ATLAS_MEMORY_MODE`:
  - `on` — память используется, если `use_memory=true`
  - `off` — память отключена, даже если `use_memory=true`

---

## Проверка

```bash
# тесты по целевому набору:
pytest -q -k "summarize or memory_api or api_smoke" --maxfail=1

# openapi:
curl -sS http://127.0.0.1:8010/openapi.json | jq '.paths["/summarize"].post.requestBody'
```

## Замечания по реализации

- Блендинг памяти выполнен на уровне evidence-сниппетов с мягким смешением весов:
  `combined = local*(1 - memory_weight) + memory*memory_weight`.
- Ошибки обращений к памяти игнорируются (graceful fallback).
- `MappaMemory` — in-process singleton (подходит для демо/тестов).
