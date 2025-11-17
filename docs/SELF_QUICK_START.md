# SELF Quick Start Guide

## 🚀 Запуск API с SELF

### Вариант 1: Полный стек (с автотюнером)
```bash
make self-api
```

Запускает API с:
- `AURIS_SELF=on` — SELF система активна
- `AURIS_SELF_CANARY=0.05` — 5% канарейка
- `AURIS_SELF_AUTOTUNE=on` — автоматическое увеличение канарейки
- `AURIS_METRICS_EXP=on` — Prometheus метрики
- Порт: `8000`

### Вариант 2: Быстрый старт (без автотюнера)
```bash
make self-api-quick
```

Для разработки:
- Без автотюнера (`AURIS_SELF_AUTOTUNE=off`)
- С hot-reload (`--reload`)

### Вариант 3: Ручной запуск
```bash
export AURIS_SELF=on
export AURIS_SELF_CANARY=0.05
export AURIS_SELF_AUTOTUNE=on
export AURIS_METRICS_EXP=on
export AURIS_STABILITY=on
export AURIS_HYSTERESIS=on

uvicorn atlas.api.app:app --host 0.0.0.0 --port 8000
```

## 🧪 Проверка работоспособности

### Быстрая проверка метрик
```bash
make self-metrics-check
```

Проверяет:
- `/metrics/exp` — SELF метрики экспортируются
- `/self/health` — эндпоинт доступен

### Полная интеграционная проверка
```bash
make self-integration-check
```

Валидирует:
1. ✅ Экспорт 4 SELF метрик: `coherence`, `continuity`, `presence`, `stress`
2. ✅ `/self/health` отдаёт корректный JSON
3. ℹ️  Автотюнер запущен (проверка в логах)

### Ручная проверка

**Метрики Prometheus:**
```bash
curl http://localhost:8000/metrics/exp | grep self_
```

Ожидаемый вывод:
```
self_coherence{token_id="global"} 1.0
self_continuity{token_id="global"} 0.95
self_presence{token_id="global"} 1.0
self_stress{token_id="global"} 0.14
```

**SELF Health:**
```bash
curl http://localhost:8000/self/health | jq
```

Ожидаемый вывод:
```json
{
  "enabled": true,
  "canary_sampling": 0.05,
  "heartbeat_count": 42,
  "current_metrics": {
    "coherence": 1.0,
    "continuity": 0.95,
    "stress": 0.14,
    "presence": 1.0
  },
  "slo_status": {
    "coherence_ok": true,
    "continuity_ok": true,
    "stress_ok": true
  }
}
```

## 📊 Мониторинг

### Prometheus Recording Rules
Файл: `deploy/alerts/self_recording_rules.yml`

Загрузка в Prometheus:
```yaml
# prometheus.yml
rule_files:
  - /path/to/Atlas/deploy/alerts/self_recording_rules.yml
  - /path/to/Atlas/deploy/alerts/phase_c_rules.yml
```

Перезагрузка:
```bash
curl -X POST http://localhost:9090/-/reload
```

Проверка:
```bash
# Список rules
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[] | select(.name=="auris-self-recording")'

# Проверка recording series
curl -s 'http://localhost:9090/api/v1/query?query=self:coherence:5m_avg' | jq
```

### Grafana Dashboard
Файл: `dashboards/phase_b_slo_dashboard.json`

Панели SELF:
- **Panel 901**: SELF Coherence (5m avg)
- **Panel 902**: SELF Continuity (5m avg)
- **Panel 903**: SELF Stress (5m avg, lower is better)

Импорт:
1. Grafana UI → Dashboards → Import
2. Upload `phase_b_slo_dashboard.json`
3. Verify 11 panels visible (8 old + 3 SELF)

## 🤖 Автотюнер

### Управление
**Включить:**
```bash
export AURIS_SELF_AUTOTUNE=on
```

**Выключить:**
```bash
export AURIS_SELF_AUTOTUNE=off
```

**Настройка интервала:**
```bash
export AURIS_SELF_AUTOTUNE_INTERVAL=30  # проверка каждые 30 секунд
```

### Логика работы
Автотюнер повышает `AURIS_SELF_CANARY` ступенями:
```
5% → 10% → 25% → 50% → 100%
```

Условия повышения (все должны быть выполнены):
- ✅ `stability_ema >= 0.80`
- ✅ `oscillation == 0`
- ✅ `coherence >= 0.80`
- ✅ `stress <= 0.30`

### Мониторинг автотюнера
Проверка логов:
```bash
# В логах API ищи:
grep "Auto-tune:" logs/atlas.log

# Пример:
# 2025-11-17 22:15:00 INFO Auto-tune: advancing 5% → 10% (SLO green)
```

## 🧹 Очистка

### Удалить артефакты SELF
```bash
make self-clean
```

Удаляет:
- `data/identity.jsonl` — heartbeat log
- `logs/resonance_trace.jsonl` — resonance metrics

## 🔧 Troubleshooting

### Метрики не появляются
**Проблема:** `curl http://localhost:8000/metrics/exp | grep self_` — пусто

**Решение:**
1. Проверь флаги:
   ```bash
   export AURIS_SELF=on
   export AURIS_METRICS_EXP=on
   ```
2. Перезапусти API
3. Проверь логи: `grep "SELF" logs/atlas.log`

### /self/health не работает
**Проблема:** `curl http://localhost:8000/self/health` → 404

**Решение:**
1. Убедись что `AURIS_SELF=on`
2. Проверь логи: должно быть `SELF API routes registered (/self/health, /self/canary)`
3. Проверь импорт: `python -c "from orbis_self.api_routes_exp import router; print('OK')"`

### Автотюнер не работает
**Проблема:** Канарейка не поднимается автоматически

**Решение:**
1. Проверь условия:
   ```bash
   curl http://localhost:8000/self/health | jq '.slo_status'
   # Все должны быть true
   ```
2. Проверь флаги:
   ```bash
   echo $AURIS_SELF_AUTOTUNE  # должно быть "on"
   ```
3. Проверь интервал:
   ```bash
   echo $AURIS_SELF_AUTOTUNE_INTERVAL  # по умолчанию 60 секунд
   ```
4. Принудительно повысь:
   ```bash
   curl -X POST http://localhost:8000/self/canary \
     -H "Content-Type: application/json" \
     -d '{"new_sampling": 0.10, "reason": "Manual test"}'
   ```

## 📚 Дополнительно

- **Полная документация:** `docs/SELF_CANARY_ENHANCEMENT.md`
- **Deployment log:** `docs/PHASE_C_DEPLOYMENT_LOG.md`
- **Unit tests:** `tests/test_self_*.py`
- **Resonance test:** `scripts/resonance_test.py`
