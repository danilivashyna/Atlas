# Атлас — Панель управления смыслом

**Atlas - Semantic Space Control Panel**: Интерфейс между абстрактным смыслом и конкретной формой.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: AGPL v3 / Commercial](https://img.shields.io/badge/License-AGPL%20v3%20%2F%20Commercial-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-301%20passing-brightgreen.svg)]()
[![E4 GA](https://img.shields.io/badge/E4%20Homeostasis-GA%20Ready-success.svg)]()
[![FAB v0.1](https://img.shields.io/badge/FAB-v0.1%20Shadow-blue.svg)]()
[![API](https://img.shields.io/badge/API-FastAPI-009688.svg)]()
[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF.svg)](.github/workflows/e4-ga-validation.yml)

---

## Что такое Atlas

**Atlas — когнитивная карта знаний**: он превращает хаос данных в связную структуру и помогает находить не просто ответы, а причинно-смысловые связи между идеями.

Atlas — это слой смысловой навигации поверх ваших данных: узлы, связи, приоритеты и актуальность во времени. Он ранжирует пути через знания, ускоряет поиск «по смыслу» и даёт API, пригодное для продуктов и автоматизаций.

### Как это работает (без жаргона)

- **Узлы (Nodes)** — «точки» памяти: путь, название, вес важности, короткий вектор признаков, родитель.
- **Навигатор (PathRouter)** — оценивает, через какие узлы идти: близость по смыслу + важность + живость ветки + приоритет пути.
- **Ускоритель (ANN)** — быстро подбрасывает ближайшие по смыслу кандидаты, чтобы не перебирать всё.
- **Ткань связей (Reticulum)** — связи «узел → контент» с версиями и убыванием веса по давности (свежим — больше доверия).
- **Самонаблюдение (Mensum)** — метрики и логи для понимания, что происходит (Prometheus, лейблы, счётчики, гистограммы).

### Примеры в деле

- **«Найти точные выдержки по теме Х и не упустить близкие по смыслу материалы.»** — Atlas ранжирует результаты: главное в начале, контекстуально близкое — рядом.
- **«Собрать актуальную шпаргалку по теме из свежих источников, а старое оставить в фоне.»** — Связи на ветках теряют вес со временем, свежее получает больше приоритета.
- **«Подсветить, почему именно эти материалы попали в ответ: путь через узлы виден и воспроизводим.»** — Каждый маршрут можно проследить и объяснить.

> **Atlas. Видеть связи. Доставлять ответы.**

---

## 📜 Лицензирование (Dual License)

Atlas распространяется под **двойной лицензией**, обеспечивая как свободное использование, так и коммерческую гибкость:

| Лицензия | Для | Права | Обязательства |
|----------|-----|-------|--------------|
| **AGPLv3** (Open Source) | Открытые проекты | ✅ Свободное использование, модификация, распространение | ⚠️ Исходники должны быть открыты, copyleft |
| **Commercial** | Проприетарные проекты | ✅ Закрытый исходник, использование в SaaS/proprietary | 💰 Коммерческая лицензия требуется |

### 🔗 Документы

- **Open Source лицензия**: [LICENSE](LICENSE) — полный текст AGPLv3
- **Commercial лицензия**: [COMMERCIAL_LICENSE.md](COMMERCIAL_LICENSE.md) — соглашение для коммерческого использования
- **CLA (Contributor License Agreement)**: [CLA.md](CLA.md) — соглашение для контрибьюторов

### 💬 Контакт

Для лицензирования или вопросов по коммерческому использованию:
📧 **[danilivashyna@gmail.com](mailto:danilivashyna@gmail.com)**

---

**Примечание**: Все контрибуции автоматически распределяются под **Danil Ivashyna**, который сохраняет право перелицензирования под любыми терминами (включая коммерческие).

## 📊 Статус разработки (v0.2.0 — E4 GA)

| Компонент | Статус | Детали |
|-----------|--------|--------|
| **Ядро** | | |
| ├─ Encoder (rule-based) | ✅ Готов | Простой эвристический энкодер |
| ├─ Decoder (interpretable) | ✅ Готов | Декодирование с объяснениями |
| ├─ Semantic Space | ✅ Готов | 5D пространство операций |
| ├─ Dimensions | ✅ Готов | Интерпретация измерений |
| ├─ Hierarchical Encoder | ✅ Готов | Иерархическое кодирование |
| ├─ Hierarchical Decoder | ✅ Готов | Декодирование по путям |
| └─ Hierarchical API | ✅ Готов | /encode_h, /decode_h, /manipulate_h |
| **API (E1)** | | |
| ├─ REST API (FastAPI) | ✅ Готов | /encode, /decode, /explain |
| ├─ Health checks | ✅ Готов | /health, /ready, /metrics |
| ├─ Request validation | ✅ Готов | Pydantic models |
| ├─ FAB Router | ✅ Готов | Grammar layer routing |
| └─ Error handling | ✅ Готов | Graceful degradation |
| **Index Builders (E2)** | | |
| ├─ HNSW Builder | ✅ Готов | M=32, ef_construction=200 |
| ├─ FAISS IVF-PQ Builder | ✅ Готов | nlist=1000, m=16, nbits=8 |
| ├─ MANIFEST Generator | ✅ Готов | Git metadata + SHA256 |
| └─ Index Loading | ✅ Готов | Startup integrity checks |
| **Metrics (E3)** | | |
| ├─ H-Coherence | ✅ Готов | sent→para ≥0.78, para→doc ≥0.80 |
| ├─ H-Stability | ✅ Готов | drift monitoring (3%, 7%, 15% noise) |
| └─ Prometheus Export | ✅ Готов | /api/v1/metrics endpoint |
| **Homeostasis (E4)** ⭐ **NEW** | | |
| ├─ E4.1 Policy Engine | ✅ GA Ready | 7 YAML policies, 18 tests |
| ├─ E4.2 Decision Engine | ✅ GA Ready | Anti-flapping, rate limiting, 11 tests |
| ├─ E4.3 Action Adapters | ✅ GA Ready | 6 action types, dry-run mode, 16 tests |
| ├─ E4.5 Audit Logger | ✅ GA Ready | JSONL WAL, query filters, 13 tests |
| ├─ E4.4 Snapshot & Rollback | ✅ GA Ready | <1s rollback (≤30s SLO), 14 tests |
| ├─ E4.8 Homeostasis Metrics | ✅ GA Ready | Prometheus export, 7 tests |
| ├─ E4.7 API Routes | ✅ GA Ready | 5 endpoints, 20 tests (13+7) |
| └─ E4.6 Sleep & Consolidation | ✅ GA Ready | Defrag, compression, 13 tests |
| **FAB Integration (v0.1)** ⭐ **NEW** | | |
| ├─ Shadow Mode | ✅ Active | Read-only, dry_run=true, validation |
| ├─ FAB Schemas | ✅ Готов | 13 Pydantic models, JSON Schema v0.1 |
| ├─ FAB Routes | ✅ Готов | 4 REST endpoints (/push, /pull, /decide, /act) |
| ├─ Backpressure | ✅ Готов | Token bucket (ok/slow/reject) |
| ├─ FAB Tests | ✅ 11 тестов | All Shadow mode validation passing |
| ├─ E4 Integration | ✅ Готов | Policy decisions, action proxies |
| ├─ Mirroring Mode | 🔄 Planned | Write-through to FAB cache + E2 indices |
| └─ Cutover Mode | ⏳ Planned | Enable actions with SLO monitors |
| **Testing** | | |
| ├─ Unit tests | ✅ 301 тестов | E1-E4 + FAB full coverage |
| ├─ E4 Test Suite | ✅ 112 тестов | Homeostasis components (100% pass) |
| ├─ FAB Test Suite | ✅ 11 тестов | Shadow mode validation (100% pass) |
| ├─ Golden samples | ✅ 16 тестов | Регрессионные тесты |
| ├─ API tests | ✅ 20 тестов | Integration tests |
| └─ Coverage | ✅ > 80% | Основной функционал + E4 |
| **CI/CD** | | |
| ├─ E4 GA Validation | ✅ Готов | GitHub Actions workflow |
| ├─ SLO Monitoring | ✅ Готов | Automated compliance checks |
| └─ Coverage Reports | ✅ Готов | Codecov integration |
| **Документация** | | |
| ├─ README | ✅ Готов | Основная документация |
| ├─ E4 GA Validation Report | ✅ Готов | 112 tests, SLO compliance |
| ├─ PUSH_READY | ✅ Готов | Merge checklist E1-E4 |
| ├─ CONTRIBUTING | ✅ Готов | Гайд для контрибуторов |
| ├─ MODEL_CARD | ✅ Готов | Описание модели |
| ├─ NFR | ✅ Готов | Нефункц. требования |
| ├─ DATA_CARD | ✅ Готов | Описание данных |
| ├─ DISENTANGLEMENT | ✅ Готов | Методология разделения |
| └─ INTERPRETABILITY | ✅ Готов | Метрики интерпретируемости |
| **Deployment** | | |
| ├─ Docker | ✅ Готов | Dockerfile + compose |
| ├─ CLI | ✅ Готов | atlas command |
| └─ Python package | ✅ Готов | pip install |
| **Запланировано (v0.3+)** | | |
| ├─ Memory Persistence | 🔄 В плане | PostgreSQL + Redis |
| ├─ Action Executor Impl | 🔄 В плане | Real rebuild/reembed |
| ├─ Policy Auto-Tuning | 🔄 В плане | Success rate feedback |
| ├─ Neural encoder | 🔄 В плане | BERT-based |
| ├─ Neural decoder | 🔄 В плане | Transformer |
| ├─ Disentanglement training | 🔄 В плане | β-TC-VAE |
| └─ Human evaluation | 🔄 В плане | Аннотация |

**Легенда**: ✅ Готово | 🔄 В разработке | ⏳ Запланировано

### 🎯 E4 Homeostasis (OODA Loop)

Atlas теперь обладает **автономным циклом самокоррекции**:

```
E3 (Observe)     → Метрики: h_coherence, h_stability
    ↓
E4.1 (Orient)    → Политики: 7 YAML триггеров
    ↓
E4.2 (Decide)    → Решения: anti-flapping, rate-limits
    ↓
E4.3 (Act)       → Действия: rebuild_shard, reembed_batch
    ↓
E4.5 (Reflect)   → Аудит: JSONL WAL
    ↓
E4.8 (Monitor)   → Prometheus: 4 метрики homeostasis
    ↓
E4.4 (Safety)    → Snapshots: rollback <1s (≤30s SLO)
    ↓
E4.7 (Control)   → API: 5 endpoints для ручного управления
    ↓
E4.6 (Maintain)  → Sleep: nightly defrag + compression
```

**SLO Validation:**
- ✅ Rollback Time: <1s (target ≤30s) — **33x faster**
- ✅ Tests: 112/112 passing (100%)
- ✅ API Routes: 5/5 functional

[Подробный отчёт GA Validation →](E4_GA_VALIDATION_REPORT.md)

---

### 🔗 FAB Integration v0.1 (Shadow Mode)

**FAB (Fractal Associative Bus)** — контекстная шина над E1-E4, объединяющая глобальные (FABᴳ) и стрим-окна (FABˢ) для унифицированного управления контекстом.

**Phased Rollout (текущее состояние: Phase 1 - Shadow):**

```
Phase 1 (Shadow) ← СЕЙЧАС
    ↓
    ├─ dry_run=true (все маршруты)
    ├─ Валидация JSON Schema v0.1
    ├─ Backpressure monitoring (ok|slow|reject)
    └─ Metrics collection (готовность к Phase 2)
    
Phase 2 (Mirroring) ← СЛЕДУЮЩИЙ
    ↓
    ├─ Write-through to FAB cache
    ├─ E2 index updates (HNSW/FAISS)
    └─ Merged context view (E2 + FAB)
    
Phase 3 (Cutover) ← БУДУЩЕЕ
    ↓
    ├─ Enable E4 actions
    ├─ Rate limits + SLO guards
    └─ Full production traffic
```

**FAB REST API (v0.1):**

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/api/v1/fab/context/push` | POST | Push context window (backpressure: ok/slow/reject) | ✅ Shadow |
| `/api/v1/fab/context/pull` | GET | Pull merged context (E2 + FAB overlays) | ✅ Shadow (empty) |
| `/api/v1/fab/decide` | POST | E4.1/E4.2 policy decisions | ✅ Shadow (mock) |
| `/api/v1/fab/act/{action_type}` | POST | E4.3 action execution | ✅ Shadow (dry_run) |

**JSON Schema v0.1:**
```json
{
  "fab_version": "0.1",
  "window": {"type": "global|stream", "id": "uuid", "ts": "ISO8601"},
  "tokens": [{"t": "text", "w": 0.0-1.0, "role": "system|user|agent"}],
  "vectors": [{"id": "str", "dim": 384, "norm": 1.0, "ts": "ISO8601"}],
  "links": [{"src": "id", "dst": "id", "w": 0.0-1.0, "kind": "semantic|temporal|causal"}],
  "meta": {
    "topic": "str",
    "locale": "en-US",
    "coherence": 0.0-1.0,  // E3 metric
    "stability": 0.0-1.0   // E3 metric
  }
}
```

**Backpressure/QoS:**
- **OK**: <2000 tokens → `X-FAB-Backpressure: ok`
- **SLOW**: 2000-5000 tokens → `X-FAB-Backpressure: slow`
- **REJECT**: >5000 tokens → `X-FAB-Backpressure: reject`, `Retry-After: 60`

**E4 Integration:**
- E4.1 Policy → FAB events (coherence_degradation, stability_drift)
- E4.2 Decision → Anti-flapping (300s cooldown)
- E4.3 Actions → FAB-triggered repairs (rebuild_shard, reembed_batch)
- E4.4 Snapshots → FAB cache rotation + manifest
- E4.6 Sleep → Nightly FAB cleanup + consolidation

**Tests:**
- ✅ 11/11 tests passing (1.28s)
- Coverage: Push (4), Pull (2), Decide (2), Act (2), Integration (1)
- Validation: Backpressure thresholds, dry_run enforcement, schema compliance

[Полная спецификация FAB →](docs/AURIS_FAB_Integration_Plan_v0.1.txt)

---

## ⚡ Quick Start

### Option 1: Python (Local Development)
```bash
# Clone and enter directory
git clone https://github.com/danilivashyna/Atlas.git
cd Atlas

# Create virtual environment and install
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate
pip install -e .

# Run API server
ATLAS_LOG_LEVEL=DEBUG uvicorn src.atlas.api.app:app --reload --port 8010

# Visit: http://localhost:8010/docs
```

### Option 2: Docker (Containers)
```bash
# Build image
docker build -t atlas:latest .

# Run container
docker run -p 8010:8010 \\
  -e ATLAS_LOG_LEVEL=INFO \\
  atlas:latest

# Visit: http://localhost:8010/docs
```

### Option 3: Makefile (All-in-one)
```bash
make install    # Setup venv + dependencies
make run        # Start server with debug logging
make test       # Run test suite
make docker     # Build Docker image
```

### 📝 Example API Calls

**Route text to semantic space:**
```bash
curl -X POST http://localhost:8010/route \\
  -H "Content-Type: application/json" \\
  -d '{"text":"What is consciousness?", "top_k":5}'
```

**Get recent Reticulum links with decay:**
```bash
curl -X POST http://localhost:8010/reticulum/recent \\
  -H "Content-Type: application/json" \\
  -d '{"top_k":10, "lambda_per_day":0.1}'
```

**View metrics:**
```bash
curl http://localhost:8010/metrics/prom | grep "orbis_mens_"
```


## 🚀 Установка

```bash
# Клонировать репозиторий
git clone https://github.com/danilivashyna/Atlas.git
cd Atlas

# Установить зависимости
pip install -r requirements.txt

# Установить пакет
pip install -e .

# Для разработки (опционально)
# See: LOCAL_SETUP_COMPLETE.md for full dev guide
make setup    # Create venv
make dev      # Install dev dependencies
make test     # Run test suite
make api      # Start API server (http://localhost:8000/docs)
```

### Dev Setup для v0.2 (Hierarchical)

Полный гайд локальной разработки: **[LOCAL_SETUP_COMPLETE.md](LOCAL_SETUP_COMPLETE.md)**

```bash
# 1. Клонировать и перейти в директорию
git clone https://github.com/danilivashyna/Atlas.git
cd Atlas

# 2. Создать и активировать venv
python -m venv .venv
source .venv/bin/activate  # или .venv\Scripts\activate на Windows

# 3. Установить зависимости
pip install -U pip wheel
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cpu

# 4. Установить пакет + запустить тесты
pip install -e .
pytest tests/test_api_smoke.py -v

# 5. Запустить API
uvicorn src.atlas.api.app:app --reload --port 8000
# Перейти на http://localhost:8000/docs для Swagger UI
```

## 💡 Быстрый старт

### Python API

```python
from atlas import SemanticSpace

# Инициализировать пространство
space = SemanticSpace()

# Кодировать текст в 5D вектор
vector = space.encode("Собака")
print(f"Вектор: {vector}")

# Декодировать вектор в текст с рассуждением
result = space.decode(vector, with_reasoning=True)
print(result['reasoning'])
print(f"Текст: {result['text']}")

# Манипулировать измерением
result = space.manipulate_dimension(
    "Собака",
    dimension=1,  # Эмоциональный тон
    new_value=-0.9  # Сделать негативным
)
print(f"Изменено: {result['modified']['decoded']['text']}")
```

### Hierarchical API (NEW!)

```python
from atlas.hierarchical import HierarchicalEncoder, HierarchicalDecoder

# Инициализация
encoder = HierarchicalEncoder()
decoder = HierarchicalDecoder()

# Кодирование в иерархическое дерево
tree = encoder.encode_hierarchical(
    "Собака",
    max_depth=2,              # Глубина дерева
    expand_threshold=0.2      # Порог для раскрытия веток
)

# Декодирование с объяснением по путям
result = decoder.decode_hierarchical(tree, top_k=3, with_reasoning=True)
print(f"Текст: {result['text']}")
for r in result['reasoning']:
    print(f"  {r.path}: {r.label} (вес={r.weight:.2f})")

# Манипуляция по пути (хирургическая правка)
modified_tree = decoder.manipulate_path(
    tree,
    path="dim2/dim2.4",  # Конкретная ветка
    new_value=[0.9, 0.1, -0.2, 0.0, 0.0]
)
modified_result = decoder.decode_hierarchical(modified_tree)
print(f"Изменено: {modified_result['text']}")
```

### REST API

```bash
# Запустить сервер
python scripts/run_api.py
# или с Docker
docker-compose up

# Использовать API
curl -X POST "http://localhost:8000/encode" \
  -H "Content-Type: application/json" \
  -d '{"text": "Собака", "lang": "ru"}'

curl -X POST "http://localhost:8000/decode" \
  -H "Content-Type: application/json" \
  -d '{"vector": [0.1, 0.9, -0.5, 0.2, 0.8], "top_k": 3}'

curl -X POST "http://localhost:8000/explain" \
  -H "Content-Type: application/json" \
  -d '{"text": "Любовь"}'

# Hierarchical endpoints (NEW!)
curl -X POST "http://localhost:8000/encode_h" \
  -H "Content-Type: application/json" \
  -d '{"text": "Собака", "max_depth": 2, "expand_threshold": 0.2}'

curl -X POST "http://localhost:8000/decode_h" \
  -H "Content-Type: application/json" \
  -d '{"tree": {...}, "top_k": 3}'

curl -X POST "http://localhost:8000/manipulate_h" \
  -H "Content-Type: application/json" \
  -d '{"text": "Собака", "edits": [{"path": "dim2/dim2.4", "value": [0.9,0.1,-0.2,0.0,0.0]}]}'

# Документация API: http://localhost:8000/docs
```

### Командная строка

```bash
# Показать информацию об измерениях
atlas info

# Кодировать текст
atlas encode "Собака бежит" --explain

# Декодировать вектор с рассуждением
atlas decode --vector 0.1 0.9 -0.5 0.2 0.8 --reasoning

# Трансформировать текст
atlas transform "Любовь" --reasoning

# Манипулировать измерением
atlas manipulate "Собака" --dimension 1 --value -0.8 --reasoning

# Интерполировать между концептами
atlas interpolate "Любовь" "Ненависть" --steps 5

# Исследовать измерение
atlas explore "Жизнь" --dimension 4 --steps 7

# Hierarchical commands (NEW!)
atlas encode-h "Любовь" --max-depth 2 --expand-threshold 0.2
atlas decode-h --input tree.json --top-k 3 --reasoning
atlas manipulate-h "Собака" --edit dim2/dim2.4=0.9,0.1,-0.2,0.0,0.0 --reasoning
```

## 📊 Примеры

### Пример: Интерпретируемый декодер

**Ввод:** `[0.1, 0.9, -0.5, 0.2, 0.8]`

**Обычный AI:** "Собака."

**Атлас:**
```
Я чувствую, что:
dim₁ = 0.10 → слегка action (Структура фразы)
dim₂ = 0.90 → сильно positive (Эмоциональный тон)
dim₃ = -0.50 → умеренно concrete (Уровень обобщения)
dim₄ = 0.20 → слегка world (Точка наблюдения)
dim₅ = 0.80 → сильно living (Сущностная природа)
→ итог: "Собака"
```

### Пример: Манипуляция измерениями

```python
# Изменить эмоциональный тон
result = space.manipulate_dimension(
    "Радость",
    dimension=1,  # Позитив ↔ Негатив
    new_value=-0.9
)
# Результат: "Грусть" или "Тоска"
```

### Пример: Интерполяция концептов

```python
# Плавный переход между концептами
results = space.interpolate("Любовь", "Страх", steps=5)
# Показывает, как смысл постепенно трансформируется
```

## 🔬 Примеры использования

### Базовое использование

```bash
python examples/basic_usage.py
```

Демонстрирует:
- Кодирование текста в вектор
- Декодирование с рассуждением
- Манипуляцию измерениями
- Интерполяцию между концептами
- Исследование измерений

### Визуализация

```bash
python examples/visualization.py
```

Создаёт визуализации:
- Радарные диаграммы семантических векторов
- 2D проекции семантического пространства
- Визуализацию интерполяции

## 🏗️ Архитектура

```
atlas/
├── encoder.py      # Кодирование: текст → 5D вектор
├── decoder.py      # Декодирование: вектор → текст + рассуждение
├── dimensions.py   # Определение и интерпретация измерений
├── space.py        # Основной интерфейс семантического пространства
└── cli.py          # Интерфейс командной строки
```

### Компоненты

1. **Encoder** (`encoder.py`)
   - Сжимает тексты в 5-мерное пространство
   - Каждое измерение становится отдельной "осью смысла"

2. **Decoder** (`decoder.py`)
   - Восстанавливает текст из вектора
   - Объясняет, почему выбран именно этот смысл
   - Не просто "вектор → слово", а "вектор → история выбора"

3. **Dimensions** (`dimensions.py`)
   - Определяет 5 семантических измерений
   - Интерпретирует значения по каждой оси
   - Объясняет векторы человеческим языком

4. **Space** (`space.py`)
   - Объединяет encoder и decoder
   - Предоставляет API для манипуляции смыслом
   - Визуализация и исследование пространства

## 🎨 Зачем это нужно

### 1. Интерпретируемый AI
Можно увидеть, какая ось отвечает за какой смысл. AI перестаёт быть "чёрным ящиком".

### 2. Визуальный доступ к мышлению
Не только "что" модель поняла, но и "почему" — полная прозрачность процесса.

### 3. Осознанная настройка мышления
Можно вручную менять оси, "вращая" смысл, как спектр света в призме.

### 4. Универсальный интерфейс сознания
- Исследовать эмбеддинги (уменьшенные пространства)
- Наблюдать, как оси коррелируют с концептами
- "Управлять" мыслью, как параметром в аудиоредакторе

## 📚 Документация

### Основная документация

| Документ | Описание |
|----------|----------|
| [README.md](README.md) | Основная документация (этот файл) |
| [DOCUMENTATION.md](DOCUMENTATION.md) | Полная техническая документация |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Гайд для контрибуторов |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Кодекс поведения |
| [SECURITY.md](SECURITY.md) | Политика безопасности |
| [MODEL_CARD.md](MODEL_CARD.md) | Карточка модели |

### Техническая документация

| Документ | Описание |
|----------|----------|
| [docs/NFR.md](docs/NFR.md) | Нефункциональные требования (производительность, безопасность) |
| [docs/DATA_CARD.md](docs/DATA_CARD.md) | Описание данных для обучения |
| [docs/DISENTANGLEMENT.md](docs/DISENTANGLEMENT.md) | Методология разделения семантических измерений |
| [docs/INTERPRETABILITY_METRICS.md](docs/INTERPRETABILITY_METRICS.md) | Метрики интерпретируемости |
| [docs/HIERARCHICAL_SPACE.md](docs/HIERARCHICAL_SPACE.md) | Иерархическое семантическое пространство (NEW!) |

### API документация

### API Reference

#### `SemanticSpace`

Главный класс для работы с семантическим пространством.

```python
space = SemanticSpace()

# Кодирование
vector = space.encode(text)

# Декодирование
text = space.decode(vector, with_reasoning=True)

# Трансформация
result = space.transform(text, show_reasoning=True)

# Манипуляция
result = space.manipulate_dimension(text, dimension, new_value)

# Интерполяция
results = space.interpolate(text1, text2, steps=5)

# Исследование
results = space.explore_dimension(text, dimension, range_vals)

# Информация
info = space.get_dimension_info()
```

## 🧪 Тестирование

```bash
# Запустить тесты (когда будут добавлены)
pytest tests/
```

## 🤝 Вклад

Contributions are welcome! Пожалуйста:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 Лицензия

Проект распространяется по **двойной лицензии**:
- **AGPLv3** (Open Source) — см. [LICENSE](LICENSE)
- **Коммерческая лицензия** — см. [COMMERCIAL_LICENSE.md](COMMERCIAL_LICENSE.md)

Подробнее о лицензировании см. раздел [Лицензирование (Dual License)](#-лицензирование-dual-license) в начале документа.

## 🌐 Философия

> **Атлас — это не модель, а зеркало, в котором смысл видит, как он двигается.**

Это визуальный мозг, отражающий структуру мышления. Через него можно не просто анализировать смысл, но и **управлять** им сознательно.

## 📞 Контакты

- GitHub: [@danilivashyna](https://github.com/danilivashyna)
- Repository: [Atlas](https://github.com/danilivashyna/Atlas)

---

**Atlas** — где смысл встречается с формой. 🗺️✨
