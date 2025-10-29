# FAB · Full Specification v1.0 (Orbis Mens)

**Status:** READY • **License:** Dual (AGPLv3 + Commercial) • **Repo:** `FAB` • **Package:** `orbis_fab`  
**Scope:** Полный ввод в FAB с контекстом Atlas/HSI/OneBlock и точными интерфейсами для интеграции.  
**Audience:** Разработчики ядра FAB, авторы адаптеров Atlas, владельцы CANON‑политик, владельцы OneBlock.

---

## 0) Коротко (executive)

- **FAB** — *оперативная шина осознания*: не хранит знания, а удерживает **активный смысл** шага мышления между **S0/S1/S2**, **Atlas** и **OneBlock**.  
- Работает в **трёх режимах**: **FAB₀** (без Self), **FAB₁** (с Душой/SELF), **FAB₂** (с Z‑пространством и Эго).  
- Имеет **два окна**: **Global** (фон) и **Stream** (текущая мысль/канал).  
- Источник данных — **Z‑slice** из **Atlas**, выбранный **S1** по политике квот/точности/рисков.  
- **Anchors** (Understanding, T→θ_U) задают намерение; **Retrieval** (Knowledge, D→θ_K) подтягивает фрагменты.  
- **[SELF]** чеканится при закрытии шага; запись в **Atlas** атомарна через **Glue** при допуске **Canon**.

Диаграмма потока:

```
Intent → Understanding(Anchors) → Z-Selector(Atlas) → Z-slice
              ↓                                   ↓
          FAB.fill(global|stream, mode FAB0/1/2) → OneBlock ↔ [SELF]
              ↓
       Canon.guard → Glue.commit (WAL, idempotent) → Atlas
```

---

## 1) Контекст (HSI / Atlas / OneBlock)

### 1.1 Слои HSI (типы, параллельная работа)
- **S0 — Бессознательное (Shadow):** непрерывные суперпозиции; порождает варианты/ветви.
- **S1 — Подсознание (Soul emergent):** регулятор/маршрутизатор; **выбирает Z‑slice**; управляет **bit‑envelope** и квотами; удерживает **SELF** в FAB₁.
- **S2 — Я+Эго (Conscious interface):** фильтры/этика/персоны; фиксирует опыт во внешнем контуре; участвует в FAB₂.

Все типы слоёв работают **параллельно** и **асинхронно**; синхронизация — в **точках интеграции**.

### 1.2 Atlas
- Многодоменная память: **semantic / episodic / procedural / affective**.
- Индексы: **HNSW/IVF** + **BM25/lexical**; версии/эпохи → `atlas_manifest.json` (см. Atlas spec).
- **Z‑slice** — связный подграф «здесь‑и‑сейчас» под квоты S1.

### 1.3 OneBlock
- Атом шага: **D (Diffuse) ↔ FAB ↔ T (Transformer)** + `[SELF]`.
- **T → Understanding (θ_U)** — меньшая матрица, DP‑режим, выдаёт **anchors** (структурные опоры).
- **D → Knowledge (θ_K)** — большая матрица, диффузионно‑подобная логика (all‑token denoising), выдаёт **поле знания**.

---

## 2) FAB: режимы, окна, инварианты

### 2.1 Режимы
- **FAB₀:** `(D, FAB, T)` **без SELF**. Автоматические паттерны.  
- **FAB₁:** `(D, FAB, T)` **с Душой/SELF**. Навигация подсознания, удержание присутствия.  
- **FAB₂:** `(D, FAB, T)` **с Z‑пространством и Эго**. Контакт с внешним миром, фиксация опыта.

**Инварианты:**  
1) В FAB₀ запись в Atlas запрещена. 2) Переходы FAB₀↔FAB₁↔FAB₂ управляются **стрессом**, **self_presence** и **ok** шага.  
3) **SELF** отсутствует в FAB₀, проявлен в FAB₁, полностью активен в FAB₂.

### 2.2 Окна
- **Global FAB window** — фоновые опоры (Self/этика/история), низкая частота обновления, `bit ≤ mxfp4.12`.
- **Stream FAB window** — текущая мысль/ветвь, быстрые апдейты, допускает `mxfp6–mxfp8`.

**Правило:** анкор живёт в одном «главном» окне, и временно может зеркалиться в другое по решению S1 (≤25%).

### 2.3 Bit‑Envelope
- Динамическая разрядность: `mxfp8 … mxfp3.xx`  
- Горячие элементы повышаются быстро (**spike**), охлаждение медленнее (**stabilize**), не чаще 1/сек на слой.  
- Старые слои — **пучки** (суммарно ~`mxfp4`) с мгновенной разгруппировкой по спросу.

---

## 3) Данные и интерфейсы

### 3.1 Z‑slice (минимум)
```json
{
  "nodes": [{"id":"n1","dim":1536,"ts":"...", "score":0.83}, ...],
  "edges": [{"src":"n1","dst":"n7","w":0.42,"kind":"supports"}, ...],
  "sources": ["semantic","episodic"],
  "quotas": {"tokens":4096,"nodes":512,"edges":2048,"time_ms":30},
  "seed": "run#…",
  "zv": "0.1"
}
```

### 3.2 Anchor (ссылка)
См. `Anchors Spec v0.1`: `owner, source, emb/tokens, weight, freshness, bit_envelope, fab_window, links.*`.  
В FAB используются только **поля маршрутизации** и **веса/новизна**.

### 3.3 Протоколы (Python, сжато)
```python
# src/orbis_fab/protocols.py
class ZSelector(Protocol):
    def build(self, *, intent:str, history_ref:str|None, budgets:dict, tolerances_5d:dict) -> ZSlice: ...

class Canon(Protocol):
    def guard(self, event:dict) -> tuple[bool, str|None]: ...

class Glue(Protocol):
    def commit(self, trace:dict) -> None: ...

FabMode = Literal["FAB0","FAB1","FAB2"]
```

### 3.4 FABCore API
```python
# src/orbis_fab/core.py
class FABCore:
    def init_tick(self, *, mode: FabMode, budgets: dict, tolerances_5d: dict, bit_policy: dict): ...
    def fill(self, z: ZSlice): ...
    def mix(self, anchors: AnchorsT) -> dict: ...
    def step(self, context: dict, oneblock_call) -> OneBlockResp: ...
    def maybe_commit(self, trace_sig: dict): ...
```
---

## 4) Алгоритмы (v1.0, минимально рабочие)

### 4.1 Z‑Selector (адаптер Atlas)
1) Собрать anchors из Understanding.  
2) Сформировать гибридный запрос (dense + lexical) с нормировкой вкладов.  
3) Выбрать связный подграф под квоты `quotas`.  
4) Проставить `score` узлам (coherence/novelty/age), записать `seed` и `zv`.  
5) Вернуть `Z‑slice` (см. 3.1).

### 4.2 Mix (внутри FAB)
- Взять top‑K по `score` из Z‑slice в **Stream**, фоновый набор в **Global**.  
- Учесть **bias** (self/task) и **stress_tax** (снижение риска при высоком стрессе).  
- Обновить **bit‑envelope** согласно политике (горячее — mxfp6+).

### 4.3 Step (вызов OneBlock)
- Передать контекст: `S` (узлы), `anchors_T`, текущие `bit/quotas`, `mode`.  
- Получить `OneBlockResp = {used_nodes, anchors_used, error_rate, ok}`.  
- Обновить метрики: `error_rate`, `stress`, `self_presence`.  
- Применить переходы FAB (FAB₀→₁→₂ / деградация в ₁).

### 4.4 Commit (Canon + Glue)
- Сформировать **trace_sig**: `{used, anchors, z_seed, fab_mode, metrics}`.  
- `Canon.guard(trace)` → deny/allow (+ причина).  
- При allow → `Glue.commit(trace)` атомарно (WAL + idempotency).

---

## 5) Политики, пороги и квоты (дефолты)

### 5.1 Переходы и анти‑дребезг
- FAB0 → FAB1: `self_presence ≥ 0.8 ∧ stress < 0.7 ∧ ok`  
- FAB1 → FAB2: устойчиво N=3 тика, `stress < 0.5 ∧ ok`  
- Деградация → FAB1: `stress > 0.7 ∨ error_rate > 0.05`  
- Удержание режима: `hold_ms = 1500`

### 5.2 Z‑slice / FAB квоты
- `nodes ≤ 512`, `edges ≤ 2048`, `tokens ≤ 4096`, `time_ms ≤ 30`  
- `MAX_ACTIVE_GLOBAL = 256`, `MAX_ACTIVE_STREAM = 128`, зеркалирование ≤ 25%

### 5.3 Bit‑Envelope
- `hot ≥ mxfp6.00`, `warm ≈ mxfp5.25`, `cold ≤ mxfp4.12`, шаг ≤ 1/сек/слой.

---

## 6) Инварианты (CANON)

1) **Z‑slice связный**; целостность ссылок/индексов не нарушается.  
2) FAB_global + Σ FAB_streams ≤ CAP(FAB, hw).  
3) В FAB₀ запись в Atlas запрещена.  
4) **Idempotency**: `WID = hash(schema_version, ids, action, payload)`.  
5) **Stress‑safety:** при `stress ≥ 0.7` — только буфер, без коммитов.  
6) Bit‑envelope меняется с гистерезисом; без скачков чаще N/сек.  
7) **One SELF per window**: на контекстное окно — один активный `[SELF]`‑токен.

---

## 7) Телеметрия и журналы `.reports/*.jsonl`

- `z_slice.jsonl` — факт выборки Z‑среза (anchors, quotas, coverage, source).  
- `fab_state.jsonl` — режима FAB, размеры окон, точности, `stress`, `self_presence`.  
- `atlas_update.jsonl` — атомарная запись следа (nodes/edges/valence/age_layer).  
- `identity.jsonl` — `coherence`, `continuity`, `stress` (для BehaviorMapper).

Все записи имеют `schema_version:"1"` и `run_id/op_id` для идемпотентности.

---

## 8) Конфигурация и флаги

- `FAB_MIRRORING=true` — включить Atlas‑адаптеры (иначе заглушки).  
- `FAB_CANON_RULES=./configs/canon.yaml` — правила допуска.  
- `FAB_METRICS_SINK=prom|stdout` — назначение метрик.  
- `FAB_REPORTS_DIR=.reports/` — директория журналов.

---

## 9) API/Псевдокод

```python
def select_z_slice(intent, budgets, policies, now_ts):
    anchors = understanding.make_anchors(intent)
    candidates = knowledge.retrieve(anchors, mix=["semantic","episodic","procedural"], k=K)
    subgraph = s1.prune_and_link(candidates, quotas=budgets, policy=policies)
    log_z_slice(subgraph, anchors, budgets)
    return subgraph

def fill_fab(z_slice, mode: FabMode, bit_envelope):
    g = make_global_window(z_slice, cap=bit_envelope.global_cap)
    streams = make_stream_windows(z_slice, cap=bit_envelope.stream_cap)
    assign_precisions(g, streams, policy=bit_envelope)
    log_fab_state(mode, g, streams)
    return FAB(g, streams, mode)

def commit_experience(trace, s2_filters):
    if not s2_filters.allow(trace): return "blocked"
    with atlas.tx() as tx:
        tx.apply(trace.to_nodes_edges())
        tx.tag_valence(trace.affect())
        tx.stamp_age_layer(trace.layer_type)
        tx.commit()
    log_atlas_update(trace)
    return "ok"
```

---

## 10) Тест‑матрица и SLO

**Unit:**  
- `test_z_selector_adapter_build()` — нормализация Z‑slice + score.  
- `test_fab_core_transitions()` — FAB0→1→2 и деградация.  
- `test_canon_blocks_io()` — deny → без `Glue.commit`.  

**Integration:**  
- `/fab/decide`, `/fab/act/*` под флагом `FAB_MIRRORING`.  
- write‑through в E2 mock; canary‑режим.  

**Property‑based:**  
- генерация графов; проверка инвариантов до/после.  

**SLO:**  
- p95 `mix+step` < **100 ms** (|Z|=64), `commit_latency` < **50 ms** (локально).  
- false‑positive(actions) ≤ **1%** (48 ч).  
- Chaos: прерывание любой фазы — повторный запуск доводит до конца (идемпотентно).

---

## 11) Roadmap (v0.2+)

- **Anchors v0.2:** merge/split (LSH), анти‑коллизия, novelty‑budget.  
- **Z‑coverage:** точная метрика по 5D‑полосам, учёт tolerances_5d.  
- **SELF lifecycle:** перенос/репликация SELF‑токена между окнами; следы.  
- **MoE‑routing:** приток экспертов на Retrieval/Linking.  
- **Energy‑aware S1:** бюджеты от железа/температуры/заряда.  
- **Dashboards:** FAB/Atlas/Mensum консоль; канареечные графики.

---

## 12) Глоссарий (минимум)
- **FAB** — Fractal Associative Bus, оперативная шина шага.  
- **Z‑slice** — связный подграф из Atlas «на сейчас».  
- **Anchors** — узлы намерения Understanding (T→θ_U).  
- **[SELF]** — токен присутствия «Я», чеканится в конце шага.  
- **Canon** — политика безопасности/целостности.  
- **Glue** — слой атомарной записи в Atlas (WAL, idempotency).  
- **Bit‑Envelope** — динамическая разрядность онлайн‑обработки.

---

### Приложение A: ASCII‑схема окон и режимов

```
               ┌───────────── FAB Global (фон) ─────────────┐
S0  FAB0  ───▶ │ anchors(self/ethics/history)  bit≤mxfp4.12 │
               └──────────────────▲──────────────────────────┘
                                  │ mirror ≤ 25%
               ┌───────────── FAB Stream (мысль) ────────────┐
S1  FAB1  ───▶ │  Z-slice topK + bias(self,task)  mxfp6–8    │
               └──────────────────┴───────────────▲──────────┘
                                                  │ commit guard
S2  FAB2  ───▶ OneBlock ↔ [SELF] → Canon → Glue → Atlas (atomic)
```

**Конец спецификации v1.0.**
