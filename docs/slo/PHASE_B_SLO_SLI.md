# Phase B: SLO/SLI Метрики

**Версия:** 1.0  
**Дата:** 2025-11-02  
**Статус:** 🚧 Draft

---

## 📊 Базовые метрики (Baseline)

Измерено на jbarton43/z-space после cleanup:

```yaml
baseline:
  tests_passed: 207
  pylint_score: 9.44
  coverage: ~85%
  
  # Производительность (estimated)
  encode_latency_p50: ~20ms
  encode_latency_p95: ~50ms
  
  # Стабильность
  test_failure_rate: 0.019  # 4 failing из 211
  oscillation_rate: unknown  # будет измерено в B1
```

---

## 🎯 B1: Hysteresis для Bit-Envelope

### Service Level Indicators (SLI)

#### 1. Switch Rate (переключения/сек/слой)
```yaml
sli:
  name: bit_envelope_switch_rate
  description: Частота переключений precision слоев
  measurement: count(switches) / time_window_seconds
  target_unit: switches/sec/layer
  
  calculation: |
    SELECT 
      layer,
      COUNT(*) / 60.0 as switches_per_sec
    FROM bit_envelope_switches
    WHERE timestamp >= NOW() - INTERVAL '1 minute'
    GROUP BY layer
```

**Целевые значения:**
- ✅ Normal: ≤1.0 switches/sec
- ⚠️ Warning: 1.0-2.0 switches/sec
- 🚨 Critical: >2.0 switches/sec

#### 2. Oscillation Rate (доля дрожащих окон)
```yaml
sli:
  name: oscillation_rate
  description: Процент окон с >2 переключениями за 5 секунд
  measurement: count(oscillating_windows) / count(total_windows)
  target_unit: ratio (0-1)
  
  calculation: |
    WITH window_switches AS (
      SELECT 
        window_id,
        COUNT(*) as switch_count
      FROM bit_envelope_switches
      WHERE timestamp >= NOW() - INTERVAL '5 seconds'
      GROUP BY window_id
    )
    SELECT 
      SUM(CASE WHEN switch_count > 2 THEN 1 ELSE 0 END)::float / 
      COUNT(*)
    FROM window_switches
```

**Целевые значения:**
- ✅ Normal: <0.05 (5% окон)
- ⚠️ Warning: 0.05-0.10
- 🚨 Critical: >0.10 (10% окон)

#### 3. Stability Latency (время до стабилизации)
```yaml
sli:
  name: stability_latency_p50
  description: Медианное время до прекращения переключений
  measurement: percentile(time_to_stable, 0.5)
  target_unit: seconds
  
  calculation: |
    SELECT 
      PERCENTILE_CONT(0.5) WITHIN GROUP (
        ORDER BY stable_at - first_switch_at
      ) as p50_latency
    FROM (
      SELECT 
        window_id,
        MIN(timestamp) as first_switch_at,
        MAX(timestamp) + INTERVAL '2 seconds' as stable_at
      FROM bit_envelope_switches
      GROUP BY window_id
      HAVING COUNT(*) > 0
    ) subq
```

**Целевые значения:**
- ✅ Normal: <2s
- ⚠️ Warning: 2-5s
- 🚨 Critical: >5s

### Service Level Objectives (SLO)

```yaml
slo_b1_hysteresis:
  - metric: oscillation_rate_p95
    target: < 0.1
    measurement_window: 5min
    alert_threshold: 0.15
    description: "95% окон НЕ дрожат (макс 2 переключения за 5сек)"
  
  - metric: stability_latency_p50
    target: < 2s
    measurement_window: 1min
    alert_threshold: 3s
    description: "50% окон стабилизируются за <2 секунды"
  
  - metric: switch_rate_max
    target: < 1.0 switches/sec
    measurement_window: 1min
    alert_threshold: 2.0
    description: "Максимум 1 переключение в секунду на слой"
```

---

## 🎯 B2: Window Stability Counter

### Service Level Indicators (SLI)

#### 1. Stability Score (EMA)
```yaml
sli:
  name: window_stability_score
  description: Экспоненциальная скользящая средняя стабильности
  measurement: EMA(is_stable, decay=0.95)
  target_unit: score (0-1)
  
  calculation: |
    # Python implementation
    score = 0.0
    for is_stable in window_events:
        score = decay * score + (1 - decay) * (1.0 if is_stable else 0.0)
    
    # Percentiles
    SELECT 
      PERCENTILE_CONT(0.5) as p50,
      PERCENTILE_CONT(0.95) as p95
    FROM window_stability_scores
    WHERE timestamp >= NOW() - INTERVAL '5 minutes'
```

**Целевые значения:**
- ✅ Normal: p50 >0.8, p95 >0.6
- ⚠️ Warning: p50 0.6-0.8, p95 0.4-0.6
- 🚨 Critical: p50 <0.6, p95 <0.4

#### 2. Degradation Events (переходы в FAB0/FAB1)
```yaml
sli:
  name: degradation_events_rate
  description: Частота принудительных деградаций режима
  measurement: count(degradation_events) / time_window_hours
  target_unit: events/hour
  
  calculation: |
    SELECT 
      COUNT(*) / 1.0 as events_per_hour
    FROM fab_mode_changes
    WHERE 
      new_mode IN ('FAB0', 'FAB1') AND
      reason = 'stability_threshold' AND
      timestamp >= NOW() - INTERVAL '1 hour'
```

**Целевые значения:**
- ✅ Normal: <5 events/hour
- ⚠️ Warning: 5-10 events/hour
- 🚨 Critical: >10 events/hour

#### 3. Recovery Time (время восстановления стабильности)
```yaml
sli:
  name: stability_recovery_time_p95
  description: 95-й перцентиль времени восстановления после деградации
  measurement: percentile(recovery_duration, 0.95)
  target_unit: seconds
  
  calculation: |
    SELECT 
      PERCENTILE_CONT(0.95) WITHIN GROUP (
        ORDER BY recovered_at - degraded_at
      ) as p95_recovery
    FROM stability_events
    WHERE 
      event_type = 'recovered' AND
      timestamp >= NOW() - INTERVAL '1 hour'
```

**Целевые значения:**
- ✅ Normal: <30s
- ⚠️ Warning: 30-60s
- 🚨 Critical: >60s

### Service Level Objectives (SLO)

```yaml
slo_b2_stability:
  - metric: stability_score_p50
    target: > 0.8
    measurement_window: 5min
    alert_threshold: 0.7
    description: "50% окон имеют стабильность >80%"
  
  - metric: stability_score_p95
    target: > 0.6
    measurement_window: 5min
    alert_threshold: 0.5
    description: "Даже worst-case окна имеют стабильность >60%"
  
  - metric: degradation_events_rate
    target: < 10/hour
    measurement_window: 1hour
    alert_threshold: 15/hour
    description: "Редкие деградации режима (<10/час)"
  
  - metric: recovery_time_p95
    target: < 30s
    measurement_window: 1hour
    alert_threshold: 60s
    description: "Быстрое восстановление (<30сек для 95% случаев)"
```

---

## 🎯 B3: Z-Space Shim Telemetry

### Service Level Indicators (SLI)

#### 1. Z-Space Latency
```yaml
sli:
  name: zspace_selector_latency
  description: Задержка Z-Space selector при выборе узлов
  measurement: histogram(select_duration_ms)
  target_unit: milliseconds
  
  calculation: |
    SELECT 
      PERCENTILE_CONT(0.5) as p50,
      PERCENTILE_CONT(0.95) as p95,
      PERCENTILE_CONT(0.99) as p99
    FROM zspace_selector_metrics
    WHERE timestamp >= NOW() - INTERVAL '1 minute'
```

**Целевые значения:**
- ✅ Normal: p50 <20ms, p95 <50ms, p99 <100ms
- ⚠️ Warning: p95 50-100ms
- 🚨 Critical: p95 >100ms

#### 2. Coverage (покрытие запроса)
```yaml
sli:
  name: zspace_coverage
  description: Процент запрошенных узлов, возвращенных selector'ом
  measurement: count(returned_nodes) / count(requested_nodes)
  target_unit: ratio (0-1)
  
  calculation: |
    SELECT 
      AVG(returned_count::float / requested_count) as avg_coverage
    FROM zspace_selector_metrics
    WHERE 
      timestamp >= NOW() - INTERVAL '1 minute' AND
      requested_count > 0
```

**Целевые значения:**
- ✅ Normal: >0.9 (90% покрытие)
- ⚠️ Warning: 0.7-0.9
- 🚨 Critical: <0.7 (70% покрытие)

#### 3. Novelty (разнообразие)
```yaml
sli:
  name: zspace_novelty
  description: Diversity score возвращенных узлов
  measurement: 1 - avg_cosine_similarity(nodes)
  target_unit: score (0-1)
  
  calculation: |
    # Novelty = 1 - average pairwise similarity
    SELECT 
      AVG(1.0 - cosine_similarity) as novelty
    FROM zspace_selector_metrics
    WHERE timestamp >= NOW() - INTERVAL '1 minute'
```

**Целевые значения:**
- ✅ Normal: >0.6 (высокое разнообразие)
- ⚠️ Warning: 0.4-0.6
- 🚨 Critical: <0.4 (низкое разнообразие)

#### 4. Budget Violations (превышения квот)
```yaml
sli:
  name: budget_violation_rate
  description: Процент запросов, превысивших time_ms/nodes бюджет
  measurement: count(violations) / count(total_requests)
  target_unit: ratio (0-1)
  
  calculation: |
    SELECT 
      SUM(CASE WHEN truncated = true THEN 1 ELSE 0 END)::float / 
      COUNT(*) as violation_rate
    FROM zspace_selector_metrics
    WHERE timestamp >= NOW() - INTERVAL '1 minute'
```

**Целевые значения:**
- ✅ Normal: <0.05 (5% запросов)
- ⚠️ Warning: 0.05-0.10
- 🚨 Critical: >0.10 (10% запросов)

### Service Level Objectives (SLO)

```yaml
slo_b3_zspace_telemetry:
  - metric: zspace_latency_p95
    target: < 50ms
    measurement_window: 1min
    alert_threshold: 100ms
    description: "Быстрый selector (95% запросов <50ms)"
  
  - metric: zspace_coverage_p50
    target: > 0.8
    measurement_window: 1min
    alert_threshold: 0.7
    description: "Высокое покрытие (50% запросов >80%)"
  
  - metric: zspace_novelty_p50
    target: > 0.5
    measurement_window: 1min
    alert_threshold: 0.4
    description: "Разнообразные результаты (novelty >50%)"
  
  - metric: budget_violation_rate
    target: < 0.05
    measurement_window: 1min
    alert_threshold: 0.10
    description: "Редкие превышения бюджета (<5%)"
```

---

## 🎯 B4: CI/Quality Gates

### Service Level Indicators (SLI)

#### 1. Build Success Rate
```yaml
sli:
  name: ci_build_success_rate
  description: Процент успешных CI builds
  measurement: count(success) / count(total_builds)
  target_unit: ratio (0-1)
  
  calculation: |
    SELECT 
      SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END)::float / 
      COUNT(*) as success_rate
    FROM ci_builds
    WHERE timestamp >= NOW() - INTERVAL '1 day'
```

**Целевые значения:**
- ✅ Normal: >0.95 (95% успешных)
- ⚠️ Warning: 0.90-0.95
- 🚨 Critical: <0.90

#### 2. Test Coverage
```yaml
sli:
  name: test_coverage
  description: Процент покрытия кода тестами
  measurement: covered_lines / total_lines
  target_unit: percentage (0-100)
  
  calculation: |
    # From pytest-cov report
    coverage = pytest_cov.get_total_coverage()
```

**Целевые значения:**
- ✅ Normal: >90%
- ⚠️ Warning: 85-90%
- 🚨 Critical: <85%

#### 3. Lint/Type Error Rate
```yaml
sli:
  name: lint_error_density
  description: Количество lint ошибок на 1000 строк кода
  measurement: count(lint_errors) / (total_lines / 1000)
  target_unit: errors per KLOC
  
  calculation: |
    total_errors = pylint_errors + mypy_errors + ruff_errors
    density = total_errors / (lines_of_code / 1000)
```

**Целевые значения:**
- ✅ Normal: <5 errors/KLOC
- ⚠️ Warning: 5-10 errors/KLOC
- 🚨 Critical: >10 errors/KLOC

### Service Level Objectives (SLO)

```yaml
slo_b4_quality:
  - metric: ci_build_success_rate
    target: > 0.95
    measurement_window: 1day
    alert_threshold: 0.90
    description: "Стабильные builds (>95% успешных за сутки)"
  
  - metric: test_coverage
    target: > 90%
    measurement_window: per_commit
    alert_threshold: 85%
    description: "Высокое покрытие тестами (>90%)"
  
  - metric: lint_error_density
    target: < 5/KLOC
    measurement_window: per_commit
    alert_threshold: 10/KLOC
    description: "Чистый код (<5 ошибок на 1000 строк)"
  
  - metric: pylint_score
    target: >= 9.0/10
    measurement_window: per_commit
    alert_threshold: 8.5/10
    description: "Высокий Pylint рейтинг (≥9.0)"
```

---

## 📈 Агрегированные метрики Phase B

### Overall Health Score

```yaml
health_score:
  calculation: |
    # Weighted average of component SLOs
    weights = {
      'hysteresis': 0.3,
      'stability': 0.3,
      'zspace_telemetry': 0.2,
      'quality': 0.2
    }
    
    score = sum(
      weights[component] * slo_compliance(component)
      for component in weights
    )
  
  target: > 0.9  # 90% compliance
  alert: < 0.8   # 80% compliance
```

### SLO Compliance Dashboard

```yaml
dashboard:
  title: "Phase B: SLO Compliance"
  
  panels:
    - title: "B1: Hysteresis"
      metrics:
        - oscillation_rate_p95: {target: 0.1, current: TBD}
        - stability_latency_p50: {target: 2s, current: TBD}
        - switch_rate_max: {target: 1.0, current: TBD}
    
    - title: "B2: Stability"
      metrics:
        - stability_score_p50: {target: 0.8, current: TBD}
        - stability_score_p95: {target: 0.6, current: TBD}
        - degradation_events: {target: 10/h, current: TBD}
    
    - title: "B3: Z-Space"
      metrics:
        - zspace_latency_p95: {target: 50ms, current: TBD}
        - zspace_coverage_p50: {target: 0.8, current: TBD}
        - budget_violations: {target: 5%, current: TBD}
    
    - title: "B4: Quality"
      metrics:
        - ci_build_success: {target: 95%, current: TBD}
        - test_coverage: {target: 90%, current: 85%}
        - pylint_score: {target: 9.0, current: 9.44}
```

---

## 🚨 Алерты и эскалация

### Severity Levels

```yaml
severity:
  P0_CRITICAL:
    response_time: 15min
    escalate_after: 30min
    conditions:
      - oscillation_rate_p95 > 0.2
      - stability_score_p50 < 0.5
      - zspace_latency_p95 > 200ms
      - ci_build_success < 0.8
  
  P1_HIGH:
    response_time: 1hour
    escalate_after: 4hours
    conditions:
      - oscillation_rate_p95 > 0.15
      - stability_score_p50 < 0.7
      - zspace_latency_p95 > 100ms
      - degradation_events > 15/hour
  
  P2_MEDIUM:
    response_time: 4hours
    escalate_after: 1day
    conditions:
      - oscillation_rate_p95 > 0.1
      - stability_score_p95 < 0.6
      - budget_violations > 0.1
  
  P3_LOW:
    response_time: 1day
    escalate_after: 1week
    conditions:
      - test_coverage < 90%
      - lint_error_density > 5/KLOC
```

### Alert Routing

```yaml
alert_routing:
  - name: "Hysteresis Oscillation"
    severity: P1_HIGH
    condition: oscillation_rate_p95 > 0.15
    notify:
      - slack: "#atlas-alerts"
      - email: "team-atlas@company.com"
    runbook: "docs/runbooks/hysteresis_oscillation.md"
  
  - name: "Stability Degradation"
    severity: P0_CRITICAL
    condition: stability_score_p50 < 0.5
    notify:
      - pagerduty: "atlas-oncall"
      - slack: "#atlas-critical"
    runbook: "docs/runbooks/stability_degradation.md"
  
  - name: "Z-Space Timeout"
    severity: P1_HIGH
    condition: zspace_latency_p95 > 100ms
    notify:
      - slack: "#atlas-performance"
    runbook: "docs/runbooks/zspace_timeout.md"
```

---

## 📊 Мониторинг и визуализация

### Prometheus Metrics

```yaml
prometheus_metrics:
  # Hysteresis
  - atlas_bit_envelope_switches_total
  - atlas_oscillation_windows_ratio
  - atlas_stability_latency_seconds
  
  # Stability
  - atlas_window_stability_score
  - atlas_degradation_events_total
  - atlas_recovery_time_seconds
  
  # Z-Space
  - atlas_zspace_selector_duration_ms
  - atlas_zspace_coverage_ratio
  - atlas_zspace_novelty_score
  - atlas_zspace_budget_violations_total
  
  # Quality
  - atlas_ci_build_status
  - atlas_test_coverage_percent
  - atlas_lint_errors_per_kloc
```

### Grafana Dashboards

```yaml
dashboards:
  - name: "Phase B: Overview"
    url: "/grafana/d/phase-b-overview"
    panels:
      - Overall Health Score
      - SLO Compliance by Component
      - Active Alerts
      - Recent Deployments
  
  - name: "B1: Hysteresis Deep Dive"
    url: "/grafana/d/hysteresis"
    panels:
      - Switch Rate Timeline
      - Oscillation Heatmap
      - Stability Latency Distribution
      - Layer-by-Layer Breakdown
  
  - name: "B2: Stability Tracking"
    url: "/grafana/d/stability"
    panels:
      - Stability Score Timeline
      - Degradation Events Log
      - Recovery Time Distribution
      - Window-Level Details
  
  - name: "B3: Z-Space Performance"
    url: "/grafana/d/zspace-perf"
    panels:
      - Latency Percentiles
      - Coverage & Novelty
      - Budget Violations
      - Top Slow Queries
```

---

**Следующие шаги:**
1. Имплементировать Prometheus exporters для новых метрик
2. Настроить Grafana dashboards
3. Создать runbooks для каждого алерта
4. Провести load testing для baseline измерений
