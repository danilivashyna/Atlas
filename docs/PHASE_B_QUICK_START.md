# Phase B → SELF: Quick Start Guide

**Статус:** 🚀 Ready to Start  
**Дата создания:** 2025-11-02  
**Базовая ветка:** `jbarton43/z-space`

---

## 🎯 Что уже сделано (Baseline)

✅ **Atlas + FAB + Z-Space собраны**
- 207 тестов проходят
- Pylint 9.44/10
- 0 warnings в исправленных файлах
- Все основные модули работают

✅ **Созданы ветки Phase B:**
```bash
phaseB/hysteresis       # B1: Анти-дребезг
phaseB/stability        # B2: Window Stability Counter
phaseB/shim-telemetry   # B3: Z-Space телеметрия
```

✅ **Документация готова:**
- `docs/PHASE_B_ROADMAP.md` - полная дорожная карта
- `docs/slo/PHASE_B_SLO_SLI.md` - метрики и SLO
- `docs/pr_templates/PR_B1_HYSTERESIS.md` - шаблон PR

---

## 🚀 Как начать работу

### Вариант 1: Начать с B1 (Hysteresis)

```bash
# Переключиться на ветку
git checkout phaseB/hysteresis

# Создать файл модуля
touch src/orbis_fab/hysteresis.py
touch tests/test_bit_envelope_hysteresis.py

# Установить hypothesis для property-based тестов
pip install hypothesis

# Начать разработку
code src/orbis_fab/hysteresis.py
```

**Срок:** 2 дня (D1-D2)  
**Acceptance criteria:** См. `docs/PHASE_B_ROADMAP.md#b1`

### Вариант 2: Начать с B2 (Stability)

```bash
git checkout phaseB/stability
touch src/orbis_fab/stability.py
touch tests/test_window_stability.py
code src/orbis_fab/stability.py
```

**Срок:** 1 день (D3)

### Вариант 3: Начать с B3 (Telemetry)

```bash
git checkout phaseB/shim-telemetry
code src/orbis_fab/zspace_shim.py  # уже существует, нужно дополнить
touch tests/test_zspace_telemetry.py
```

**Срок:** 1 день (D4)

---

## 📋 7-дневный план (краткий)

| День | Задача | Ветка | Deliverables |
|------|--------|-------|--------------|
| **D1-D2** | B1: Hysteresis | `phaseB/hysteresis` | `BitEnvelopeHysteresis` + тесты + метрики |
| **D3** | B2: Stability | `phaseB/stability` | `WindowStabilityCounter` + EMA + триггеры |
| **D4** | B3: Telemetry | `phaseB/shim-telemetry` | Метрики + фича-флаг + квоты |
| **D5** | Load Testing | все ветки | Нагрузочные прогоны + профилирование |
| **D6-D7** | Stabilization | все ветки | Багфиксы + docs + SELF skeleton |

---

## 🎯 SLO Targets (краткая справка)

### B1: Hysteresis
- `oscillation_rate_p95 < 0.1` (10% окон)
- `stability_latency_p50 < 2s` (быстрая стабилизация)
- `switch_rate_max ≤ 1.0/sec` (1 переключение/сек)

### B2: Stability
- `stability_score_p50 > 0.8` (80% окон стабильны)
- `stability_score_p95 > 0.6` (даже worst-case >60%)
- `degradation_events < 10/hour` (редкие деградации)

### B3: Z-Space Telemetry
- `zspace_latency_p95 < 50ms` (быстрый selector)
- `zspace_coverage_p50 > 0.8` (80% покрытие)
- `budget_violations < 5%` (редкие превышения)

---

## 🧪 Как запустить тесты

```bash
# Все тесты
pytest -v

# Только новые Phase B тесты
pytest -v tests/test_bit_envelope_hysteresis.py
pytest -v tests/test_window_stability.py
pytest -v tests/test_zspace_telemetry.py

# С покрытием
pytest --cov=src/orbis_fab --cov-report=html

# Property-based (много примеров)
pytest tests/test_bit_envelope_hysteresis.py --hypothesis-show-statistics
```

---

## 📊 Метрики и мониторинг

### Экспорт Prometheus метрик

```python
# В src/atlas/metrics/mensum.py добавить:
from prometheus_client import Counter, Gauge, Histogram

# Hysteresis
bit_envelope_switches = Counter(
    'atlas_bit_envelope_switches_total',
    'Total bit envelope layer switches',
    ['layer']
)

oscillation_ratio = Gauge(
    'atlas_oscillation_windows_ratio',
    'Ratio of oscillating windows'
)

stability_latency = Histogram(
    'atlas_stability_latency_seconds',
    'Time to reach stability',
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0]
)
```

### Grafana Dashboard

После реализации создать dashboard:
- URL: `/grafana/d/phase-b-overview`
- Панели: Health Score, SLO Compliance, Alerts
- Обновить `docs/slo/PHASE_B_SLO_SLI.md#grafana-dashboards`

---

## 🚨 Алерты (краткая справка)

### P0 Critical (response: 15min)
- `oscillation_rate_p95 > 0.2`
- `stability_score_p50 < 0.5`
- `zspace_latency_p95 > 200ms`

### P1 High (response: 1hour)
- `oscillation_rate_p95 > 0.15`
- `degradation_events > 15/hour`
- `zspace_latency_p95 > 100ms`

---

## 🔗 Полезные ссылки

### Документация
- [Phase B Roadmap](../docs/PHASE_B_ROADMAP.md) - полный план
- [SLO/SLI Metrics](../docs/slo/PHASE_B_SLO_SLI.md) - метрики
- [PR Template B1](../docs/pr_templates/PR_B1_HYSTERESIS.md) - шаблон PR

### Код
- `src/orbis_fab/core.py` - FAB orchestrator
- `src/atlas/metrics/mensum.py` - Prometheus metrics
- `tests/conftest.py` - pytest fixtures

### Ветки
```bash
git branch -a | grep phaseB
  phaseB/hysteresis
  phaseB/stability
  phaseB/shim-telemetry
```

---

## ⚡ Quick Commands

```bash
# Переключиться на Phase B ветку
git checkout phaseB/hysteresis

# Создать новый модуль
touch src/orbis_fab/{module_name}.py
touch tests/test_{module_name}.py

# Запустить тесты + lint
pytest -v && pylint src/orbis_fab/{module_name}.py

# Проверить coverage
pytest --cov=src/orbis_fab --cov-report=term-missing

# Создать PR
git add .
git commit -m "feat(phaseB): implement {feature}"
git push origin phaseB/{branch_name}
# Затем открыть PR на GitHub
```

---

## 🎯 Definition of Done (Phase B)

Когда все 4 компонента (B1-B4) будут готовы:

✅ **Технически:**
- [ ] Все тесты проходят (207+ passed)
- [ ] Pylint ≥9.4/10
- [ ] Новые метрики экспортируются
- [ ] SLO compliance >90%

✅ **Документация:**
- [ ] Design docs завершены
- [ ] Runbooks написаны
- [ ] MODEL_CARD.md обновлен
- [ ] API docs актуальны

✅ **Готовность к SELF:**
- [ ] Скелет `SelfManager` создан
- [ ] `SelfToken` dataclass определен
- [ ] Протокол передачи spec готов

---

**Следующий шаг:** SELF Implementation (Phase C)  
**Вопросы:** Открой issue или спроси в Slack #atlas-dev

---

🚀 **Удачи в Phase B!** Давай построим надежную основу для SELF! 💪
