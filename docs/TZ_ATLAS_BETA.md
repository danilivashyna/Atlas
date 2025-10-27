# Atlas β — ТЗ (память + иерархия + безопасные стыки с FAB)

---

## ⚠️ **Scope Clarification**

**Atlas β implements ONLY the Memory and Hierarchical Encoding subsystem.**

- **This is a memory engine, NOT an AGI prototype.**
- Conscious or self-reflective behaviors (FAB/HSI/Sphere layers) are **explicitly out of scope**.
- FAB acts **only as a stateless data routing layer**, not a feedback or learning loop.
- All logic must be **deterministic, reproducible, and verifiable** via `make validate` and `make smoke`.

**What Atlas β IS:**
- ✅ Hierarchical semantic memory (5D + token/sent/para/doc levels)
- ✅ Multi-level search with deterministic fusion (RRF, max_sim)
- ✅ Index builders (HNSW/FAISS) with MANIFEST versioning
- ✅ Memory quality metrics (H-Coherence, H-Stability)
- ✅ Stateless API with Pydantic validation

**What Atlas β IS NOT:**
- ❌ Consciousness / self-awareness / observer patterns
- ❌ Attention policies / intention mechanisms
- ❌ Online learning / self-modification without review
- ❌ Autonomous agents / planning systems
- ❌ HSI (Human-level Self-Improvement) crossing boundaries

**Safety Constraints:**
- All parameters in configs (git-tracked, reviewed)
- MANIFEST validates artifacts (SHA256 checksums)
- No runtime config mutation
- ConfigLoader is read-only
- RRF/max_sim are pure functions (same input → same output)

**Focus:** E1–E3 roadmap tasks (schemas → indices → metrics). Keep all work within memory subsystem boundaries.

---

## 0) Цель релиза

Довести Atlas до беты как производственную систему иерархической памяти и смысловой навигации:

- **Иерархическое кодирование/декодирование** (rule-based — готово; нейронный S1 подключается опционально).
- **Стабильные API**: `/encode`, `/decode`, `/explain`, `/encode_h`, `/decode_h`, `/manipulate_h`, `/search`.
- **Индексация HNSW/FAISS** и многоуровневый ретрив (sentence/paragraph/document) с детерминированным слиянием (RRF / max_sim).
- **Метрики памяти** (H-Coherence, H-Stability) как анализ устойчивости представлений, без появления внимания/наблюдателя.
- **FAB как тонкая мембрана**: stateless, только роутинг и слияние очков, никаких политик внимания/самообучения.

---

## 1) Область и не-цели

### Входит:
- Память: 5D + hierarchical (token/sent/para/doc); операции в пространстве.
- API, валидация, обработка ошибок, health/ready/metrics.
- Индексы: построение, обновление, снапшоты, MANIFEST версий.
- Модельные артефакты: `encoder_base.mxfp16` (teacher, опц.), `encoder_mini6.mxfp4` (дистиллят, позже).
- Метрики памяти: H-Coherence, H-Stability.
- НФТ: производительность, наблюдаемость, бюджет ресурсов, безопасность.

### Не входит (строго):
- Любые политики внимания/намерений, автоперестройка контекстов.
- Онлайн-обучение/самоизменение параметров без внешнего ревью.
- Агентность/планирование, автономные действия.
- Реализация HSI/Observer.

---

## 2) Архитектура (вид сверху)

```
Client
  ↓ REST/gRPC
FastAPI / Atlas API
  ├─ /encode, /decode, /explain
  ├─ /encode_h, /decode_h, /manipulate_h
  ├─ /search (sent/para/doc, fuse=RRF|max_sim)
  └─ /health, /ready, /metrics
        ↓
FAB (membrane; stateless)
  ├─ Router (fan-out по индексам)
  ├─ Merger (нормализация + RRF/max_sim)
  └─ Manifest/Indices registry (read-only)
        ↓
Semantic Space & Indices
  ├─ HNSW (sentence/paragraph)
  ├─ FAISS IVF-PQ (document)
  └─ 5D ops + hierarchical ops
        ↓
Storage
  ├─ models/*.mxfp16, *.mxfp4
  ├─ indexes/*.hnsw, *.faiss
  └─ MANIFEST.v0_2.json
```

**Принципы:**
- FAB без состояния, без записи; все долгоживущие артефакты — вне FAB.
- Слияние результатов — строго алгоритмическое (RRF/max_sim), детерминированное.
- Внутри API — только explainable шаги и трассировка.

---

## 3) Контракты и форматы (REST, Pydantic)

### 3.1 `/encode` (5D)

**Request:**
```json
{
  "text": "string",
  "lang": "ru",
  "normalize": true
}
```

**Response:**
```json
{
  "embedding_5d": [0.1, 0.2, -0.3, 0.15, 0.4],
  "dimensions": ["A", "B", "C", "D", "E"],
  "meta": { "len": 123, "lang": "ru" }
}
```

### 3.2 `/decode`

**Request:**
```json
{
  "embedding_5d": [0.1, 0.0, 0.3, -0.2, 0.8],
  "top_k": 5
}
```

**Response:**
```json
{
  "text": "вероятный смысловой текст",
  "rationale": [
    "dimA↑ => абстрактность",
    "dimE↑ => интенсивность"
  ],
  "path": ["token1/token2"]
}
```

### 3.3 `/explain`

**Request:**
```json
{
  "embedding_5d": [0.1, 0.2, -0.3, 0.15, 0.4]
}
```

**Response:**
```json
{
  "dimensions": [
    {
      "name": "A",
      "weight": 0.42,
      "examples": ["абстракция", "концепция"]
    }
  ],
  "normalization": "L2",
  "notes": "Пространство описывает семантические оси"
}
```

### 3.4 `/encode_h` (иерархия)

**Request:**
```json
{
  "text": "Полный текст документа...",
  "levels": ["sentence", "paragraph", "document"],
  "proj_dim": 384,
  "normalize": true
}
```

**Response:**
```json
{
  "levels": {
    "sentence": [[384], [384]],
    "paragraph": [[384]],
    "document": [384]
  },
  "masks": {
    "token_to_sent": [[0, 1, 1, 0]],
    "sent_to_para": [[1, 0]],
    "para_to_doc": [[1]]
  }
}
```

### 3.5 `/decode_h`

**Request:**
```json
{
  "levels": ["sentence", "paragraph", "document"],
  "vectors": {
    "sentence": [[384]],
    "paragraph": [[384]],
    "document": [384]
  },
  "top_k": 3
}
```

**Response:**
```json
{
  "reconstructions": {
    "sentence": ["текст1", "текст2"],
    "paragraph": ["параграф1"],
    "document": "полный документ"
  },
  "path_scores": [
    {"path": "doc/para/sent", "score": 0.87}
  ]
}
```

### 3.6 `/manipulate_h`

**Request:**
```json
{
  "op": "union",
  "lhs": {"level": "sentence", "vec": [384]},
  "rhs": {"level": "paragraph", "vec": [384]},
  "top_k": 5
}
```

**Response:**
```json
{
  "result": {"level": "paragraph", "vec": [384]},
  "trace": ["normalize", "cosine", "merge"]
}
```

### 3.7 `/search` (через FAB)

**Request:**
```json
{
  "query": "что такое дисентанглмент",
  "levels": ["sentence", "paragraph", "document"],
  "top_k": 7,
  "fuse": "RRF"
}
```

**Response:**
```json
{
  "hits": [
    {
      "level": "sentence",
      "id": "s:123",
      "score": 0.83,
      "trace": {"sim": 0.83, "rank_s": 1, "rank_p": 5}
    },
    {
      "level": "document",
      "id": "d:42",
      "score": 0.79,
      "trace": {"sim": 0.79, "ivf": "cluster_42"}
    }
  ],
  "debug": {
    "per_level": {
      "sentence": [0.83, 0.81, 0.77],
      "paragraph": [0.80, 0.75],
      "document": [0.79]
    },
    "fuse_weights": {"RRF_k": 60}
  }
}
```

### 3.8 `/health`, `/ready`, `/metrics`

- **`/health`** — liveness (200 OK).
- **`/ready`** — индексы загружены, MANIFEST валиден.
- **`/metrics`** — Prometheus (латентность, QPS, hit@k, статус индексов).

---

## 4) Индексы и манифест

### Входные артефакты
- `models/encoder_base.mxfp16` (teacher, опционально).
- `models/encoder_mini6.mxfp4` (дистиллят для онлайна — в S3).
- `indexes/sent.hnsw`, `indexes/para.hnsw`, `indexes/doc.faiss`.

### Построение
- **sentence** → HNSW: M=32, efConstruction=200, efSearch=64.
- **paragraph** → HNSW: M=48, efConstruction=400, efSearch=96.
- **document** → FAISS IVF-PQ: nlist≈√N, m=16, nbits=8.

### Нормализация
- Все векторы L2-norm, similarity = dot (эквивалент косинусу).

### Манифест `MANIFEST.v0_2.json`

```json
{
  "version": "0.2",
  "git": {
    "head": "96e7fd2abc...",
    "branch": "main"
  },
  "models": [
    {
      "file": "models/encoder_base.mxfp16",
      "sha256": "abc123def456...",
      "type": "teacher"
    }
  ],
  "indices": [
    {
      "level": "sentence",
      "file": "indexes/sent.hnsw",
      "hparams": {"M": 32, "efC": 200, "efSearch": 64}
    },
    {
      "level": "paragraph",
      "file": "indexes/para.hnsw",
      "hparams": {"M": 48, "efC": 400, "efSearch": 96}
    },
    {
      "level": "document",
      "file": "indexes/doc.faiss",
      "hparams": {"nlist": 1000, "m": 16, "nbits": 8}
    }
  ],
  "created_at": "2025-10-27T12:00:00Z",
  "compat": {
    "api": "beta",
    "vector_dim": 384
  }
}
```

---

## 5) FAB (мембрана, безопасная)

- **Router**: fan-out запросов по уровням/индексам.
- **Normalizer**: выравнивание шкал очков, отбрасывание аномалий.
- **Merger**: RRF (Reciprocal Rank Fusion, k=60 по умолчанию) и/или max_sim.
- **Registry**: read-only доступ к MANIFEST и дескрипторам индексов.
- **Нет**: состояния, кешей обучения, политик внимания, авто-переконфигурации.

---

## 6) Метрики (качество памяти)

### H-Coherence (↑)
Средний косинус между соседними уровнями (token→sent, sent→para, …).

### H-Stability (↓)
Дрейф эмбеддингов при лёгких пертурбациях (пунктуация/шум).

### IR
Recall@k / nDCG@k на локальных наборах (док-внутренние пары).

### Цели приёмки β
- **H-Coherence** ≥ 0.78 (sent/para), ≥ 0.80 (para/doc).
- **H-Stability drift** ≤ 0.08.
- **Search**: median latency p50 ≤ 60 ms (GPU) / ≤ 200 ms (CPU) на top_k=7.
- **`/ready`** < 5 s холодный старт с загрузкой индексов ≤ 5M векторов.

---

## 7) Наблюдаемость и безопасность

- **Логи**: `ATLAS_LOG_LEVEL` (DEBUG|INFO), трассировка trace_id, query_id.
- **Прометей**: `atlas_api_requests_total`, `atlas_search_latency_ms`, `atlas_hits_at_k`.
- **Снапшоты индексов**: атомарное переключение (двойной путь active/next).
- **Валидатор MANIFEST**: сверка sha256, разрядность, совместимость vector_dim.
- **Роллбек**: `POST /admin/indices/rollback?to=<manifest>` (защищённый эндпоинт).
- **Нет**: онлайн-тюнинга, автоперестройки, самообучения без человек-в-лупе.

---

## 8) Производительность и форматы весов

- **Основной формат**: `.mxfp16` (teacher); квантованный: `.mxfp4` (student; S3).
- **Квантование** (позже, S3): mxfp4 per-channel, нормы/scale — fp16; ограничения:
  - Δcos ≤ 0.01 против fp16, падение IR ≤ 2 pp.

---

## 9) Приёмка (Acceptance)

Система принимается в β, если одновременно выполнено:

1. **API**: все эндпоинты проходят тесты (200/4xx корректно), схемы валидны.
2. **Индексы**: построение, загрузка, `/ready` < 5 s, MANIFEST валиден.
3. **Метрики**: H-Coherence/H-Stability — в целях; IR@k соответствует ожидаемому baseline.
4. **НФТ**: p50/p95 по латентности в целевых границах; логи/метрики — доступны.
5. **Документация**: MODEL_CARD, DATA_CARD, NFR, INTERPRETABILITY, DISENTANGLEMENT — актуальны.
6. **Безопасность**: FAB stateless, без auto-policy; снапшоты и роллбек работают.

---

## 10) План работ (эпики → задачи)

### E1. API & Контракты
- [ ] Схемы Pydantic для всех эндпоинтов
- [ ] Примеры payload'ов, валидация, 4xx/5xx стратегия
- [ ] `/search` с FAB: fan-out, нормализация, RRF/max_sim, трассировка

### E2. Индексы & MANIFEST
- [ ] Инструменты построения/апдейта индексов
- [ ] Атомарное переключение индексов (active/next)
- [ ] MANIFEST генератор/валидатор, sha256, совместимость dims

### E3. Метрики памяти
- [ ] Реализация H-Coherence/H-Stability
- [ ] Тестовые наборы, отчёт
- [ ] Прометей-метрики, дешборд

### E4. НФТ
- [ ] Логирование, rate-limits (базовые), алерты
- [ ] Cold-start, warm-paths, профилирование

### E5. Документация
- [ ] Обновление MODEL_CARD/DATA_CARD/NFR/INTERPRETABILITY
- [ ] README — секции Quick Start β, индексация, `/search`

### E6. (Опция) Нейронный S1
- [ ] Подключение encoder_base.mxfp16 (если доступен)
- [ ] Валидация нормировок и совместимости proj_384/768

### E7. Релизные артефакты
- [ ] `indexes/*.hnsw|*.faiss`, `MANIFEST.v0_2.json`
- [ ] Docker build, smoke-тесты, релиз-ноты

---

## 11) Примеры запросов (канонические)

### Search → RRF

```bash
curl -X POST http://localhost:8010/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "что такое дисентанглмент",
    "levels": ["sentence", "document"],
    "top_k": 7,
    "fuse": "RRF"
  }'
```

### Encode/Decode 5D

```bash
curl -X POST http://localhost:8010/encode \
  -H "Content-Type: application/json" \
  -d '{
    "text": "текст документа",
    "lang": "ru",
    "normalize": true
  }'

curl -X POST http://localhost:8010/decode \
  -H "Content-Type: application/json" \
  -d '{
    "embedding_5d": [0.1, 0.2, 0, 0.3, 0.4],
    "top_k": 5
  }'
```

### Hierarchical encode

```bash
curl -X POST http://localhost:8010/encode_h \
  -H "Content-Type: application/json" \
  -d '{
    "text": "полный текст документа...",
    "levels": ["sentence", "paragraph", "document"],
    "proj_dim": 384,
    "normalize": true
  }'
```

---

## 12) Ветки и выпуск

- **Рабочая ветка**: `beta/fab-membrane`.
- **Защита main**: PR-ревью + CI (линты + API/индексы smoke).
- **Тег беты**: `v0.2.0-beta` (после прохождения Acceptance).

---

## История обновлений

| Дата | Версия | Изменения |
|------|--------|-----------|
| 27.10.2025 | 0.1 | Первая версия ТЗ Atlas β |
