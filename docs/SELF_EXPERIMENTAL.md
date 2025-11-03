# SELF Framework - Experimental Sandbox

**Статус:** Экспериментальный (EXP_SANDBOX)  
**Версия:** 0.1.0-exp  
**Ветка:** `jbarton43/z-space` (основная разработка)  
**Feature Flag:** `AURIS_SELF=off` (по умолчанию)

---

## Обзор

SELF (Self-Experimental Lifecycle Framework) - экспериментальная система самореференции для отслеживания когерентности и непрерывности работы системы Atlas/FAB.

Система полностью изолирована от основного кода и не влияет на производственное поведение до явной активации.

---

## Архитектура

### Компоненты

```
src/orbis_self/
├── __init__.py         # Экспорты, feature flag
├── contracts.py        # Базовые типы (SelfScores, SelfEvent, CoherenceProbe)
├── token.py            # SelfToken (presence, coherence, continuity, stress)
├── manager.py          # SelfManager (mint/update/transfer/replicate/heartbeat)
└── bridge.py           # CoherenceBridge (вычисление метрик, синхронизация)

src/orbis_fab/
└── fab_self_bridge_exp.py  # Экспериментальный адаптер для FABCore

tests/
├── test_self_token.py     # 23 теста для SelfToken
├── test_self_manager.py   # 25 тестов для SelfManager
└── test_self_bridge.py    # 19 тестов для CoherenceBridge
```

### Основные абстракции

#### 1. **SelfToken** - токен самореференции

Хранит 4 метрики состояния системы:

```python
@dataclass
class SelfToken:
    presence: float      # [0.0, 1.0] - "я есть", активность
    coherence: float     # [0.0, 1.0] - согласованность FAB↔Atlas
    continuity: float    # [0.0, 1.0] - непрерывность во времени
    stress: float        # [0.0, 1.0] - уровень перегрузки
```

**Методы:**
- `normalize()` - клипает значения в [0.0, 1.0]
- `decay(rate=0.01)` - экспоненциальная деградация (stress НЕ деградирует)
- `as_dict()` → `SelfScores` - сериализация
- `compute_status()` → "stable" | "degraded" | "critical"

#### 2. **SelfManager** - управление жизненным циклом

```python
class SelfManager:
    def mint(token_id, initial_scores=None) -> SelfToken
    def update(token_id, tick=None, **scores) -> SelfToken
    def transfer(token_id, to_fab=None) -> bool  # Заглушка
    def replicate(token_id) -> SelfToken
    def heartbeat(token_id, every_n=50) -> bool
```

**Хранение:**
- In-memory: `dict[str, SelfToken]`
- Персистентность: `data/identity.jsonl` (JSONL append-only)

**События:**
Все операции логируются в `identity.jsonl`:

```json
{"ts": "2025-11-03T10:30:00Z", "kind": "mint", "token_id": "fab-default", "presence": 0.5}
{"ts": "2025-11-03T10:30:01Z", "kind": "heartbeat", "token_id": "fab-default", "presence": 0.8, "status": "stable"}
```

#### 3. **CoherenceBridge** - вычисление метрик

**Статические методы:**

```python
# Coherence: согласованность FAB↔Atlas состояний
compute_coherence(fab_state, atlas_state) -> float

# Косинусное сходство векторов (для embeddings)
compute_coherence_cosine(vec_a, vec_b) -> float

# Continuity: стабильность presence
compute_continuity(prev_presence, curr_presence) -> float

# Stress: перегрузка на основе stability/oscillation
compute_stress(stability_score, oscillation_rate) -> float

# Логирование метрик
emit_metrics(prefix, scores: SelfScores) -> None
```

#### 4. **FAB Integration Adapter** (экспериментальный)

Не изменяет FABCore, работает через wrapper:

```python
from orbis_fab.fab_self_bridge_exp import attach, maybe_self_tick

# Активация (только при AURIS_SELF=on)
self_mgr = attach(fab_core_instance)

# В цикле обработки
for tick in range(1000):
    # ... основная логика FAB ...
    maybe_self_tick(fab_core, self_mgr, token_id="fab-default")
```

---

## Использование

### 1. Отключено (default)

```bash
# Ничего не делаем - SELF не активируется
python examples/basic_usage.py
```

### 2. Включено вручную

```bash
export AURIS_SELF=on
python examples/with_self.py
```

```python
import os
os.environ["AURIS_SELF"] = "on"

from orbis_self.manager import SelfManager

# Создаём менеджер
mgr = SelfManager()

# Создаём токен
token = mgr.mint("fab-default")

# Обновляем метрики
for tick in range(100):
    mgr.update(
        "fab-default",
        tick=tick,
        presence=0.8 + 0.1 * (tick % 10) / 10,
        coherence=0.9,
        continuity=0.85,
        stress=0.1 + 0.05 * (tick % 20) / 20,
    )
    
    # Heartbeat каждые 10 тиков
    mgr.heartbeat("fab-default", every_n=10)

# Токен сохранён в data/identity.jsonl
```

---

## Тестирование

### Запуск тестов

```bash
# Все SELF тесты
pytest tests/test_self_*.py -v

# С coverage
pytest tests/test_self_*.py --cov=src/orbis_self --cov-report=term-missing
```

### Статистика

- **Тесты:** 67 total (23 token + 25 manager + 19 bridge)
- **Coverage:** 95% (222 statements, 10 missed)
- **Pylint:** 9.63/10 (выше цели ≥9.3)
- **Black:** ✅ Отформатировано

---

## Quality Gates

### ✅ Критерии приёмки (DoD)

- [x] Все модули созданы и работают изолированно
- [x] Существующие файлы проекта НЕ изменены
- [x] 67 тестов проходят (100% success rate)
- [x] Coverage ≥85% (достигнуто 95%)
- [x] Pylint ≥9.3 (достигнуто 9.63)
- [x] Black форматирование применено
- [x] SelfManager работает без FAB (с имитацией)
- [x] identity.jsonl создаётся и содержит валидные JSONL события

### Предупреждения (допустимые)

```
R0912: Too many branches (bridge.py) - сложная эвристика coherence
C0415: Import outside toplevel (fab_self_bridge_exp.py) - lazy imports для изоляции
W0511: TODO comments (fab_self_bridge_exp.py) - для будущей интеграции
```

Все предупреждения - намеренные архитектурные решения для экспериментального кода.

---

## Roadmap

### Phase A (Текущая) - Изолированная реализация ✅

- [x] Базовые контракты (SelfScores, SelfEvent, CoherenceProbe)
- [x] SelfToken с нормализацией и decay
- [x] SelfManager с полным lifecycle
- [x] CoherenceBridge с эвристиками
- [x] Экспериментальный FAB адаптер
- [x] Полное тестовое покрытие

### Phase B - Интеграция с FABCore (будущее)

После завершения Phase B основной ветки (hysteresis, stability, telemetry):

- [ ] Извлечение real FAB state (precision, stability_score, oscillation_rate)
- [ ] Интеграция с Z-Space metrics
- [ ] Автоматический вызов `maybe_self_tick()` в FABCore.step_stub()
- [ ] Prometheus метрики для SELF (presence_gauge, coherence_gauge)
- [ ] Grafana dashboard

### Phase C - Production Activation

**Gates (до активации):**

1. Phase B SLO выполнены 24h непрерывно:
   - oscillation_rate_p95 < 0.1
   - stability_score_p50 > 0.8
   - degradation_events < 10/hour

2. Quality gates:
   - CI green (all checks passing)
   - Coverage ≥90%
   - Pylint ≥9.4 (project-wide)
   - 24h snapshot задокументирован

**Активация:**

```bash
# Production config
export AURIS_SELF=on

# Мониторинг
tail -f data/identity.jsonl | jq '.'
```

---

## Safety Guarantees

### 1. **Zero Production Impact (по умолчанию)**

- `AURIS_SELF=off` → все методы no-op
- Не импортируется в основной код
- Не модифицирует FABCore/ZSpace

### 2. **Graceful Degradation**

- SelfManager может работать автономно (без FAB)
- Ошибки в SELF не прерывают основной процесс
- Lazy imports защищают от circular dependencies

### 3. **Observability**

- Все события в `identity.jsonl` (append-only, rotatable)
- Python logging (DEBUG/INFO levels)
- Готов к Prometheus integration

### 4. **Изоляция файлов**

```
Созданные файлы (не пересекаются с основной веткой):
  src/orbis_self/*
  src/orbis_fab/fab_self_bridge_exp.py  # EXP suffix
  tests/test_self_*
  docs/SELF_EXPERIMENTAL.md
```

---

## FAQ

### Q: Почему отдельный namespace `orbis_self`?

Полная изоляция от существующих `orbis_fab`, `orbis_z`, `atlas`. Легко удалить или отключить.

### Q: Что означают метрики?

- **presence:** Степень активности системы (↑ при тиках, ↓ при decay)
- **coherence:** Согласованность FAB↔Atlas (косинусное сходство состояний)
- **continuity:** Непрерывность (1 - |Δpresence|)
- **stress:** Перегрузка (f(stability, oscillation))

### Q: Когда использовать `transfer()` vs `replicate()`?

- **transfer():** Передача токена другому компоненту (заглушка, логирует событие)
- **replicate():** Создание копии токена с новым ID (полная независимость)

### Q: Как интегрировать с Prometheus?

```python
from prometheus_client import Gauge

SELF_PRESENCE = Gauge("self_presence", "SELF token presence", ["token_id"])
SELF_STRESS = Gauge("self_stress", "SELF token stress", ["token_id"])

def update_prometheus(token_id: str, token: SelfToken):
    SELF_PRESENCE.labels(token_id=token_id).set(token.presence)
    SELF_STRESS.labels(token_id=token_id).set(token.stress)
```

---

## Контакты

**Автор:** AURIS + Copilot (экспериментальная реализация)  
**Ветка:** `jbarton43/z-space` (основная разработка)  
**Review:** Требуется перед merge в main

**Коммит:**
```bash
git add src/orbis_self tests/test_self_* src/orbis_fab/fab_self_bridge_exp.py docs/SELF_EXPERIMENTAL.md
git commit -m "feat(self): experimental SELF framework with lifecycle management

- SelfToken: presence/coherence/continuity/stress metrics
- SelfManager: mint/update/transfer/replicate/heartbeat lifecycle
- CoherenceBridge: coherence/continuity/stress computation
- FAB adapter (exp): attach/maybe_self_tick without core.py changes
- 67 tests, 95% coverage, Pylint 9.63/10
- identity.jsonl JSONL logging
- Feature flag: AURIS_SELF=off (zero production impact)

EXP_SANDBOX: isolated namespace, no core file changes, ready for Phase B integration"
```

---

**Статус:** ✅ **Ready for review** (все DoD критерии выполнены)
