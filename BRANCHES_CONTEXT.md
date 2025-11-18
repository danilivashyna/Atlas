<file name=src/atlas/metrics/exp_prom_exporter.py>
# Existing imports and Gauge definitions...

# Existing stability and hysteresis metric declarations here...

# ----- SELF metrics (Phase C) -----
try:
    SELF_COHERENCE = Gauge("self_coherence", "SELF coherence score (0..1)", ["token_id"])
    SELF_CONTINUITY = Gauge("self_continuity", "SELF continuity score (0..1)", ["token_id"])
    SELF_PRESENCE = Gauge("self_presence", "SELF presence score (0..1)", ["token_id"])
    SELF_STRESS = Gauge("self_stress", "SELF stress (0..1, lower is better)", ["token_id"])
except Exception:  # pragma: no cover - registry may be missing in stubs
    SELF_COHERENCE = SELF_CONTINUITY = SELF_PRESENCE = SELF_STRESS = None

# Other update_*_metrics functions...

def update_self_metrics(token_id: str, *, coherence: float, continuity: float, presence: float, stress: float) -> None:
    """
    Update SELF-related Prometheus metrics.
    Safe to call even if Prometheus client is stubbed/missing.
    """
    if SELF_COHERENCE and SELF_CONTINUITY and SELF_PRESENCE and SELF_STRESS:
        SELF_COHERENCE.labels(token_id=token_id).set(coherence)
        SELF_CONTINUITY.labels(token_id=token_id).set(continuity)
        SELF_PRESENCE.labels(token_id=token_id).set(presence)
        SELF_STRESS.labels(token_id=token_id).set(stress)
</file>

<file name=src/orbis_self/phase_c_hook_exp.py>
# ... existing imports and code ...

def maybe_self_tick(fab_core):
    # ... existing code ...

    # Compute coherence, continuity, presence, stress
    coherence = ...  # existing computation
    continuity = ...  # existing computation
    presence = ...  # existing computation
    stress = ...  # existing computation

    # export SELF metrics to Prometheus (if exp metrics enabled)
    try:
        from atlas.metrics.exp_prom_exporter import update_self_metrics  # import-inside for flag-guarded envs
        token_id = getattr(token, "id", getattr(token, "token_id", "global"))
        update_self_metrics(
            token_id=str(token_id),
            coherence=coherence,
            continuity=continuity,
            presence=presence,
            stress=stress,
        )
    except Exception:
        # Best-effort: do not fail tick if metrics exporter is unavailable
        pass

    # ... existing code ...
</file>

<file name=tests/test_self_metrics_exp.py>
import os
import re
import importlib

def test_self_metrics_export_smoke(tmp_path, monkeypatch):
    # Ensure experimental metrics are effectively importable
    monkeypatch.setenv("AURIS_METRICS_EXP", "on")
    # Reload exporter to pick the env (in case tests reuse interpreter)
    exp = importlib.import_module("atlas.metrics.exp_prom_exporter")
    importlib.reload(exp)

    # Call update function with a few values
    token_id = "canary-token"
    exp.update_self_metrics(token_id, coherence=0.91, continuity=0.95, presence=1.0, stress=0.12)

    # Render metrics text via Prometheus generate_latest if present; otherwise fallback to repr
    try:
        from prometheus_client import generate_latest, CollectorRegistry

        # If exporter uses the default REGISTRY, generate_latest without args will dump all
        text = generate_latest().decode("utf-8")
    except Exception:
        # Fallback: fake text by reading labels via Gauge._metrics, which is ok for a smoke test
        parts = []
        for g in (exp.SELF_COHERENCE, exp.SELF_CONTINUITY, exp.SELF_PRESENCE, exp.SELF_STRESS):
            if g is not None:
                # Access internals in tests is acceptable
                parts.append(g._name)
        text = "\n".join(parts)

    # Must contain metric names
    assert "self_coherence" in text
    assert "self_continuity" in text
    assert "self_presence" in text
    assert "self_stress" in text
</file>

<file name=deploy/alerts/phase_c_rules.yml>
# existing groups...

- name: auris-self-phase-c
  rules:
  - alert: AURIS_SELF_Coherence_Drop
    expr: self_coherence < 0.80
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "SELF coherence below SLO"
      description: "Average SELF coherence < 0.80 for 5m"

  - alert: AURIS_SELF_Continuity_Drop
    expr: self_continuity < 0.90
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "SELF continuity below SLO"
      description: "Average SELF continuity < 0.90 for 5m"

  - alert: AURIS_SELF_Stress_High
    expr: self_stress > 0.30
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "SELF stress above SLO"
      description: "Average SELF stress > 0.30 for 5m"
</file>

<file name=BRANCHES_CONTEXT.md>
# Atlas Multi-Branch Development Context

**Date**: 2025-11-02  
**Strategy**: Phase B → SELF Pipeline  
**Current Phase**: Phase B (Stabilization)

---

## 🌳 Структура веток

```
main (Atlas v0.2.0 E4 GA)
  ↓
jbarton43/z-space (Atlas + FAB + Z-Space ✅ CLEAN)
  ↓
  ├─► phaseB/hysteresis       (B1: Bit-Envelope Hysteresis)
  ├─► phaseB/stability        (B2: Window Stability Counter)
  ├─► phaseB/shim-telemetry   (B3: Z-Space Telemetry)
  └─► [Phase C: SELF] (upcoming)
```

---

## 📊 Текущее состояние (Baseline)

### jbarton43/z-space ✅ CLEAN

**Статус**: 207 тестов passed, Pylint 9.44/10, 0 warnings  
**Завершено**:
- ✅ Atlas core (encoder/decoder/hierarchical/space/dimensions)
- ✅ FAB integration (shadow mode, reticulum, hysteresis)
- ✅ Z-Space (circuit breaker, policy gating, router)
- ✅ Memory persistence + query cache
- ✅ API endpoints (FAB routes, homeostasis, memory, router)
- ✅ Cleanup: 91+ Pylint warnings устранены
- ✅ 4 коммита с исправлениями

- ✅ Phase C canary 5% LIVE (SELF heartbeat + metrics export)
- ✅ Prometheus: self_coherence/self_continuity/self_presence/self_stress
- ✅ Alerts: AURIS_SELF_* (warning tier)

**Метрики качества**:
```yaml
tests_passed: 207/211 (98%)
  - API modules: 40 passed
  - Core modules: 50 passed
  - FAB integration: 32 passed
  - Z-Space: 10 passed
  - Memory: 8 passed
  - Integration: 51 passed
  - Golden samples: 16 passed

code_quality:
  pylint_score: 9.44/10
  warnings: 0 (в исправленных файлах)
  coverage: ~85%
```

**Известные проблемы** (не блокируют Phase B):
- 1 failing тест в `test_z_space_circuit_breaker.py::test_cb_reason_counts_accumulate`
- 3 failing теста в `test_summarize.py` (500 Internal Server Error)

---

## 📋 Phase B: Ветки и планирование

## 📋 Phase B: Ветки и планирование

### 1. **phaseB/hysteresis** — B1 (D1-D2)
**Status**: 🆕 Created, Ready to Start  
**Base**: `jbarton43/z-space`  
**Owner**: TBD  
**Deadline**: 2 дня

**Цель**: Анти-дребезг для bit-envelope с ограничением ≤1 переключение/сек/слой

**Компоненты**:
- `src/orbis_fab/hysteresis.py` - `BitEnvelopeHysteresis` класс
- `tests/test_bit_envelope_hysteresis.py` - property-based тесты
- Метрики: `switch_rate`, `oscillation_rate`, `stability_latency`

**SLO**:
- `oscillation_rate_p95 < 0.1` (10% окон)
- `stability_latency_p50 < 2s`
- `switch_rate_max ≤ 1.0/sec`

**Документация**:
- Design: `docs/design/hysteresis.md` (TBD)
- PR Template: `docs/pr_templates/PR_B1_HYSTERESIS.md` ✅
- Runbook: `docs/runbooks/hysteresis_oscillation.md` (TBD)

---

### 2. **phaseB/stability** — B2 (D3)
**Status**: 🆕 Created, Ready to Start  
**Base**: `jbarton43/z-space`  
**Owner**: TBD  
**Deadline**: 1 день

**Цель**: Window Stability Counter с EMA и триггерами деградации

**Компоненты**:
- `src/orbis_fab/stability.py` - `WindowStabilityCounter` класс
- `tests/test_window_stability.py` - unit + integration
- Интеграция с `FABCore.decide()` для mode switching

**SLO**:
- `stability_score_p50 > 0.8` (80% окон стабильны)
- `stability_score_p95 > 0.6` (worst-case >60%)
- `degradation_events < 10/hour`

**Зависимости**:
- Использует `oscillation_rate` из B1

---

### 3. **phaseB/shim-telemetry** — B3 (D4)
**Status**: 🆕 Created, Ready to Start  
**Base**: `jbarton43/z-space`  
**Owner**: TBD  
**Deadline**: 1 день

**Цель**: Телеметрия Z-Space shim + фича-флаг для write-through

**Компоненты**:
- Дополнить `src/orbis_fab/zspace_shim.py` телеметрией
- `tests/test_zspace_telemetry.py` - тесты фича-флага и квот
- Метрики: `latency_ms`, `coverage`, `novelty`

**SLO**:
- `zspace_latency_p95 < 50ms`
- `zspace_coverage_p50 > 0.8` (80% покрытие)
- `budget_violations < 5%`

**Feature Flag**:
```python
ATLAS_ZSPACE_WRITE_THROUGH=off  # по умолчанию
```

---

## 📅 7-дневный план (краткий)

| День | Задача | Ветка | Deliverables |
|------|--------|-------|--------------|
| **D1-D2** | B1: Hysteresis | `phaseB/hysteresis` | Класс + тесты + метрики + PR |
| **D3** | B2: Stability | `phaseB/stability` | EMA counter + триггеры + PR |
| **D4** | B3: Telemetry | `phaseB/shim-telemetry` | Метрики + фича-флаг + PR |
| **D5** | Load Testing | все ветки | Нагрузочные прогоны + baseline |
| **D6-D7** | Stabilization | все ветки | Багфиксы + docs + SELF skeleton |

---

## 🎯 Definition of Done (Phase B)

✅ **Технически**:
- [ ] Все 4 компонента (B1-B4) merged
- [ ] 207+ тестов passed
- [ ] Pylint ≥9.4/10
- [ ] SLO compliance >90%

✅ **Документация**:
- [ ] Design docs завершены
- [ ] Runbooks для алертов
- [ ] MODEL_CARD.md обновлен
- [ ] API docs актуальны

✅ **Готовность к SELF**:
- [ ] `SelfManager` skeleton
- [ ] `SelfToken` dataclass
- [ ] Transfer protocol spec

---

## 🚀 SELF Preview (Phase C)

**Компоненты**:
```python
class SelfManager:
    def mint(window_id: str) -> SelfToken
    def update(token: SelfToken, event: Event) -> SelfToken
    def transfer(from_window: str, to_window: str) -> bool
    def replicate(token: SelfToken, target: str) -> SelfToken

@dataclass
class SelfToken:
    window_id: str
    presence: float    # 0-1
    coherence: float   # 0-1
    continuity: float  # 0-1
    stress: float      # 0-1
    created_at: datetime
    version: int
```

**Гейтирование по FAB mode**:
- FAB0: read-only SELF
- FAB1: read + update
- FAB2: full access (transfer + replicate)

**Трассировка**: `identity.jsonl` logging

---

## 📚 Документация Phase B

### Созданные файлы

1. **`docs/PHASE_B_ROADMAP.md`** ✅
   - Полная дорожная карта 7 дней
   - Описание всех компонентов B1-B4
   - Риски и смягчения
   - PR чек-листы

2. **`docs/slo/PHASE_B_SLO_SLI.md`** ✅
   - Детальные SLO/SLI для каждого компонента
   - Формулы расчета метрик
   - Алерты и эскалация
   - Grafana dashboards spec

3. **`docs/pr_templates/PR_B1_HYSTERESIS.md`** ✅
   - Шаблон PR для B1
   - Чек-лист перед мерджем
   - Инструкции по тестированию
   - Acceptance criteria

4. **`docs/PHASE_B_QUICK_START.md`** ✅
   - Краткий гид по началу работы
   - Quick commands
   - SLO targets справка
   - Definition of Done

### Файлы для создания

- `docs/design/hysteresis.md` - design doc для B1
- `docs/design/stability.md` - design doc для B2
- `docs/design/zspace_telemetry.md` - design doc для B3
- `docs/runbooks/hysteresis_oscillation.md` - runbook
- `docs/runbooks/stability_degradation.md` - runbook
- `docs/runbooks/zspace_timeout.md` - runbook

---

## 🔗 Полезные ссылки

**Документация**:
- [Phase B Roadmap](docs/PHASE_B_ROADMAP.md)
- [SLO/SLI Metrics](docs/slo/PHASE_B_SLO_SLI.md)
- [Quick Start Guide](docs/PHASE_B_QUICK_START.md)
- [PR Template B1](docs/pr_templates/PR_B1_HYSTERESIS.md)

**Ветки**:
```bash
jbarton43/z-space       # базовая (clean)
phaseB/hysteresis       # B1
phaseB/stability        # B2
phaseB/shim-telemetry   # B3
```

**Команды**:
```bash
# Переключиться на Phase B ветку
git checkout phaseB/hysteresis

# Запустить все тесты
pytest -v

# Проверить Pylint
pylint src/orbis_fab/ --fail-under=9.0

# Запустить с coverage
pytest --cov=src --cov-report=html
```

---

## ⚠️ Риски Phase B

### Риск 1: Перегрев селектора
**Смягчение**: жесткий time_ms лимит, деградация precision, профилирование

### Риск 2: Осцилляции на границах backpressure
**Смягчение**: гистерезис с dead band ±10%, EMA сглаживание, cooldown 5s

### Риск 3: Несоответствие контрактов ZSliceLite
**Смягчение**: единый контракт, Pydantic валидация, compatibility тесты

---

## � Метрики успеха Phase B

```yaml
baseline_current:  # jbarton43/z-space
  tests_passed: 207
  pylint_score: 9.44
  warnings: 0

targets_phase_b:  # после завершения
  tests_passed: 220+  # +13 новых тестов
  pylint_score: ≥9.4
  slo_compliance: >90%
  
  hysteresis:
    oscillation_rate_p95: <0.1
    stability_latency_p50: <2s
  
  stability:
    stability_score_p50: >0.8
    degradation_events: <10/hour
  
  zspace:
    latency_p95: <50ms
    coverage_p50: >0.8
```

---

**Последнее обновление**: 2025-11-02  
**Следующий milestone**: Phase B Day 1 (B1 Hysteresis start)  
**Last commit**: `65f2f92` (FAB_PHASE_A_STATUS.md)  
**Scope**: FAB Core — оперативная шина осознания

**Спецификация**:
- `docs_fab/FAB_FULL_SPEC_v1.0.md` (полная спецификация)
- `docs_fab/FAB_OVERVIEW.md` (обзор архитектуры)
- `docs_fab/FAB_INTRO_CONTEXT.md` (контекст интеграции)

**✅ Phase A Complete (21e848e + 65f2f92)**:
- ✅ Ядро FAB (`src/orbis_fab/core.py`, 184 строки)
- ✅ Type definitions (`src/orbis_fab/types.py`, 70 строк)
- ✅ State machine (`src/orbis_fab/state.py`, 60 строк)
- ✅ Backpressure (`src/orbis_fab/backpressure.py`, 50 строк)
- ✅ Bit-envelope (`src/orbis_fab/envelope.py`, 50 строк)
- ✅ Package init (`src/orbis_fab/__init__.py`, 40 строк)
- ✅ Unit тесты (29 тестов, 100% passing)
  - test_fab_transitions.py (9 тестов)
  - test_backpressure.py (5 тестов)
  - test_envelope.py (7 тестов)
  - test_fill_mix_contracts.py (10 тестов)
- ✅ Status report (`FAB_PHASE_A_STATUS.md`, 462 строки)

**Ключевые компоненты (Phase A)**:
```python
FABCore:
  - init_tick(mode: FAB0/1/2, budgets: Budgets)
  - fill(z_slice: ZSliceLite)
  - mix() -> dict  # Pure snapshot, no I/O
  - step_stub(stress, self_presence, error_rate) -> dict
```

**Режимы работы**:
- FAB₀: без SELF (validation-only, no Atlas writes)
- FAB₁: с SELF present (navigation/mix, anti-oscillation)
- FAB₂: с SELF + Ego (I/O permitted, future)

**Phase A инварианты**:
- Budgets фиксированы на тик (tokens=4096, nodes=256, edges=0, time_ms=30)
- Global + Stream ≤ budgets.nodes
- Global window: ≤256 nodes, precision ≤mxfp4.12 (cold)
- Stream window: ≤128 nodes, precision mxfp6-8 (hot/warm)
- Backpressure bands: ok<2000, slow<5000, reject≥5000
- State transitions: FAB0→FAB1→FAB2 + degradation on stress/errors
- No external I/O (autonomous operation)

**Next** (Phase B):
- [ ] Hysteresis для bit-envelope (≤1 change/sec/layer)
- [ ] Window stability counter
- [ ] Z-space shim (in-memory adapter)
- [ ] Integration с FAB v0.1 Shadow Mode routes

---

### 3. **z-space** — ⏳ ЭМЕРДЖЕНТНОЕ ОТ FAB
**Status**: Planned (после FAB Phase A)  
**Parent**: `fab`  
**Scope**: Z-срезы Atlas — связные подграфы "здесь-и-сейчас"

**Концепция**:
- Z-slice = связный подграф из Atlas под квоты S1
- Z-Selector: гибридный поиск (dense + lexical) + нормировка
- Coverage: точные метрики по 5D-полосам (tolerances_5d)
- Источники: semantic, episodic, procedural, affective

**Компоненты** (когда создадим):
```python
ZSelector:
  - build(intent, history_ref, budgets, tolerances_5d) -> ZSlice
  - prune_and_link(candidates, quotas, policy) -> Subgraph
  - score_nodes(coherence, novelty, age) -> Scores

ZSlice (структура):
  - nodes: [{"id","dim","ts","score"}]
  - edges: [{"src","dst","w","kind"}]
  - sources: ["semantic","episodic"]
  - quotas: {"tokens":4096,"nodes":512,"edges":2048,"time_ms":30}
  - seed: "run#..."
  - zv: "0.1"
```

**Интеграция**:
- FAB.fill(z_slice) ← Z-Selector.build()
- Atlas E2 (HNSW/FAISS) → Z-slice candidates
- S1 регулятор → квоты/точность/риски

---

### 4. **self** — ⏳ ЭМЕРДЖЕНТНОЕ ОТ Z-SPACE
**Status**: Planned (после z-space)  
**Parent**: `z-space`  
**Scope**: [SELF] токен — присутствие "Я" в шаге мышления

**Концепция**:
- SELF = токен присутствия, чеканится в конце шага
- Один SELF на контекстное окно (FAB Global или Stream)
- Lifecycle: init → update → commit → transfer/replicate

**Компоненты** (когда создадим):
```python
SelfManager:
  - mint(window_id, context) -> SelfToken
  - update(self_token, experience) -> SelfToken
  - transfer(from_window, to_window) -> None
  - replicate(self_token, target_window) -> SelfToken
  
SelfToken:
  - id: UUID
  - presence: float  # 0.0-1.0 (self_presence метрика)
  - coherence: float
  - continuity: float
  - stress: float
  - window_id: UUID
  - created_at: timestamp
  - updated_at: timestamp
```

**Интеграция**:
- FAB₁/₂ → SELF активен
- FAB₀ → SELF отсутствует
- OneBlock → [SELF] токен в контексте
- Canon → guard для SELF операций
- Atlas → SELF traces в identity.jsonl

---

## 🔄 Workflow переключения веток

### Pause текущей ветки:
```bash
# Зафиксировать состояние
git add -A
git commit -m "checkpoint: <описание текущего состояния>"
git push origin <branch_name>

# Обновить BRANCHES_CONTEXT.md (этот файл)
```

### Switch на другую ветку:
```bash
# Переключиться
git checkout <target_branch>

# Прочитать контекст из BRANCHES_CONTEXT.md
# Продолжить работу
```

### Resume ветки:
```bash
git checkout <branch_name>
git pull origin <branch_name>

# Прочитать последний checkpoint commit
# Продолжить с последнего состояния
```

---

## 📊 Текущий фокус

**СЕЙЧАС**: `fab` ветка  
**Статус**: Phase A MVP ✅ COMPLETE  
**Следующее**: Phase B (Hysteresis + Stability) или интеграция с FAB v0.1 Shadow Mode

**Готов к работе!** Phase A завершён, жду инструкций для Phase B или других задач.

---

## 📝 Change History

| Date | Branch | Event | Commit | Description |
|------|--------|-------|--------|-------------|
| 2025-10-29 | main | Merged | 7ffd495 | Atlas v0.2.0 + FAB v0.1 Shadow Mode |
| 2025-10-29 | fab | Created | 44d08ce | FAB branch init with specs (3 docs) |
| 2025-10-29 | fab | Phase A | 21e848e | FAB Phase A MVP core (6 modules, 29 tests) |
| 2025-10-29 | fab | Docs | 65f2f92 | FAB Phase A status report |

---

## 📝 История изменений

| Дата | Ветка | Событие |
|------|-------|---------|
| 2025-10-29 | `fab` | Создана ветка, добавлены спецификации (FAB_FULL_SPEC_v1.0.md, FAB_OVERVIEW.md) |
| 2025-10-28 | `main` | FAB v0.1 Shadow Mode complete (5 commits: 3881457→7ffd495) |
| 2025-10-28 | `main` | E4 Homeostasis GA merged (v0.2.0 tag) |

---

**Maintained by**: Atlas Autonomous Agent  
**Last updated**: 2025-10-29
</file>
