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
**Status**: Phase A (MVP) — в разработке  
**Base**: `main` (Atlas v0.2.0)  
**Scope**: FAB Core — оперативная шина осознания

**Спецификация**:
- `docs_fab/FAB_FULL_SPEC_v1.0.md` (полная спецификация)
- `docs_fab/FAB_OVERVIEW.md` (обзор архитектуры)
- `docs_fab/FAB_INTRO_CONTEXT.md` (контекст интеграции)

**Цели Phase A (MVP)**:
- [ ] Ядро FAB (`src/orbis_fab/core.py`)
- [ ] Протоколы адаптеров (`src/orbis_fab/protocols.py`)
- [ ] Политики (`src/orbis_fab/policies.py`)
- [ ] Метрики Mensum (`src/orbis_fab/metrics.py`)
- [ ] Моки адаптеров (`src/orbis_fab/adapters/`)
- [ ] Unit тесты (≥90% coverage)
- [ ] Integration тесты (нулевой цикл)

**Ключевые компоненты**:
```python
FABCore:
  - init_tick(mode: FAB0/1/2, budgets, tolerances_5d, bit_policy)
  - fill(z_slice: ZSlice)
  - mix(anchors: AnchorsT) -> dict
  - step(context, oneblock_call) -> OneBlockResp
  - maybe_commit(trace_sig) -> None
```

**Режимы работы**:
- FAB₀: без SELF (автоматические паттерны)
- FAB₁: с Душой/SELF (навигация подсознания)
- FAB₂: с Z-пространством и Эго (контакт с миром)

**SLO**:
- mix() p95 ≤ 10 ms (1k узлов)
- step() p95 ≤ 5 ms
- commit() ≤ 50 ms
- error_rate ≤ 0.05

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
**Задача**: FAB Phase A (MVP) — ядро + моки адаптеров  
**Следующее**: Unit тесты + Integration тесты

**Готов к работе!** Жду конкретное ТЗ для FAB Phase A.

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
