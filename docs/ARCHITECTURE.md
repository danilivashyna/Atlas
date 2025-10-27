# Atlas β — Архитектурная Схема Проводки

**Версия:** 0.2.0-beta  
**Статус:** Жёсткий каркас без люфтов  
**Дата:** 27 октября 2025  

---

## 🔌 6 Связок: Как всё замыкается

Каждая связка — это прямое соединение конфигов → кода → результата, без "магии".

---

### 1️⃣ Конфиги → API (Контракт)

```
src/atlas/configs/api/
├── routes.yaml        ← Источник истины для эндпоинтов
└── schemas.json       ← Источник истины для Request/Response
        ↓
    ConfigLoader
        ↓
    FastAPI app
        ├── GET /health
        ├── POST /encode
        ├── POST /decode
        ├── POST /search
        └── ... (8 endpoints всего)
```

**Механизм:**

```python
# В src/atlas/api/app.py
from src.atlas.configs import ConfigLoader

routes_cfg = ConfigLoader.get_api_routes()
schemas = ConfigLoader.get_api_schemas()

app = FastAPI()

# Динамическое построение роутов из routes.yaml
for endpoint_name, endpoint_spec in routes_cfg.items():
    route_path = endpoint_spec['path']
    route_method = endpoint_spec['method']
    timeout_ms = endpoint_spec.get('timeout_ms', 30000)
    
    # Валидация по schemas.json
    input_schema = schemas['definitions'][endpoint_spec['input']]
    output_schema = schemas['definitions'][endpoint_spec['output']]
    
    @app.route(route_path, methods=[route_method])
    async def handler(request: Pydantic.model_validate(input_schema)):
        ...
        return output_schema.validate(response)
```

**Эффект:**
- ✅ Контракт API стабилен (меняем YAML → меняется API без перекомпиляции)
- ✅ Валидация на входе/выходе (все ошибки ловятся)
- ✅ Одна версия истины (нет рассинхрона)

**Таймауты & Rate-limits:**
```yaml
# routes.yaml
defaults:
  rate_limit_qps: 1000
  rate_limit_concurrent: 100

search:
  timeout_ms: 5000      # ← Middleware читает отсюда
```

---

### 2️⃣ Конфиги → Индексы (Гиперпараметры)

```
src/atlas/configs/indices/
├── sent_hnsw.yaml     ← M=32, ef_construction=200, ef_search=64
├── para_hnsw.yaml     ← M=48, ef_construction=400, ef_search=96
└── doc_faiss.yaml     ← nlist=1000, m=16, nbits=8
        ↓
    HNSW/FAISS Builders
        ↓
    indexes/
    ├── indexes/sent.hnsw    (воспроизводимый)
    ├── indexes/para.hnsw    (одинаковый на всех стендах)
    └── indexes/doc.faiss    (deterministic)
```

**Механизм:**

```python
# src/atlas/indices/hnsw_builder.py
from src.atlas.configs import ConfigLoader

def build_sent_hnsw(vectors):
    cfg = ConfigLoader.get_index_config('sentence')
    
    index = hnswlib.Index(space='cosine', dim=cfg['vector_dim'])
    index.init_index(
        max_elements=len(vectors),
        M=cfg['hnsw']['M'],                    # ← из sent_hnsw.yaml
        ef_construction=cfg['hnsw']['ef_construction'],
        seed=cfg['hnsw']['seed']               # ← детерминизм!
    )
    index.add_items(vectors, ids)
    index.save(cfg['storage']['path_template'])
    return index
```

**Поиск использует тот же конфиг:**
```python
# src/atlas/search/searcher.py
def search_sentences(query_vec, top_k=10):
    cfg = ConfigLoader.get_index_config('sentence')
    index = hnswlib.Index(space='cosine')
    index.load_index(cfg['storage']['path_template'])
    
    labels, distances = index.knn_query(
        query_vec,
        k=top_k,
        ef=cfg['hnsw']['ef_search']            # ← из того же sent_hnsw.yaml
    )
    return labels, distances
```

**Эффект:**
- ✅ Воспроизводимость (тот же seed → тот же индекс)
- ✅ Одинаковый latency/recall на стендах (параметры жёсткие)
- ✅ Легко A/B тестировать (меняем YAML, перестраиваем индекс)

**Матрица гиперпараметров:**

| Уровень | Index Type | M/nlist | ef_construction | ef_search | Target p50 | Recall@10 |
|---------|-----------|---------|-----------------|-----------|-----------|-----------|
| sentence | HNSW | 32 | 200 | 64 | ≤15ms | ≥0.95 |
| paragraph | HNSW | 48 | 400 | 96 | ≤25ms | ≥0.93 |
| document | FAISS IVF-PQ | 1000 | 100k | 100 | ≤30ms | ≥0.90 |

---

### 3️⃣ Конфиги → Манифест (Версионирование)

```
src/atlas/configs/indices/
└── manifest_schema.json   ← JSON Schema валидатор
        ↓
MANIFEST.v0_2.json
    ├── models/
    │   ├── encoder_base.mxfp16 (SHA256: abc123...)
    │   └── (опц.) encoder_mini6.mxfp4
    ├── indices/
    │   ├── indexes/sent.hnsw (SHA256: def456...)
    │   ├── indexes/para.hnsw (SHA256: ghi789...)
    │   └── indexes/doc.faiss (SHA256: jkl012...)
    └── git/
        ├── head: "96e7fd2..."
        └── branch: "main"
```

**Механизм валидации:**

```python
# src/atlas/manifest/validator.py
from src.atlas.configs import ConfigLoader
from jsonschema import validate

def validate_manifest(manifest_dict):
    schema = ConfigLoader.get_manifest_schema()
    
    # ✅ Проверка структуры
    validate(instance=manifest_dict, schema=schema)
    
    # ✅ Проверка SHA256 (файлы не подмешаны)
    for model in manifest_dict['models']:
        file_path = model['file']
        actual_sha = compute_sha256(file_path)
        assert actual_sha == model['sha256'], \
            f"Model {file_path} checksum mismatch!"
    
    for index in manifest_dict['indices']:
        file_path = index['file']
        actual_sha = compute_sha256(file_path)
        assert actual_sha == index['sha256'], \
            f"Index {file_path} checksum mismatch!"
    
    # ✅ Проверка совместимости vector_dim
    assert manifest_dict['compatibility']['vector_dim'] == 384, \
        "Only 384-dim vectors supported!"
    
    return True
```

**Эффект:**
- ✅ Нельзя "подсунуть" несогласованные веса/индексы
- ✅ Каждый артефакт прозрачно отслеживается (SHA256)
- ✅ Версионирование через git (head, branch, tag)

---

### 4️⃣ FAB-мембрана → Поиск (Бесстатная маршрутизация)

```
request (/search)
    ↓
ConfigLoader.get_api_routes()  ← какие уровни искать?
ConfigLoader.get_all_index_configs()  ← как искать?
    ↓
FAB Router (fan-out на 3 индекса параллельно)
    ├─→ sent.hnsw   + ef_search=64
    ├─→ para.hnsw   + ef_search=96
    └─→ doc.faiss   + nprobe=100
    ↓
Per-level scores: [0.85, 0.81, 0.77]  (sentence level)
                  [0.80, 0.75]        (paragraph level)
                  [0.79]              (document level)
    ↓
FAB Merger (детерминированное слияние)
    ├─ RRF (Reciprocal Rank Fusion, k=60)  OR
    └─ max_sim (максимальное сходство)
    ↓
Final fused scores: [0.84, 0.80, 0.78, 0.75, ...]
    ↓
response (отсортировано, trace с рангами)
```

**Механизм FAB:**

```python
# src/atlas/fab/router.py
from src.atlas.configs import ConfigLoader

def search_multi_level(query_text: str, levels: List[str], fuse_method: str = "RRF"):
    cfg = ConfigLoader.get_api_routes()
    index_cfgs = ConfigLoader.get_all_index_configs()
    
    # ✅ Валидация уровней из route.yaml
    allowed_levels = cfg['search']['levels']
    levels = [l for l in levels if l in allowed_levels]
    
    # Параллельный поиск
    results_per_level = {}
    with ThreadPoolExecutor() as executor:
        futures = {}
        
        for level in levels:
            index_cfg = index_cfgs[level]
            future = executor.submit(
                search_level,
                query_text,
                level,
                index_cfg
            )
            futures[level] = future
        
        for level, future in futures.items():
            results_per_level[level] = future.result()
    
    # Детерминированное слияние
    if fuse_method == "RRF":
        from src.atlas.fab.merger import rrf_fusion
        fused = rrf_fusion(results_per_level, k=60)  # ← из конфига
    elif fuse_method == "max_sim":
        from src.atlas.fab.merger import max_sim_fusion
        fused = max_sim_fusion(results_per_level)
    
    return fused
```

**Свойства FAB:**

| Свойство | Значение | Почему |
|----------|----------|--------|
| Состояние | None | Только поиск, никакой памяти |
| Обучение | Запрещено | Только алгоритмическое слияние |
| Политики | Запрещены | Нет внимания, интенций, самоизменений |
| Детерминизм | ✅ Да | RRF/max_sim — чистые функции |
| HSI граница | ✅ Не переходит | Только память, не разум |

**Эффект:**
- ✅ Тонкий транспорт без неожиданных побочных эффектов
- ✅ Одинаковый результат при одинаковых индексах
- ✅ Полная трассировка (debug info в response)

---

### 5️⃣ Метрики → Приёмка (Единая шкала качества)

```
src/atlas/configs/metrics/h_metrics.yaml
    ├── h_coherence targets:
    │   ├── sent_to_para: 0.78
    │   └── para_to_doc: 0.80
    ├── h_stability targets:
    │   └── max_drift: 0.08
    ├── ir_metrics targets:
    │   ├── recall@10: [0.85, 0.88, 0.90]
    │   └── ndcg@10: [0.82, 0.85, 0.88]
    └── latency targets:
        ├── GPU p50: 60ms
        └── CPU p50: 200ms
        ↓
    Применяются в:
    ├── Unit tests (tests/test_metrics_beta.py)
    ├── CI pipeline (проверка перед push)
    ├── Production monitoring (Prometheus alerts)
    └── Sprint acceptance (все ✅ → beta ready)
```

**Механизм измерения:**

```python
# tests/test_metrics_beta.py
from src.atlas.configs import ConfigLoader

def test_h_coherence():
    metrics_cfg = ConfigLoader.get_metrics_config()
    targets = ConfigLoader.get_h_coherence_targets()
    
    # Измеряем coherence на тестовом наборе
    coherence_score = measure_h_coherence(test_vectors)
    
    # Сравниваем с конфигом
    assert coherence_score >= targets['sent_to_para'], \
        f"H-Coherence sent→para: {coherence_score} < {targets['sent_to_para']}"

def test_search_latency():
    metrics_cfg = ConfigLoader.get_metrics_config()
    latency_targets = ConfigLoader.get_latency_targets(device='gpu')
    
    latencies = []
    for query in test_queries:
        start = time.time()
        search(query)
        latencies.append((time.time() - start) * 1000)  # ms
    
    p50 = np.percentile(latencies, 50)
    assert p50 <= latency_targets['search']['p50_ms'], \
        f"Latency p50: {p50}ms > {latency_targets['search']['p50_ms']}ms"
```

**Prometheus экспорт:**

```python
# src/atlas/metrics/exporter.py
from prometheus_client import Gauge, Counter, Histogram
from src.atlas.configs import ConfigLoader

metrics_cfg = ConfigLoader.get_metrics_config()

# Динамический экспорт из h_metrics.yaml
h_coherence_sent_para = Gauge(
    'atlas_h_coherence_sent_para',
    'H-Coherence: sentence to paragraph',
    multiprocess_mode='livesum'
)

h_stability_drift = Gauge(
    'atlas_h_stability_drift',
    'H-Stability: max drift under perturbations',
    multiprocess_mode='livesum'
)

search_latency = Histogram(
    'atlas_search_latency_ms',
    'Search query latency (ms)',
    buckets=metrics_cfg['prometheus']['metrics']['atlas_search_latency_ms']['buckets']
)
```

**Эффект:**
- ✅ Единая шкала качества (dev, CI, prod — одни метрики)
- ✅ Одна "кнопка" приёмки (все checks из h_metrics.yaml)
- ✅ Автоматические алерты (Prometheus rules)

---

### 6️⃣ Модели/Веса → Индексы → API (Жёсткая связность)

```
models/
├── encoder_base.mxfp16  (teacher, опц.)
│   └── SHA256: abc123def456...
└── encoder_mini6.mxfp4  (student, позже)
    └── SHA256: ghi789jkl012...
        ↓
        ├─→ используется для /encode, /encode_h
        └─→ используется для обновления индексов
        ↓
MANIFEST.v0_2.json
├── models[0]:
│   ├── file: "models/encoder_base.mxfp16"
│   ├── sha256: "abc123def456..."
│   └── type: "teacher"
├── indices[0]:
│   ├── file: "indexes/sent.hnsw"
│   ├── sha256: "def456..."
│   └── hparams: {M: 32, efC: 200, ...}
        ↓
        (Валидируется MANIFEST валидатором)
        ↓
API запуск:
├── 1. Загружены ли all models → /ready
├── 2. Загружены ли all indices → /ready
├── 3. Совпадают ли SHA256 → /ready
└── 4. Совместимы ли vector_dim → /ready
        ↓
        ✅ Если всё OK → API зелёный
        ❌ Если рассинхрон → API красный, отказ
```

**Механизм в коде:**

```python
# src/atlas/startup.py
from src.atlas.configs import ConfigLoader
from src.atlas.manifest import ManifestValidator

async def app_startup():
    """Проверка при запуске API"""
    
    # 1. Загрузить MANIFEST
    with open('MANIFEST.v0_2.json') as f:
        manifest = json.load(f)
    
    # 2. Валидировать против schema
    ManifestValidator.validate(manifest)  # ← использует manifest_schema.json
    
    # 3. Загрузить модели
    for model_spec in manifest['models']:
        model_file = model_spec['file']
        
        # Проверить SHA256
        actual_sha = compute_sha256(model_file)
        assert actual_sha == model_spec['sha256']
        
        # Загрузить в память
        load_model(model_file)
    
    # 4. Загрузить индексы
    for index_spec in manifest['indices']:
        index_file = index_spec['file']
        
        # Проверить SHA256
        actual_sha = compute_sha256(index_file)
        assert actual_sha == index_spec['sha256']
        
        # Загрузить в память
        load_index(index_spec['level'], index_file)
    
    # 5. Установить /ready в True
    app.state.ready = True
    logger.info(f"✅ API ready. Manifest: {manifest['version']}, "
                f"Git: {manifest['git']['head']}, "
                f"Vectors: {manifest['compatibility']['vector_dim']}-dim")
```

**Эффект:**
- ✅ Жёсткая связность "веса ↔ индекс ↔ контракт"
- ✅ Нельзя запустить API с несогласованными артефактами
- ✅ Каждый запрос знает, откуда данные (trace через MANIFEST)

---

## 🔄 Потоки: Что происходит на запросе

### Поток 1: `/search` (multi-level)

```
curl -X POST /api/v1/search -d '{"query": "...", "levels": ["sentence", "document"], "fuse": "RRF"}'

1. Приходит request
   ↓
2. Pydantic валидация (из schemas.json → SearchRequest)
   ✓ query: string ✓ levels: ["sentence", "document"] ✓ fuse: "RRF"
   ↓
3. Middleware: rate-limit check (из routes.yaml:defaults:rate_limit_qps)
   ✓ QPS < 1000 → proceed ✓ concurrent < 100 → proceed
   ↓
4. FAB Router (читает routes.yaml + indices/*.yaml):
   
   a) Encode query → 384-dim vector (encoder_base.mxfp16)
   
   b) Параллельный поиск (ThreadPool):
      - search_level('sentence', 10, ef_search=64) → scores: [0.85, 0.81, 0.79, ...]
      - search_level('document', 10, nprobe=100) → scores: [0.79, 0.75, ...]
   
   c) Слияние (RRF, k=60):
      - rank_sent = [1, 2, 3, ...]  →  rrf_sent = [1/(1+60), 1/(2+60), ...]
      - rank_doc = [1, 2]           →  rrf_doc = [1/(1+60), 1/(2+60)]
      - fused = rrf_sent + rrf_doc
      - sort(fused) descending
   
   d) Финальное слияние (по score + иерархия)
      Result: [
        {"level": "sentence", "id": "s:1", "score": 0.84, "trace": {...}},
        {"level": "document", "id": "d:1", "score": 0.82, "trace": {...}},
        ...
      ]
   ↓
5. Pydantic валидация output (из schemas.json → SearchResponse)
   ✓ hits: [{level, id, score, trace}, ...] ✓ query_time_ms: 58
   ↓
6. Возврат response (JSON)
   ↓
7. Prometheus metric: atlas_search_latency_ms histogram.observe(58)
```

### Поток 2: `/encode_h` (hierarchical)

```
curl -X POST /api/v1/encode_h -d '{"text": "...", "levels": ["sentence", "paragraph", "document"]}'

1. Приходит request
   ↓
2. Pydantic валидация (EncodeHierarchicalRequest)
   ✓ text: string ✓ levels: [...] ✓ proj_dim: 384
   ↓
3. Encoder (encoder_base.mxfp16 или rule-based fallback):
   
   a) Разбиение на уровни (text → tokens → sentences → paragraphs → document)
   
   b) Кодирование каждого уровня:
      - Tokens → embeddings (опционально, если S1 доступна)
      - Sentences → 384-dim вектора (из encoder)
      - Paragraphs → 384-dim вектора (pool sentences или encoder)
      - Document → 384-dim вектор (pool paragraphs)
   
   c) Нормализация (L2-norm каждого уровня)
   
   d) Создание масок (token→sent, sent→para, para→doc):
      masks = {
        "token_to_sent": [[0, 1, 1, 0, ...], ...],  # какие токены в какие sent
        "sent_to_para": [[1, 0, ...], ...],         # какие sent в какие para
        "para_to_doc": [[1, ...]]                   # какие para в doc
      }
   ↓
4. Pydantic валидация output (EncodeHierarchicalResponse)
   ✓ levels: {sentence: [...], paragraph: [...], document: [...]}
   ✓ masks: {...}
   ↓
5. (Опционально) Запись в индексы (если апдейт):
   - Добавить sentences в sent.hnsw (используя sent_hnsw.yaml params)
   - Добавить paragraphs в para.hnsw (используя para_hnsw.yaml params)
   - Добавить document в doc.faiss (используя doc_faiss.yaml params)
   ↓
6. Возврат response
```

### Поток 3: `/encode` (5D basic)

```
curl -X POST /api/v1/encode -d '{"text": "...", "lang": "ru"}'

1. Валидация (EncodeRequest)
   ↓
2. Rule-based 5D кодирование:
   - Разбить текст на tokens/sentences
   - Вычислить 5 признаков (A, B, C, D, E):
     A: abstraction (как абстрактно?)
     B: sentiment (настроение?)
     C: complexity (сложность?)
     D: specificity (специфичность?)
     E: intensity (интенсивность?)
   - Нормализовать L2
   ↓
3. Валидация output (EncodeResponse)
   ✓ embedding_5d: [0.1, 0.2, -0.3, 0.15, 0.4]
   ✓ dimensions: ["A", "B", "C", "D", "E"]
   ✓ meta: {len: 42, lang: "ru", normalized: true}
   ↓
4. Возврат response
```

---

## 🔒 Границы Безопасности (Никакого HSI)

### Запрещено (🚫)

| Что | Почему | Как блокируем |
|-----|--------|---------------|
| Политики внимания | Ведут в HSI (Observer) | FAB stateless, только RRF/max_sim |
| Online learning | Параметры меняются без ревью | No gradient updates, только конфиги |
| Auto-reconfig индексов | Скрытое поведение | Меняем .yaml → перестраиваем → новый MANIFEST |
| Скрытое состояние в FAB | Неопредсказуемо | FAB = чистые функции (query → results) |
| Вывод интенций | "Помним, что хотел пользователь" | Только стателесный поиск |

### Разрешено (✅)

| Что | Зачем | Как |
|-----|-------|------|
| Детерминированное слияние | Воспроизводимость | RRF/max_sim алгоритмы |
| Версионирование артефактов | Трассируемость | MANIFEST + SHA256 |
| Обновление конфигов | Улучшение качества | PR + CI + ревью → новый MANIFEST |
| Мониторинг метрик | Контроль качества | Prometheus → alerts из h_metrics.yaml |
| Фан-аут поиска | Параллелизм | Router распределяет на 3 индекса |

### Валидаторы (Предохранители)

```python
# 1. Валидатор schemas.json
#    → Все Request/Response должны быть в конфиге
#    → Нельзя "тайком" добавить поле

# 2. Валидатор manifest_schema.json
#    → Все модели/индексы описаны
#    → SHA256 совпадают с файлами
#    → Никакого рассинхрона

# 3. Валидатор indices/*.yaml
#    → Диапазоны параметров (M ∈ [16, 64], ef ∈ [100, 500], ...)
#    → Целостность гиперпараметров

# 4. Валидатор h_metrics.yaml
#    → Пороги качества не понижаются
#    → Latency targets реалистичны

# 5. Валидатор FAB
#    → Нет состояния (stateless check)
#    → Только RRF/max_sim (no attention)
#    → Детерминизм (same inputs → same outputs)
```

---

## ⚡ Быстрые Проверки (На Старт)

### 1. Валидность конфигов

```bash
# Проверить schemas.json
python -c "
import json
from jsonschema import Draft7Validator

schemas = json.load(open('src/atlas/configs/api/schemas.json'))
Draft7Validator.check_schema(schemas)
print('✅ schemas.json valid')
"

# Проверить manifest_schema.json
python -c "
import json
from jsonschema import Draft7Validator

manifest_schema = json.load(open('src/atlas/configs/indices/manifest_schema.json'))
Draft7Validator.check_schema(manifest_schema)
print('✅ manifest_schema.json valid')
"

# Проверить indices/*.yaml диапазоны
python -c "
import yaml

sent_cfg = yaml.safe_load(open('src/atlas/configs/indices/sent_hnsw.yaml'))
assert 16 <= sent_cfg['hnsw']['M'] <= 64, 'M out of range'
assert 100 <= sent_cfg['hnsw']['ef_construction'] <= 500, 'ef_construction out of range'
print('✅ indices configs valid')
"
```

### 2. Smoke /search

```bash
# Поднять API
python -m src.atlas.api.app

# В отдельном терминале:
curl -X POST http://localhost:8010/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "тест",
    "levels": ["sentence", "document"],
    "fuse": "RRF"
  }'

# Проверить:
# - response.hits не пусто
# - trace содержит ranks и scores
# - latency < 60ms (GPU) / 200ms (CPU)
```

### 3. Валидация MANIFEST

```bash
python -c "
import json
from src.atlas.manifest import ManifestValidator

manifest = json.load(open('MANIFEST.v0_2.json'))
ManifestValidator.validate(manifest)
print('✅ MANIFEST.v0_2.json valid and consistent')
"
```

---

## 📊 Итоговая Таблица: 6 Связок + Границы

| № | Связь | Конфиг | Код | Артефакт | Валидация |
|---|-------|--------|-----|----------|-----------|
| 1 | routes → API | `routes.yaml` | ConfigLoader → FastAPI | API роуты | /health → 200 |
| 2 | indices cfg → builders | `{sent,para,doc}.yaml` | HNSW/FAISS builders | `.hnsw/.faiss` файлы | recall@10 ≥ target |
| 3 | manifest schema → versioning | `manifest_schema.json` | ManifestValidator | MANIFEST.v0_2.json | SHA256 match |
| 4 | FAB → search | `routes.yaml` + `indices.yaml` | Router + Merger | fused scores | p50 ≤ 60ms (GPU) |
| 5 | metrics → acceptance | `h_metrics.yaml` | Test suite | test results | все checks ✅ |
| 6 | models → indices → API | MANIFEST ref | LoaderFan-out | bound artifacts | /ready check |

---

## 🎯 Почему это стабильно даже при "дрожи связи"

```
Сценарий: Кто-то вручную подменил индекс на старый
                     ↓
1. MANIFEST содержит SHA256 старого индекса
2. При запуске API: compute_sha256(индекс) ≠ MANIFEST.sha256
3. ManifestValidator.validate() выбросит exception
4. API не поднимается → /ready = False
5. Оператор замечает красный статус → откатывает изменение
                     ↓
                  ✅ Потенциальный баг не заходит в production
```

```
Сценарий: Разработчик забыл обновить параметр в routes.yaml
                     ↓
1. Меняет rate_limit_qps: 1000 → 10
2. ConfigLoader.get_api_routes() читает новое значение
3. Middleware применяет новый лимит
4. CI smoke-test: 100 параллельных запросов → 90 отказаны (429)
5. Тест FALLS → PR не мержится
                     ↓
                  ✅ Рассинхрон поймался в CI
```

```
Сценарий: Индекс построен с неправильным M, но файл файлу назвается
                     ↓
1. Builder читает M=32 из sent_hnsw.yaml
2. hnswlib.Index(M=32, ...) создаёт индекс с M=32
3. Но если кто-то подменил sent_hnsw.yaml на M=16 (ошибка)
4. Новый индекс построен с M=16
5. Тест search latency FALLS (slow → p50 > target)
6. Test suite из h_metrics.yaml блокирует
                     ↓
                  ✅ Деградация качества поймана немедленно
```

---

## 📋 Следующие Шаги (Минимальный План)

### E1: API & Контракты
- [ ] Сгенерить Pydantic-классы из `schemas.json` (адаптер-слой)
- [ ] Собрать FastAPI роуты из `routes.yaml` (middleware: CORS, rate-limit)
- [ ] Smoke-тест: `/health`, `/encode`, `/search` (mock-индексы)

### E2: Индексы & MANIFEST
- [ ] Builders HNSW/FAISS читают `{sent,para,doc}.yaml`
- [ ] Генератор `MANIFEST.v0_2.json` + валидатор
- [ ] Тесты recall/latency (синтетика) vs `h_metrics.yaml` пороги

### E3: Метрики
- [ ] H-Coherence/H-Stability вычислители
- [ ] Prometheus экспорт (имена из `h_metrics.yaml`)
- [ ] Тестовые датасеты для измерения

---

## 🔗 Ссылки

- **TZ:** `docs/TZ_ATLAS_BETA.md`
- **Задачи:** `docs/ATLAS_BETA_TASKS.md`
- **Статус:** `docs/ATLAS_BETA_DEVELOPMENT_STATUS.md`
- **Конфиги:** `src/atlas/configs/`
- **Этот файл:** `docs/ARCHITECTURE.md`

---

**Итог:** Жёсткий каркас без люфтов. Каждая связка — это прямое соединение конфиг → код → результат. Валидаторы ловят рассинхроны. FAB остаётся бесстатным. Никакого HSI. 🚀
