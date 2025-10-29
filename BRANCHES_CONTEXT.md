# Atlas Multi-Branch Development Context

**Date**: 2025-10-29  
**Strategy**: Параллельная разработка с эмерджентными зависимостями  

---

## 🌳 Структура веток

```
main (Atlas v0.2.0 E4 GA)
  ↓
  ├─► fab (Fractal Associative Bus) ← ТЕКУЩАЯ
  │    ├─► z-space (эмерджентное от FAB)
  │    │    └─► self (эмерджентное от Z-space)
  │    │
  │    └─► [другие ветки FAB]
  │
  └─► [другие ветки Atlas]
```

---

## 📋 Branches Roadmap

### 1. **Atlas** (main) — ⏸️ НА ПАУЗЕ
**Status**: v0.2.0 GA (E4 Homeostasis Complete)  
**Last commit**: `7ffd495` (FAB_PHASE1_COMPLETE.md)  
**Components**:
- ✅ E1 API (FastAPI, health, validation)
- ✅ E2 Index Builders (HNSW, FAISS, MANIFEST)
- ✅ E3 Metrics (h_coherence, h_stability, Prometheus)
- ✅ E4 Homeostasis (OODA loop: E4.1-E4.8)
- ✅ FAB Integration v0.1 (Shadow Mode: 4 routes, 11 tests)

**Next** (когда вернёмся):
- FAB Phase 2 (Mirroring): FAB cache + E2 write-through
- FAB Phase 3 (Cutover): E4 actions + SLO monitors
- v0.3 Memory Persistence (PostgreSQL + Redis)

**Контекст сохранён в**:
- `FAB_v0.1_STATUS.md` (315 lines)
- `FAB_PHASE1_COMPLETE.md` (completion report)
- `docs/AURIS_FAB_Integration_Plan_v0.1.txt`

---

### 2. **fab** — 🔥 ТЕКУЩАЯ ВЕТКА
**Status**: Phase A (MVP) — ✅ COMPLETE  
**Base**: `main` (Atlas v0.2.0)  
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
