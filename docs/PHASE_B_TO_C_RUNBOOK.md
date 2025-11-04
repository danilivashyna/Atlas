# AURIS HSI — Phase B → Phase C Runbook

## Scope

Краткий план контролируемого включения **Phase C (SELF)** в staging-окружении с метриками, smoke-тестами и откатом под флагами.

Дополняет артефакты Phase B:
- **B2**: StabilityTracker (runtime integration)
- **B1**: Hysteresis (anti-chatter)
- **B3**: Telemetry (Prometheus /metrics/exp)
- **B4**: CI Quality Gates (GitHub Actions)

---

## CI Ожидания (phaseB_ci.yml)

### Jobs
- **lint-format**: Ruff, Black, Pylint (≥9.3 core, ≥7.5 exp), MyPy (best-effort)
- **unit-tests**: Flags OFF, pytest (54/54 tests), coverage ≥85%
- **exp-smoke**: Flags ON, SELF heartbeat ≥5, Stability/Hysteresis probes, /metrics/exp scrape

### Пороги качества
| Метрика | Threshold | Текущий |
|---------|-----------|---------|
| Pylint (orbis_fab) | ≥9.3/10 | 9.40/10 |
| Pylint (hysteresis_exp) | ≥9.3/10 | 9.67/10 |
| Pylint (exp_prom_exporter) | ≥7.5/10 | 7.55/10 |
| Coverage (total) | ≥85% | ~87% |
| SELF heartbeats | ≥5 | 8 |
| Stability EMA | converges | ✅ |
| Hysteresis switch_rate | ≤1.0/sec | 0.0/sec |

### Артефакты (7 дней retention)
- `exp-logs/identity.jsonl` (SELF heartbeat log)
- `exp-logs/resonance_trace.jsonl` (resonance metrics)

---

## Типичные CI Fails и Фиксы

### 1. Pylint < 9.3 (orbis_fab)
**Причины**:
- f-строки в `logging` (W1309: f-string-without-interpolation)
- Неправильный порядок импортов (C0411: wrong-import-order)
- `import-outside-toplevel` вне feature-флагов

**Фикс**:
```python
# До
logging.info(f"Degradation detected")

# После (lazy formatting)
logging.info("Degradation detected")  # если нет переменных
# или
logging.info("Score: %s", score)  # если есть переменные
```

```python
# Порядок импортов (ruff isort):
# 1) stdlib
# 2) third-party
# 3) first-party
import os
import sys

from fastapi import APIRouter

from atlas.metrics.exp_prom_exporter import ...
```

```python
# import-outside-toplevel только под флагами:
if os.getenv("AURIS_STABILITY", "off") == "on":
    from orbis_fab.stability_hook_exp import attach_to_fab  # OK внутри условия
```

### 2. Coverage < 85%
**Причины**:
- Новые файлы без тестов (orbis_self/bridge.py, atlas/api/app.py)
- Неполное покрытие веток (if/else, try/except)

**Фикс**:
```bash
# Проверяем покрытие локально
make cov

# Смотрим HTML отчёт
pytest --cov=src --cov-report=html
open htmlcov/index.html

# Добавляем тесты для файлов с покрытием < 80%
```

### 3. /metrics/exp пуст (exp-smoke job fails)
**Причины**:
- `AURIS_METRICS_EXP=off` (флаг не включён)
- Exp-роутер не подключён в `app.py`
- uvicorn не стартует (порт занят, ошибка импорта)

**Фикс**:
```bash
# Проверяем локально
export AURIS_METRICS_EXP=on
export AURIS_STABILITY=on
export AURIS_HYSTERESIS=on

uvicorn atlas.api.app:app --port 8000 --log-level error &
sleep 2
curl http://127.0.0.1:8000/metrics/exp

# Должны увидеть:
# atlas_stability_score{window_id="global"} 0.75
# atlas_stability_score_ema{window_id="global"} 0.68
# atlas_recommended_fab_mode{window_id="global"} 0
# atlas_hysteresis_switch_rate_per_sec{window_id="global"} 0.0
# atlas_hysteresis_oscillation_rate{window_id="global"} 0.0
```

```python
# Проверяем app.py
from atlas.api.exp_metrics_routes import router as exp_router

app.include_router(exp_router, prefix="/metrics", tags=["experimental"])
```

---

## Phase C — Контролируемая Активация

### Флаги (по умолчанию OFF)

**Production** (core logic):
```bash
AURIS_SELF=off          # SELF token lifecycle
AURIS_STABILITY=off     # StabilityTracker integration
AURIS_HYSTERESIS=off    # Anti-chatter hysteresis
AURIS_METRICS_EXP=off   # Prometheus /metrics/exp
```

**Staging** (включаем осознанно):
```bash
export AURIS_SELF=on
export AURIS_STABILITY=on
export AURIS_HYSTERESIS=on
export AURIS_METRICS_EXP=on
```

### Smoke-последовательность

```bash
# 1. Unit tests (flags OFF — проверяем, что core не сломан)
make test

# 2. SELF smoke (flags ON)
make self-test
make self-smoke

# 3. Resonance test (SELF heartbeat generation)
AURIS_SELF=on python scripts/resonance_test.py

# 4. Stability + Hysteresis probes
AURIS_STABILITY=on AURIS_HYSTERESIS=on AURIS_METRICS_EXP=on \
  python scripts/stability_probe_exp.py

AURIS_STABILITY=on AURIS_HYSTERESIS=on AURIS_METRICS_EXP=on \
  python scripts/hysteresis_probe_exp.py

# 5. API /metrics/exp scrape
uvicorn atlas.api.app:app --port 8000 --log-level error &
sleep 2
curl http://127.0.0.1:8000/metrics/exp | grep atlas_
kill %1
```

### Целевые метрики (Phase C SLO)

**SELF**:
- `coherence` ≥ 0.80 (внутренняя связность токена)
- `continuity` ≥ 0.90 (стабильность идентичности между тиками)
- `stress` ≤ 0.30 (низкая нагрузка на FABCore)

**Stability** (B2):
- `stability_score_ema` ≥ 0.80 (после стабилизации, ~200 тиков)
- `degradation_events` < 5 (за час)
- `recommended_fab_mode` стабильный (редкие переключения)

**Hysteresis** (B1):
- `switch_rate_per_sec` ≤ 1.0 (SLO: не более 1 переключения/сек)
- `oscillation_rate` ≈ 0 (редукция ≥90%, текущая 98%)
- `dwell_counter` ≥ 50 (тики задержки перед переключением)

---

## Grafana Dashboard

### Импорт
1. Grafana → Dashboards → Import
2. Выбираем файл `dashboards/phase_b_slo_dashboard.json`
3. Выбираем Prometheus datasource
4. Импортируем

### Панели
- **Panel 1**: Stability Score & EMA (dual line, threshold 0.8)
- **Panel 2**: Modes (recommended vs effective vs desired, step graph)
- **Panel 3**: Rates (switch_rate, oscillation_rate, threshold 1.0)
- **Panel 4**: Dwell Ticks (gauge, green ≥50)
- **Panel 5**: Age Ticks (gauge, yellow ≥500)
- **Panel 6-8**: Degradation stats (events, stable_ticks, total count)

### Annotations
- **Degradation Events**: автоматические метки при `changes(atlas_stability_degradation_events[1m]) > 0`

### Алерты (рекомендуемые)
1. **EMA < 0.50** (5 минут) → WARNING
2. **oscillation_rate > 1.0** (1 минута) → CRITICAL
3. **stress > 0.40** (5 минут) → WARNING
4. **switch_rate_per_sec > 1.0** (sustained 2 minutes) → CRITICAL

---

## Rollback План

### Шаг 1: Отключение флагов
```bash
# В .env или systemd unit
AURIS_SELF=off
AURIS_STABILITY=off
AURIS_HYSTERESIS=off
AURIS_METRICS_EXP=off
```

### Шаг 2: Перезапуск сервиса
```bash
# Systemd
sudo systemctl restart atlas-api

# Docker
docker compose restart atlas-api

# Локально
kill $(lsof -ti:8000)
uvicorn atlas.api.app:app --port 8000
```

### Шаг 3: Валидация
```bash
# Unit tests (flags OFF)
make test  # Все 54/54 должны пройти

# Exp-smoke (flags OFF — не должно быть exp-метрик)
curl http://127.0.0.1:8000/metrics/exp
# Ожидаем: 404 или пустой ответ (exp-роутер не активен)

# Или базовые метрики без exp-префикса
curl http://127.0.0.1:8000/metrics
# Ожидаем: стандартные FastAPI метрики
```

### Шаг 4: Аудит
```bash
# Сохраняем артефакты для анализа
cp data/identity.jsonl artifacts/identity_rollback_$(date +%Y%m%d_%H%M%S).jsonl
cp logs/resonance_trace.jsonl artifacts/resonance_rollback_$(date +%Y%m%d_%H%M%S).jsonl

# Анализируем причины отката
grep "ERROR" logs/resonance_trace.jsonl
grep "coherence" data/identity.jsonl | tail -10
```

---

## Phase C Next Steps (после успешного smoke)

### 1. Канареечный запуск (5-10% трафика)
```python
# В FABCore.step_stub()
if os.getenv("AURIS_SELF", "off") == "on":
    import random
    if random.random() < 0.05:  # 5% тиков
        # SELF token update logic
        pass
```

### 2. Prometheus scrape config
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'atlas_exp'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics/exp'
    scrape_interval: 10s
```

### 3. Production deployment
```bash
# После 7 дней успешного staging:
# 1. Merge PR с CI gates как required checks
# 2. Deploy на production с AURIS_*=off
# 3. Включаем флаги постепенно (SELF → Stability → Hysteresis → Metrics)
# 4. Мониторим Grafana dashboard 24/7
```

---

## Контакты и ссылки

- **CI**: https://github.com/danilivashyna/Atlas/actions
- **Docs**: `docs/B{1,2,3,4}_*.md`
- **Grafana**: `dashboards/phase_b_slo_dashboard.json`
- **Scripts**: `scripts/{stability,hysteresis,resonance}_*.py`
- **Tests**: `tests/test_{stability,hysteresis,exp_prom}_*.py`

**Версия**: Phase B.4 Complete (2025-11-04)  
**Статус**: ✅ Ready for Phase C staging smoke
