# SELF Canary Enhancement (Phase C+)

**Status**: ✅ COMPLETED (2025-11-05)  
**Branch**: `jbarton43/z-space`  
**Commit**: `f35184b`

---

## Что сделано

### 🔸 SELF Metrics Export (Prometheus)

**Файл**: `src/atlas/metrics/exp_prom_exporter.py`

Добавлены 4 новых Prometheus gauge:
- `self_coherence{token_id}` — SELF coherence score [0.0, 1.0]
- `self_continuity{token_id}` — SELF continuity score [0.0, 1.0]
- `self_presence{token_id}` — SELF presence score [0.0, 1.0]
- `self_stress{token_id}` — SELF stress metric [0.0, 1.0] (lower is better)

**Функция**: `update_self_metrics(token_id, coherence, continuity, presence, stress)`

**Интеграция**: `src/orbis_self/phase_c_hook_exp.py`
- Автоматический экспорт после каждого `manager.update()`
- Fail-safe: try/except блок (не ломает SELF tick при недоступности Prometheus)

**Тесты**: `tests/test_self_metrics_exp.py` — **4/4 passing** ✅
- Smoke test: метрики попадают в registry
- Disabled gracefully: no-op при AURIS_METRICS_EXP=off
- Multiple tokens: изолированные labels
- Edge values: 0.0 и 1.0 обрабатываются корректно

---

### 🔸 SELF Alerts (warning-tier)

**Файл**: `deploy/alerts/phase_c_rules.yml`

Добавлена группа `auris-self-phase-c` с 3 правилами:

1. **AURIS_SELF_Coherence_Drop**
   - Expr: `avg_over_time(self_coherence[5m]) < 0.80`
   - For: 5m
   - Severity: warning

2. **AURIS_SELF_Continuity_Drop**
   - Expr: `avg_over_time(self_continuity[5m]) < 0.90`
   - For: 5m
   - Severity: warning

3. **AURIS_SELF_Stress_High**
   - Expr: `avg_over_time(self_stress[5m]) > 0.30`
   - For: 5m
   - Severity: warning

**Runbook**: `docs/PHASE_B_TO_C_RUNBOOK.md#self-slo-violations`

---

### 🔸 C1: Snapshot & Replay

**Файл**: `scripts/self_replay_exp.py`

CLI инструмент для анализа SELF heartbeats из `data/identity.jsonl`:
- Вычисляет средние (coherence, continuity, presence, stress)
- Показывает перцентили (p50, p95, p99)
- Валидирует SLO targets (Phase C)
- Опционально сохраняет snapshot в `data/self_state.json`

**Usage**:
```bash
# Анализ последних 50 heartbeats (default)
python scripts/self_replay_exp.py

# Анализ последних 100 heartbeats
python scripts/self_replay_exp.py --count 100

# Сохранить snapshot
python scripts/self_replay_exp.py --save-snapshot
```

**Output**:
```
📊 Analyzing last 20 heartbeats (of 20 total)

📈 Averages:
   coherence    = 1.000
   continuity   = 1.000
   presence     = 1.000
   stress       = 0.140

📊 Percentiles (p50 / p95 / p99):
   coherence    = 1.000 / 1.000 / 1.000
   ...

🎯 SLO Status (Phase C):
   [✅ PASS] coherence >= 0.80    (actual: 1.000)
   [✅ PASS] continuity >= 0.90   (actual: 1.000)
   [✅ PASS] stress <= 0.30       (actual: 0.140)

🟢 ALL SLO TARGETS PASSED
```

---

### 🔸 C2: Auto-tune канарейки

**Файл**: `src/orbis_self/canary_autotune_exp.py`

Автоматическое управление `AURIS_SELF_CANARY` на основе SLO метрик:

**Условия для продвижения** (все должны пройти):
1. `stability_score_ema >= 0.80` (10m avg)
2. `oscillation_rate == 0` (10m avg)
3. `self_coherence >= 0.80` (10m avg)
4. `self_stress <= 0.30` (10m avg)

**Ступенчатое продвижение**:
```
5% → 10% → 25% → 50% → 100%
```

**Откат** при любом SELF/Stability alert (критический или warning).

**Usage**:
```python
from orbis_self.canary_autotune_exp import CanaryAutoTuner

tuner = CanaryAutoTuner(prometheus_url="http://localhost:9090")
decision = tuner.check_and_tune()  # Вызывать каждые 5-10 минут

if decision["action"] == "advance":
    tuner.apply_canary_change(decision["next_canary"])
```

**Note**: В production нужно интегрировать с systemd/ConfigMap для перезапуска сервиса.

---

### 🔸 C3: API для оператора

**Файл**: `src/orbis_self/api_routes_exp.py`

FastAPI router с 2 endpoint'ами:

#### **GET /self/health**

Возвращает текущие SELF метрики и статус canary:

```json
{
  "enabled": true,
  "canary_sampling": 0.05,
  "heartbeat_count": 42,
  "last_heartbeat": {
    "kind": "heartbeat",
    "coherence": 0.95,
    "continuity": 0.98,
    "presence": 1.0,
    "stress": 0.12
  },
  "averages": {
    "coherence": 0.93,
    "continuity": 0.96,
    "presence": 1.0,
    "stress": 0.14
  },
  "slo_status": {
    "coherence_slo": true,
    "continuity_slo": true,
    "stress_slo": true
  }
}
```

#### **POST /self/canary**

Безопасное изменение `AURIS_SELF_CANARY`:

```bash
curl -X POST http://localhost:8000/self/canary \
  -H "Content-Type: application/json" \
  -d '{
    "new_sampling": 0.25,
    "reason": "Advancing to 25% after 24h green metrics"
  }'
```

Response:
```json
{
  "success": true,
  "old_sampling": 0.05,
  "new_sampling": 0.25,
  "reason": "Advancing to 25% after 24h green metrics",
  "note": "⚠️  Restart required: systemctl restart atlas-api"
}
```

**Audit log**: Все изменения логируются с причиной (для compliance).

---

## Проверка прямо сейчас

### 1. Подключить Prometheus alerts

```bash
# Добавить в prometheus.yml
rule_files:
  - '/path/to/Atlas/deploy/alerts/phase_c_rules.yml'

# Reload Prometheus
curl -X POST http://localhost:9090/-/reload
# ИЛИ
kill -HUP $(pgrep prometheus)

# Проверить
# Visit: http://localhost:9090/alerts
# Должно быть видно 13 alert rules (10 Phase B+C + 3 SELF)
```

### 2. Экспортировать флаги и запустить систему

```bash
export AURIS_SELF=on
export AURIS_SELF_CANARY=0.05
export AURIS_STABILITY=on
export AURIS_HYSTERESIS=on
export AURIS_METRICS_EXP=on

# Запустить FABCore tick loop или uvicorn
python scripts/resonance_test.py  # Для генерации heartbeats
```

### 3. Проверить метрики в Prometheus

```bash
# Открыть /metrics/exp
curl http://localhost:8000/metrics/exp | grep self_

# Должно быть:
# self_coherence{token_id="..."}
# self_continuity{token_id="..."}
# self_presence{token_id="..."}
# self_stress{token_id="..."}
```

### 4. Grafana панели (опционально)

Добавить в существующий `dashboards/phase_b_slo_dashboard.json`:

```json
{
  "title": "SELF Metrics",
  "targets": [
    {
      "expr": "avg(self_coherence)",
      "legendFormat": "Coherence (avg)"
    },
    {
      "expr": "avg(self_continuity)",
      "legendFormat": "Continuity (avg)"
    },
    {
      "expr": "avg(self_stress)",
      "legendFormat": "Stress (avg)"
    }
  ]
}
```

### 5. Проверить replay скрипт

```bash
# Анализ последних 20 heartbeats
python scripts/self_replay_exp.py --count 20

# Сохранить snapshot
python scripts/self_replay_exp.py --save-snapshot

# Должен появиться data/self_state.json
cat data/self_state.json
```

### 6. Тестировать API endpoints

```bash
# GET /self/health
curl http://localhost:8000/self/health

# POST /self/canary (с валидацией)
curl -X POST http://localhost:8000/self/canary \
  -H "Content-Type: application/json" \
  -d '{"new_sampling": 0.10, "reason": "Manual test"}'
```

---

## Следующие шаги

### Короткосрочные (24-48 часов)

1. **Интегрировать SELF API в main API** (добавить router в `src/atlas/api/app.py`)
2. **Настроить Grafana dashboard** с 3 SELF панелями
3. **Протестировать auto-tune** (запустить `CanaryAutoTuner.check_and_tune()` в cron каждые 10 минут)

### Среднесрочные (1-2 недели)

1. **Gradual rollout**: 5% → 10% → 25% → 50% → 100%
2. **Production deployment**: копировать конфигурацию на production с canary 5%
3. **Auto-tune automation**: интеграция с systemd/Kubernetes для автоматического перезапуска

### Долгосрочные (Phase D+)

1. **Adaptive SELF activation**: динамическое управление `should_activate_self()` на основе FABCore stress
2. **EGO layer integration** (после SELF стабилизации)
3. **Oneblock architecture** (после EGO)

---

## Статус

✅ **Канарейка 5% LIVE, SELF метрики экспортируются**  
✅ **C1/C2/C3 готовы к использованию**  
⏳ **24-48h мониторинг** → gradual rollout к 25%

**Last commit**: `f35184b` (2025-11-05 12:38 UTC)  
**Tests**: 4/4 passing ✅  
**Branch**: `jbarton43/z-space` (pushed to GitHub)
