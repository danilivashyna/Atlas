# Phase B → SELF: Дорожная карта

**Статус:** 🚧 В работе  
**Период:** 7 дней  
**Базовая ветка:** `jbarton43/z-space`  
**Цель:** Стабилизация Atlas + FAB + Z-Space перед внедрением SELF

---

## 📊 Текущее состояние (Baseline)

✅ **Завершено:**
- Atlas core (encoder/decoder/hierarchical/space)
- FAB integration (shadow mode, hysteresis, reticulum)
- Z-Space (circuit breaker, policy gating, router)
- Memory persistence + caching
- API endpoints (FAB routes, homeostasis, memory, router)

📈 **Метрики качества:**
- Тестов: 207 passed ✅
- Pylint: 9.44/10 ⭐
- Warnings: 0 в исправленных файлах

---

## 🎯 Phase B: Компоненты

### B1. Hysteresis для Bit-Envelope (анти-дребезг)

**Ветка:** `phaseB/hysteresis`  
**Владелец:** TBD  
**Срок:** D1-D2 (2 дня)

**Описание:**
Ограничение частоты переключений bit-envelope для предотвращения осцилляций.

**Требования:**
- ✅ Лимит: ≤1 переключение/сек/слой
- ✅ Метрики: `switch_rate`, `oscillation_rate`
- ✅ Алерты при дрожании (>2 переключений/5сек)
- ✅ Property-based тесты (hypothesis)

**Файлы для изменения:**
- `src/orbis_fab/core.py` - добавить `BitEnvelopeHysteresis`
- `src/atlas/metrics/mensum.py` - метрики switch_rate/oscillation_rate
- `tests/test_bit_envelope_hysteresis.py` - property-based тесты

**Acceptance Criteria:**
```python
# 1. Rate limiting работает
assert hysteresis.can_switch(layer=2) == False  # если <1сек с последнего
assert hysteresis.get_switch_rate(layer=2) <= 1.0  # switches/sec

# 2. Oscillation detection
assert hysteresis.detect_oscillation(history) == True  # если >2 за 5сек

# 3. Property: eventually stable
@given(st.lists(st.booleans()))
def test_eventually_stable(transitions):
    # После N переключений система стабилизируется
    assert hysteresis.is_stable(window=10) == True
```

**SLO/SLI:**
- `oscillation_rate_p95 < 0.1` (10% окон)
- `stability_latency_p50 < 2s` (время до стабилизации)

---

### B2. Window Stability Counter

**Ветка:** `phaseB/stability`  
**Владелец:** TBD  
**Срок:** D3 (1 день)

**Описание:**
Экспоненциальный счетчик стабильности для Global/Stream окон с триггерами деградации.

**Требования:**
- ✅ EMA счетчик стабильности (decay=0.95)
- ✅ Пороговые действия при падении стабильности
- ✅ Метрики: `stability_score`, `degradation_events`
- ✅ Интеграция с FAB mode switching (FAB2→FAB1→FAB0)

**Файлы для изменения:**
- `src/orbis_fab/stability.py` - новый модуль `WindowStabilityCounter`
- `src/orbis_fab/core.py` - интеграция в `FABCore.decide()`
- `tests/test_window_stability.py` - unit + integration тесты

**Acceptance Criteria:**
```python
# 1. Stability tracking
counter = WindowStabilityCounter(decay=0.95)
counter.update(window_id="global_1", stable=True)
assert counter.get_score(window_id="global_1") > 0.9

# 2. Degradation triggers
counter.update(window_id="global_1", stable=False)  # 5 раз подряд
assert counter.should_degrade(window_id="global_1") == True

# 3. Mode switching
fab_mode = counter.recommend_mode(stability_score=0.3)
assert fab_mode == "FAB0"  # деградация до safe mode
```

**SLO/SLI:**
- `stability_score_p50 > 0.8` (80% окон стабильны)
- `stability_score_p95 > 0.6` (даже worst-case >60%)
- `degradation_events < 10/hour` (редкие деградации)

---

### B3. Z-Space Shim → FAB.fill (телеметрия и квоты)

**Ветка:** `phaseB/shim-telemetry`  
**Владелец:** TBD  
**Срок:** D4 (1 день)

**Описание:**
Измерение производительности Z-Space shim с фича-флагом для write-through.

**Требования:**
- ✅ Телеметрия: `latency_ms`, `coverage`, `novelty`
- ✅ Фича-флаг: `ATLAS_ZSPACE_WRITE_THROUGH=off` (по умолчанию)
- ✅ Квоты: `time_ms`, `nodes`, `tokens` бюджеты
- ✅ Graceful degradation при превышении квот

**Файлы для изменения:**
- `src/orbis_fab/zspace_shim.py` - добавить телеметрию
- `src/atlas/metrics/mensum.py` - метрики latency/coverage/novelty
- `tests/test_zspace_telemetry.py` - тесты фича-флага и квот

**Acceptance Criteria:**
```python
# 1. Telemetry collected
metrics = zspace_shim.get_metrics()
assert "latency_ms" in metrics
assert "coverage" in metrics  # % от запрошенных узлов
assert "novelty" in metrics   # diversity score

# 2. Feature flag
assert os.getenv("ATLAS_ZSPACE_WRITE_THROUGH", "off") == "off"
assert zspace_shim.write_through_enabled == False

# 3. Budget enforcement
result = zspace_shim.select(k=1000, budgets={"time_ms": 10, "nodes": 100})
assert result.truncated == True  # превышен бюджет
assert len(result.nodes) <= 100
```

**SLO/SLI:**
- `zspace_latency_p95 < 50ms` (быстрый selector)
- `zspace_coverage_p50 > 0.8` (80% запрошенных узлов)
- `budget_violations < 5%` (редкие превышения квот)

---

### B4. CI/Quality Gates

**Ветка:** `main` (инфраструктура)  
**Владелец:** DevOps/CI  
**Срок:** D5 (параллельно с нагрузкой)

**Описание:**
Обязательные гейты качества для всех PR в Phase B.

**Требования:**
- ✅ `ruff check` - без ошибок
- ✅ `black --check` - форматирование
- ✅ `mypy --strict` - типизация
- ✅ `pytest --cov=90%` - покрытие тестами
- ✅ Запрет мерджа при новых lint/type ошибках

**Файлы для изменения:**
- `.github/workflows/ci.yml` - добавить gates
- `pyproject.toml` - настройки ruff/mypy/pytest
- `scripts/run_quality_gates.sh` - скрипт для локального запуска

**Quality Dashboard:**
```yaml
metrics:
  - name: latency_p95
    target: < 100ms
    alert: > 200ms
  
  - name: drift_rate
    target: < 0.05  # 5% дрейфа
    alert: > 0.1
  
  - name: oscillation_rate
    target: < 0.1   # 10% осцилляций
    alert: > 0.2
  
  - name: stability_score
    target: > 0.8   # 80% стабильных окон
    alert: < 0.6
```

---

## 📅 7-дневный план работ

### День 1-2: B1 Hysteresis
- [ ] Реализовать `BitEnvelopeHysteresis` класс
- [ ] Добавить метрики `switch_rate`, `oscillation_rate`
- [ ] Написать property-based тесты (hypothesis)
- [ ] Интеграция в `FABCore`
- [ ] PR review + merge в `jbarton43/z-space`

### День 3: B2 Stability Counter
- [ ] Реализовать `WindowStabilityCounter` класс
- [ ] EMA tracking с decay=0.95
- [ ] Пороговые триггеры деградации
- [ ] Метрики `stability_score`, `degradation_events`
- [ ] Тесты + алерты на дрожание
- [ ] PR review + merge

### День 4: B3 Z-Space Telemetry
- [ ] Добавить телеметрию в `zspace_shim.py`
- [ ] Фича-флаг `ATLAS_ZSPACE_WRITE_THROUGH`
- [ ] Квоты и graceful degradation
- [ ] Метрики `latency_ms`, `coverage`, `novelty`
- [ ] Тесты фича-флага
- [ ] PR review + merge

### День 5: Нагрузочное тестирование
- [ ] Прогоны с realistic workload (100k запросов)
- [ ] Профилирование bottlenecks
- [ ] Обновление golden samples с новыми метриками
- [ ] Проверка SLO/SLI compliance

### День 6-7: Стабилизация + документация
- [ ] Фикс багов из нагрузочных прогонов
- [ ] Документация Phase B (API, архитектура, метрики)
- [ ] Обновление `MODEL_CARD.md` с новыми характеристиками
- [ ] Подготовка к SELF: скелет `SelfManager`
- [ ] Final review всех PR

---

## 🚀 SELF Preview (следующий этап)

**Концепция:**
SELF (Self-Evolving Learning Framework) - система управления идентичностью окон с протоколом передачи состояния.

### Компоненты SELF:

#### 1. SelfManager
```python
class SelfManager:
    """Управление жизненным циклом SELF токенов."""
    
    def mint(self, window_id: str) -> SelfToken:
        """Создать новый SELF токен для окна."""
        
    def update(self, token: SelfToken, event: Event) -> SelfToken:
        """Обновить состояние токена на основе события."""
        
    def transfer(self, from_window: str, to_window: str) -> bool:
        """Передать SELF между окнами (stream merge)."""
        
    def replicate(self, token: SelfToken, target: str) -> SelfToken:
        """Создать копию токена для нового окна."""
```

#### 2. SelfToken
```python
@dataclass
class SelfToken:
    """Идентичность окна с метриками состояния."""
    
    window_id: str
    presence: float      # 0-1: насколько окно "присутствует"
    coherence: float     # 0-1: внутренняя согласованность
    continuity: float    # 0-1: непрерывность во времени
    stress: float        # 0-1: нагрузка/давление на окно
    
    created_at: datetime
    updated_at: datetime
    version: int
    
    # Трассировка
    parent_id: Optional[str]
    lineage: List[str]
```

#### 3. Гейтирование по FAB mode
```python
# FAB0 (Safe): Только чтение SELF
self_manager.can_write(mode="FAB0") == False

# FAB1 (Balanced): Чтение + обновление
self_manager.can_write(mode="FAB1") == True
self_manager.can_transfer(mode="FAB1") == False

# FAB2 (Aggressive): Полный доступ
self_manager.can_transfer(mode="FAB2") == True
self_manager.can_replicate(mode="FAB2") == True
```

#### 4. Протокол передачи
```python
# Stream merge: Global ← Stream
protocol = SelfTransferProtocol()
success = protocol.merge(
    from_token=stream_self,
    to_token=global_self,
    strategy="weighted_average"  # coherence-weighted
)

# Трассинг в identity.jsonl
identity_log.append({
    "event": "transfer",
    "from": stream_self.window_id,
    "to": global_self.window_id,
    "coherence_delta": new_coherence - old_coherence,
    "timestamp": now()
})
```

---

## ⚠️ Риски и смягчения

### Риск 1: Перегрев селектора
**Симптомы:** Z-Space latency >200ms, CPU spike  
**Смягчение:**
- Жесткий `time_ms` лимит (50ms default)
- Деградация `precision` при timeout
- Профилирование + оптимизация hot paths

### Риск 2: Осцилляции на границах backpressure
**Симптомы:** Частые переключения FAB1↔FAB0, дрожание  
**Смягчение:**
- Гистерезис с dead band (±10%)
- EMA сглаживание метрик (decay=0.95)
- Cooldown период после переключения (5s)

### Риск 3: Несоответствие контрактов ZSliceLite
**Симптомы:** Ошибки при fill(), incompatible data types  
**Смягчение:**
- Единый контракт в `orbis_fab/zslice.py`
- Pydantic валидация на границах
- Тесты совместимости FAB ↔ Z-Space

---

## 📋 Чек-листы для PR

### PR Template: Phase B

**Название:** `[PhaseB/B{1-4}] {краткое описание}`

**Чек-лист перед мерджем:**
- [ ] Все тесты проходят (`pytest -v`)
- [ ] Pylint ≥9.0/10, 0 warnings в новых файлах
- [ ] Type hints для всех публичных функций
- [ ] Docstrings для всех классов и функций
- [ ] Метрики добавлены в Prometheus/Grafana
- [ ] SLO/SLI определены и документированы
- [ ] Golden samples обновлены (если applicable)
- [ ] CHANGELOG.md обновлен
- [ ] Reviewed by 1+ team member

**Ссылки:**
- Design doc: `docs/design/{component}.md`
- SLO/SLI: `docs/slo/{component}.yaml`
- Тесты: `tests/test_{component}.py`

---

## 🎯 Definition of Done для Phase B

✅ **Техническое:**
- [ ] Все 4 компонента (B1-B4) реализованы и merged
- [ ] 207+ тестов проходят (новые тесты добавлены)
- [ ] Pylint ≥9.4/10 на всем кодбейзе
- [ ] Нагрузочные прогоны показывают соответствие SLO

✅ **Метрики:**
- [ ] `oscillation_rate_p95 < 0.1`
- [ ] `stability_score_p50 > 0.8`
- [ ] `zspace_latency_p95 < 50ms`
- [ ] `degradation_events < 10/hour`

✅ **Документация:**
- [ ] Phase B design docs завершены
- [ ] API docs обновлены
- [ ] MODEL_CARD.md включает новые характеристики
- [ ] Runbook для операторов (troubleshooting)

✅ **Готовность к SELF:**
- [ ] Скелет `SelfManager` создан
- [ ] `SelfToken` dataclass определен
- [ ] Протокол передачи spec написан
- [ ] Тесты для SELF протокола (stub implementation)

---

**Следующий этап:** SELF Implementation (Phase C)  
**Ориентировочно:** Начало через 7 дней после завершения Phase B
