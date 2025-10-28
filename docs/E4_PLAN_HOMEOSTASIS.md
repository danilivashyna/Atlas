# E4: Homeostasis & Auto-Healing Loop

**Дата:** 27 октября 2025  
**Статус:** 📋 PLANNING  
**Epic:** E4 — Замкнутый контур саморегуляции

---

## 🎯 Замысел E4

E4 замыкает контур **самосознания системы**: метрики осознанности (E3) → решения (политики) → действия (ремонт/тюнинг) → аудит → метрики. Цель — удерживать Atlas в **"здоровом коридоре"** автоматически, без простоев:

- Обнаруживать деградации (drift, coherence loss, латентность)
- Локально чинить память (rebuild shards, re-embed)
- Управлять параметрами поиска (tune ef_search, nprobe)
- Версионировать состояние (snapshots, rollback)
- Логировать всё (WAL, audit trail)

**Петля гомеостаза:**
```
Observe (E3) → Decide (политики) → Act (ремонт/тюнинг) → Reflect (аудит) → Observe
```

---

## 🏗️ Архитектурная связность

### E1 → E2 → E3 → **E4** (Гомеостаз)

**E1 (Grammar):** Как говорить
- Pydantic schemas, FastAPI routes, FAB router
- **Роль в E4:** Контракты для /health/decisions, /actions/*, /audit

**E2 (Vocabulary):** Какие слова существуют
- HNSW/FAISS indices, MANIFEST, integrity verification
- **Роль в E4:** Цели для rebuild/reembed, snapshot/rollback

**E3 (Self-awareness):** Как хорошо я говорю
- H-Coherence, H-Stability, Prometheus metrics
- **Роль в E4:** Источники сигналов для Policy Engine

**E4 (Homeostasis):** Как остаться здоровым
- Policy Engine, Decision Engine, Action Adapters, Snapshot/Rollback, Audit/WAL
- **Роль:** Замкнуть контур самосознания → самоизлечения

### Метафора: Организм

```
E1 = Язык       (как выражать намерения)
E2 = Память     (что помнить)
E3 = Сознание   (как я себя чувствую)
E4 = Гомеостаз  (как остаться в норме)
```

Система становится **организмом**, который:
1. **Общается** (E1 API)
2. **Помнит** (E2 indices)
3. **Осознаёт себя** (E3 metrics)
4. **Лечит себя** (E4 homeostasis)

---

## 📦 Scope E4

### Входит:
- ✅ Policy Engine (YAML-правила реагирования)
- ✅ Decision Engine (интерпретация метрик, анти-флаппинг)
- ✅ Action Adapters (rebuild, reembed, tune, quarantine)
- ✅ Snapshot & Rollback (атомарные снапшоты индексов+MANIFEST)
- ✅ Audit & WAL (идемпотентные записи run_id/op_id)
- ✅ Sleep/Consolidation (ночной "сон" системы)
- ✅ Метрики контура (atlas_decision_count, atlas_repair_success_ratio)
- ✅ SLO (time_to_repair_p95, repair_success, false_positive_rate)

### Не входит:
- ❌ Обучение базовой модели (это отдельный epic)
- ❌ Крупные миграции Atlas (это отдельный epic)
- ❌ Внешние системы мониторинга (только Prometheus export)

---

## 🔬 Компоненты E4

### 1. Policy Engine
**Назначение:** Определяет **правила реагирования** на метрики.

**Функции:**
- Загрузка YAML-политик из `configs/policies/homeostasis.yaml`
- Композитные правила (AND/OR/NOT логика)
- Пороги для H-Coherence, H-Stability, latency, error_rate
- Приоритеты правил (критические vs некритические)
- Dry-run режим (симуляция без действий)

**Пример политики:**
```yaml
policies:
  - name: low_coherence_sent_to_para
    trigger:
      metric: h_coherence_sent_to_para
      operator: "<"
      threshold: 0.78
      duration: 5m  # 5 минут ниже порога
    action:
      type: rebuild_shard
      target: sentence
      max_per_window: 3  # не более 3 rebuild в час
      cooldown: 15m
    priority: high

  - name: high_drift_noise
    trigger:
      metric: h_stability_drift_noise
      operator: ">"
      threshold: 0.08
      duration: 10m
    action:
      type: reembed_batch
      target: top_100_drift_docs
      max_per_window: 1
      cooldown: 30m
    priority: medium
```

**Файлы:**
- `src/atlas/homeostasis/policy.py` (PolicyEngine, PolicySpec)
- `configs/policies/homeostasis.yaml`
- JSON Schema для валидации политик

---

### 2. Decision Engine
**Назначение:** Превращает **метрики** в **решения** с гарантиями безопасности.

**Функции:**
- **Анти-флаппинг:** Cooldown periods (не действовать сразу после action)
- **Rate-limits:** Max actions per window (не более N rebuild в час)
- **Приоритеты:** Критические правила вытесняют некритические
- **Детерминизм:** Seed для воспроизводимости решений
- **Прямая интеграция с E3:** Читает HCoherenceMetric/HStabilityMetric напрямую (не Prometheus)
- **Dry-run:** Режим "что сделаешь при таких метриках?" без выполнения

**Алгоритм:**
```python
for policy in sorted_policies(by_priority):
    if policy.trigger.matches(current_metrics):
        if not in_cooldown(policy) and not rate_limited(policy):
            decision = Decision(
                policy=policy,
                reason=f"{policy.trigger.metric} = {metric_value}",
                action=policy.action,
                dry_run=config.dry_run
            )
            if not dry_run:
                execute_action(decision)
            log_decision(decision)
```

**Файлы:**
- `src/atlas/homeostasis/decision.py` (DecisionEngine, Decision)

---

### 3. Action Adapters
**Назначение:** Выполняют **действия** с pre-checks и rollback.

**Действия:**

**rebuild_shard(level, shard_id)**
- Перестроить HNSW/FAISS шард (не весь индекс)
- Pre-check: Проверка доступности данных, capacity
- Post-check: SHA256 verification нового шарда
- Rollback: Откат к предыдущему снапшоту при ошибке

**reembed_batch(doc_ids)**
- Переэмбеддинг списка документов (топ-100 по drift)
- Pre-check: Проверка доступности encoder
- Post-check: H-Stability должна улучшиться
- Rollback: Восстановление старых векторов

**tune_search_params(level, params)**
- Изменить ef_search (HNSW) или nprobe (FAISS)
- Pre-check: Параметры в допустимых границах
- Post-check: Latency p95 должна улучшиться
- Rollback: Восстановление старых параметров

**quarantine_docs(doc_ids)**
- Поместить шумные документы в карантин (исключить из индексов)
- Pre-check: Проверка threshold шума
- Post-check: H-Coherence должна улучшиться
- Audit: Запись причины карантина

**regenerate_manifest()**
- Перегенерация MANIFEST.v0_2.json с новыми SHA256
- Pre-check: Все индексы доступны
- Post-check: Валидация JSON Schema
- Atomic: Атомарная замена MANIFEST

**Файлы:**
- `src/atlas/homeostasis/actions.py` (ActionAdapter, Action subclasses)

---

### 4. Snapshot & Rollback
**Назначение:** Атомарные снапшоты индексов+MANIFEST для быстрого отката.

**Функции:**
- **Copy-on-write:** Создание снапшота без остановки системы
- **SHA256 verification:** Проверка целостности снапшота
- **Fast rollback:** Откат ≤30 сек (атомарный symlink switch)
- **Retention policy:** Хранить последние N снапшотов (default: 7)
- **Журнал операций:** Audit trail всех snapshot/rollback

**Формат снапшота:**
```
snapshots/
  2025-10-27_18-32-00/
    indices/
      sentence.hnsw
      paragraph.hnsw
      document.faiss
    MANIFEST.v0_2.json
    snapshot_meta.json  # timestamp, reason, metrics at snapshot
```

**Rollback:**
```python
def rollback_to_snapshot(snapshot_id: str):
    # 1. Verify snapshot integrity (SHA256)
    verify_snapshot(snapshot_id)
    
    # 2. Atomic symlink switch
    old_link = Path("data/indices/active")
    new_link = Path(f"snapshots/{snapshot_id}/indices")
    old_link.unlink()
    old_link.symlink_to(new_link)
    
    # 3. Reload app.state.indices
    reload_indices_from_manifest(new_link / "MANIFEST.v0_2.json")
    
    # 4. Log rollback
    audit_log.write(RollbackEvent(snapshot_id=snapshot_id, reason=reason))
```

**Файлы:**
- `src/atlas/homeostasis/snapshot.py` (SnapshotManager)
- `configs/snapshots/policy.yaml` (retention, schedule)

---

### 5. Audit & WAL
**Назначение:** Write-Ahead Log для идемпотентности и прозрачности.

**Функции:**
- **JSONL формат:** Одна строка = одна операция
- **Идемпотентность:** run_id/op_id/step для replay без дубликатов
- **Причина→Действие→Результат:** Полная цепочка для каждого решения
- **Фильтры:** По времени, типу операции, статусу
- **API /api/v1/audit:** Просмотр и экспорт аудита
- **Экспорт в /metrics:** Счётчики atlas_audit_*

**Формат WAL записи:**
```json
{
  "run_id": "20251027_183200_homeostasis",
  "op_id": "rebuild_shard_sentence_001",
  "step": "pre_check",
  "timestamp": "2025-10-27T18:32:05Z",
  "policy": "low_coherence_sent_to_para",
  "trigger": {
    "metric": "h_coherence_sent_to_para",
    "value": 0.75,
    "threshold": 0.78
  },
  "action": {
    "type": "rebuild_shard",
    "target": "sentence",
    "shard_id": "001"
  },
  "status": "success",
  "duration_sec": 12.5,
  "before_metrics": {"coherence": 0.75},
  "after_metrics": {"coherence": 0.82}
}
```

**Файлы:**
- `src/atlas/homeostasis/audit.py` (AuditLog, WALWriter)
- `data/audit/homeostasis.jsonl` (append-only log)

---

### 6. Sleep & Consolidation
**Назначение:** Ночной "сон" системы для оптимизации и очистки.

**Функции:**
- **Дефрагментация индексов:** Удаление tombstones, оптимизация структуры
- **Сжатие векторов:** Quantization тихих измерений
- **Перекалибровка порогов:** Обновление H-Coherence/H-Stability thresholds на основе истории
- **Агрегация метрик:** Подсчёт статистики за день (p50/p95/p99)
- **Отчёт о изменениях:** Сколько векторов сжато, сколько индексов оптимизировано

**Расписание:**
```yaml
schedules:
  - name: nightly_sleep
    cron: "0 3 * * *"  # 03:00 каждую ночь
    actions:
      - defragment_indices
      - compress_vectors
      - recalibrate_thresholds
      - aggregate_metrics
    timeout: 30m
    on_failure: alert_ops
```

**Отчёт после "сна":**
```json
{
  "sleep_run_id": "20251027_030000_sleep",
  "duration_sec": 1200,
  "actions_completed": 4,
  "defragmentation": {
    "indices_optimized": 3,
    "tombstones_removed": 1523,
    "space_saved_mb": 45
  },
  "compression": {
    "vectors_compressed": 10000,
    "dimensions_quantized": 128,
    "space_saved_mb": 120
  },
  "recalibration": {
    "h_coherence_threshold_updated": {"old": 0.78, "new": 0.80},
    "h_stability_threshold_updated": {"old": 0.08, "new": 0.06}
  }
}
```

**Файлы:**
- `src/atlas/homeostasis/sleep.py` (SleepManager, Consolidator)
- `configs/schedules/cron.yaml`

---

## 🌐 API Routes

### GET /api/v1/health/decisions
**Назначение:** Последние решения Decision Engine.

**Response:**
```json
{
  "last_decisions": [
    {
      "decision_id": "20251027_183205_rebuild_001",
      "policy": "low_coherence_sent_to_para",
      "trigger": {
        "metric": "h_coherence_sent_to_para",
        "value": 0.75,
        "threshold": 0.78
      },
      "action": {
        "type": "rebuild_shard",
        "target": "sentence",
        "shard_id": "001"
      },
      "status": "completed",
      "duration_sec": 12.5,
      "improvement": {"coherence": 0.82}
    }
  ],
  "active_cooldowns": [
    {
      "policy": "low_coherence_sent_to_para",
      "cooldown_until": "2025-10-27T18:47:00Z"
    }
  ]
}
```

---

### POST /api/v1/policies/test
**Назначение:** Симуляция "что сделаешь при таких метриках?".

**Request:**
```json
{
  "metrics": {
    "h_coherence_sent_to_para": 0.75,
    "h_stability_drift_noise": 0.05
  },
  "dry_run": true
}
```

**Response:**
```json
{
  "decisions": [
    {
      "policy": "low_coherence_sent_to_para",
      "would_trigger": true,
      "action": "rebuild_shard",
      "reason": "h_coherence_sent_to_para (0.75) < 0.78",
      "dry_run": true
    }
  ]
}
```

---

### POST /api/v1/actions/rebuild
**Назначение:** Таргетная перестройка индекса/шарда.

**Request:**
```json
{
  "level": "sentence",
  "shard_id": "001",
  "reason": "manual_rebuild_after_data_update"
}
```

**Response:**
```json
{
  "action_id": "20251027_183500_rebuild_002",
  "status": "started",
  "estimated_duration_sec": 15
}
```

---

### POST /api/v1/actions/reembed
**Назначение:** Переэмбеддинг списка объектов/шарда.

**Request:**
```json
{
  "doc_ids": ["doc_001", "doc_042", "doc_123"],
  "reason": "high_drift_detected"
}
```

**Response:**
```json
{
  "action_id": "20251027_183600_reembed_003",
  "status": "started",
  "docs_to_reembed": 3,
  "estimated_duration_sec": 8
}
```

---

### GET /api/v1/audit
**Назначение:** Просмотр WAL/аудита.

**Query params:**
- `run_id` (filter by run)
- `op_id` (filter by operation)
- `start_time` / `end_time` (time range)
- `status` (success/failure/in_progress)
- `limit` (max records)

**Response:**
```json
{
  "entries": [
    {
      "run_id": "20251027_183200_homeostasis",
      "op_id": "rebuild_shard_sentence_001",
      "timestamp": "2025-10-27T18:32:05Z",
      "status": "success",
      "duration_sec": 12.5
    }
  ],
  "total": 42,
  "has_more": true
}
```

---

### POST /api/v1/sleep/run
**Назначение:** Ручной запуск консолидации (не дожидаясь cron).

**Request:**
```json
{
  "actions": ["defragment_indices", "compress_vectors"],
  "dry_run": false
}
```

**Response:**
```json
{
  "sleep_run_id": "20251027_184000_sleep_manual",
  "status": "started",
  "estimated_duration_sec": 1200
}
```

---

## 📊 Метрики контура

### atlas_decision_count{type, status}
**Тип:** Counter  
**Описание:** Количество решений Decision Engine.

**Labels:**
- `type`: rebuild_shard, reembed_batch, tune_params, quarantine, etc.
- `status`: triggered, executed, skipped_cooldown, skipped_rate_limit

**Пример:**
```
atlas_decision_count{type="rebuild_shard", status="executed"} 12
atlas_decision_count{type="rebuild_shard", status="skipped_cooldown"} 3
```

---

### atlas_action_duration_seconds{action}
**Тип:** Histogram  
**Описание:** Длительность выполнения действий.

**Labels:**
- `action`: rebuild_shard, reembed_batch, tune_params, etc.

**Buckets:** [1, 5, 10, 30, 60, 120, 300]

**Пример:**
```
atlas_action_duration_seconds_bucket{action="rebuild_shard", le="30"} 10
atlas_action_duration_seconds_sum{action="rebuild_shard"} 125.5
atlas_action_duration_seconds_count{action="rebuild_shard"} 12
```

---

### atlas_repair_success_ratio
**Тип:** Gauge  
**Описание:** Доля успешных "починок" (action успешен + метрика улучшилась).

**Формула:**
```
success_ratio = successful_repairs / total_repairs
```

**SLO:** ≥ 0.9 (90% успешных починок)

**Пример:**
```
atlas_repair_success_ratio 0.92
```

---

### atlas_snapshot_age_seconds
**Тип:** Gauge  
**Описание:** Возраст активного снапшота (сколько прошло с момента создания).

**Пример:**
```
atlas_snapshot_age_seconds 3600  # 1 hour
```

---

## 🎯 SLO (Service Level Objectives)

### time_to_repair_p95 ≤ 5m
**Описание:** 95-й перцентиль времени от обнаружения проблемы до её устранения.

**Измерение:**
```
time_to_repair = decision_timestamp - trigger_timestamp + action_duration
```

**Цель:** p95 ≤ 300 сек (5 минут)

---

### repair_success ≥ 0.9
**Описание:** Доля успешных починок (action успешен + метрика улучшилась).

**Измерение:**
```
repair_success = successful_repairs / total_repairs
```

**Цель:** ≥ 0.9 (90%)

---

### false_positive_rate ≤ 0.1
**Описание:** Доля ложных срабатываний (action выполнен, но метрика не улучшилась).

**Измерение:**
```
false_positive_rate = (actions_without_improvement) / total_actions
```

**Цель:** ≤ 0.1 (10%)

---

## ⚠️ Риски и смягчение

### Риск 1: Ложные срабатывания
**Проявление:** Decision Engine запускает rebuild при временной флуктуации метрик.

**Смягчение:**
- ✅ **Анти-флаппинг:** Cooldown periods (15-30 минут после action)
- ✅ **Подтверждение:** Trigger должен быть активен ≥ duration (5-10 минут)
- ✅ **Два сигнала:** Композитные правила (AND логика)
- ✅ **Dry-run:** Тестирование политик без выполнения

---

### Риск 2: Долгие перестройки
**Проявление:** rebuild_shard занимает слишком долго, блокирует другие действия.

**Смягчение:**
- ✅ **Таргетные операции:** rebuild_shard (не весь индекс), reembed_batch (не все документы)
- ✅ **Очереди:** Асинхронное выполнение действий
- ✅ **Backoff:** Экспоненциальная задержка при неудачах
- ✅ **Timeout:** Максимальная длительность действия (default: 5 минут)

---

### Риск 3: Порча индексов
**Проявление:** Action портит индекс, система становится недоступной.

**Смягчение:**
- ✅ **Snapshots:** Атомарные снапшоты перед каждым действием
- ✅ **SHA256 verification:** Проверка целостности до и после
- ✅ **Fast rollback:** Откат ≤30 сек при ошибке
- ✅ **Pre-checks:** Проверка доступности данных, capacity

---

### Риск 4: Конфликт политик
**Проявление:** Две политики запускают противоречащие действия.

**Смягчение:**
- ✅ **Приоритеты:** Критические правила вытесняют некритические
- ✅ **Mutually-exclusive guards:** Политики помечены как несовместимые
- ✅ **Audit:** Подробная запись причин выбора политики
- ✅ **Single-action-per-window:** Ограничение на количество действий в окно

---

## 🔗 Интеграция с E1/E2/E3

### Интеграция с E1 (API & Contracts)
- ✅ **Новые роуты:** /health/decisions, /policies/test, /actions/*, /audit, /sleep/run
- ✅ **Pydantic schemas:** PolicySpec, Decision, Action, AuditEntry, SleepReport
- ✅ **FastAPI integration:** Новые endpoints в routes.py

---

### Интеграция с E2 (Index Builders + MANIFEST)
- ✅ **Безопасные билдеры:** rebuild_shard использует HNSWIndexBuilder/FAISSIndexBuilder
- ✅ **Атомарный MANIFEST-switch:** SnapshotManager интегрируется с MANIFESTGenerator
- ✅ **SHA256 verification:** Использует verify_manifest_integrity() из E2.3

---

### Интеграция с E3 (H-metrics Framework)
- ✅ **Прямое чтение метрик:** PolicyEngine читает HCoherenceMetric/HStabilityMetric напрямую
- ✅ **Не scrape Prometheus:** Избегаем задержки scrape interval
- ✅ **Trigger на основе E3:** Все политики используют atlas_h_coherence, atlas_h_stability

---

## 🚀 Мильстоуны (Acceptance Criteria)

### E4.1: Policy Engine & Spec
- [ ] YAML-схема политик (triggers, actions, priorities)
- [ ] Композитные правила (AND/OR/NOT логика)
- [ ] Dry-run режим симуляции
- [ ] Unit-тесты на граничные кейсы (edge cases)
- [ ] JSON Schema валидация политик

**Файлы:**
- `src/atlas/homeostasis/policy.py`
- `configs/policies/homeostasis.yaml`
- `tests/test_policy_engine.py`

---

### E4.2: Decision Engine
- [ ] Анти-флаппинг (cooldown periods)
- [ ] Rate-limits (max actions per window)
- [ ] Приоритеты правил
- [ ] Детерминированные решения (seed)
- [ ] Прямая интеграция с E3 метриками

**Файлы:**
- `src/atlas/homeostasis/decision.py`
- `tests/test_decision_engine.py`

---

### E4.3: Action Adapters
- [ ] rebuild_shard с pre-checks
- [ ] reembed_batch с rollback
- [ ] tune_search_params с latency check
- [ ] quarantine_docs с audit
- [ ] regenerate_manifest с atomic switch

**Файлы:**
- `src/atlas/homeostasis/actions.py`
- `tests/test_action_adapters.py`

---

### E4.4: Snapshot & Rollback
- [ ] Атомарные снапшоты (copy-on-write)
- [ ] SHA256 verification
- [ ] Откат ≤30 сек
- [ ] Retention policy (последние N)
- [ ] Журнал операций snapshot/rollback

**Файлы:**
- `src/atlas/homeostasis/snapshot.py`
- `configs/snapshots/policy.yaml`
- `tests/test_snapshot_manager.py`

---

### E4.5: Audit & WAL
- [ ] JSONL формат (run_id/op_id/step)
- [ ] Идемпотентные записи
- [ ] Фильтры по времени/типу/статусу
- [ ] API /api/v1/audit
- [ ] Экспорт счётчиков в /metrics

**Файлы:**
- `src/atlas/homeostasis/audit.py`
- `tests/test_audit_log.py`

---

### E4.6: Sleep & Consolidation
- [ ] Дефрагментация индексов
- [ ] Сжатие векторов (quantization)
- [ ] Перекалибровка порогов
- [ ] Агрегация метрик
- [ ] Отчёт о изменениях

**Файлы:**
- `src/atlas/homeostasis/sleep.py`
- `configs/schedules/cron.yaml`
- `tests/test_sleep_manager.py`

---

### E4.7: Health & Audit Routes
- [ ] GET /api/v1/health/decisions
- [ ] POST /api/v1/policies/test
- [ ] POST /api/v1/actions/rebuild
- [ ] POST /api/v1/actions/reembed
- [ ] GET /api/v1/audit
- [ ] POST /api/v1/sleep/run

**Файлы:**
- `src/atlas/api/routes.py` (updated)
- `src/atlas/api/schemas.py` (updated)
- `tests/test_homeostasis_routes.py`

---

### E4.8: Homeostasis Metrics
- [ ] atlas_decision_count{type, status}
- [ ] atlas_action_duration_seconds{action}
- [ ] atlas_repair_success_ratio
- [ ] atlas_snapshot_age_seconds
- [ ] SLO dashboard config

**Файлы:**
- `src/atlas/api/routes.py` (updated /metrics)
- `configs/prometheus/slo_dashboard.json`

---

## 🔄 Далее (E5/E6)

### E5: IR-метрики качества поиска
- Recall@k, nDCG@k, MRR (Mean Reciprocal Rank)
- Латентность (p50/p95/p99)
- Контент-валидаторы (semantic relevance)

### E6: Active Learning
- Ручная разметка примеров
- Выборка hard negatives
- Дообучение эмбеддингов
- Feedback loop (user feedback → reranking)

---

## 📝 Примечания

**Связность E1→E2→E3→E4:**
```
E1 (Grammar)       → E4 использует API контракты
E2 (Vocabulary)    → E4 управляет индексами
E3 (Self-awareness) → E4 реагирует на метрики
E4 (Homeostasis)    → Замыкает контур саморегуляции
```

**Метафора организма:**
- E1 = Язык (как выражать)
- E2 = Память (что помнить)
- E3 = Сознание (как я себя чувствую)
- E4 = Гомеостаз (как остаться здоровым)

**Итог:** Atlas становится **самовосстанавливающимся организмом**, который не только помнит, но и **заботится о себе**.

---

**Статус:** 📋 READY TO START  
**Следующий шаг:** E4.1 (Policy Engine & Spec)
