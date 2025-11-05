# Phase B.1: Hysteresis Anti-Chatter — COMPLETE ✅

## Summary

**Status**: ✅ **Complete** (7/7 tasks)  
**Tests**: 20/20 passing (9 unit + 11 integration)  
**E2E Probe**: 4/4 checks passing  
**Quality**: Pylint 9.67/10 (hysteresis_exp.py), 9.39/10 (hysteresis_hook_exp.py), Black formatted

---

## Feature Overview

**Goal**: Prevent rapid FAB mode oscillations (anti-drebezg) through:
- **Dwell time**: Hold desired mode for 50 ticks before accepting switch
- **Global rate limit**: Enforce ≥1000 ticks (≈1 sec) between any switches  
- **Oscillation detection**: Track rapid back-and-forth changes within 300 tick window

**Feature Flag**: `AURIS_HYSTERESIS=on` (guarded, isolated, zero impact when off)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Phase B Integration                        │
└──────────────────────────────────────────────────────────────┘

  B2 StabilityTracker                B1 Hysteresis                 
  (recommend_mode)      ──────►   (anti-chatter)       ──────►  FABCore
                                                                 (effective_mode)
       ↓                               ↓                            ↓
   Prometheus                      Prometheus                   step_stub()
   (stability_*)                   (hyst_*)                     

                           Unified /metrics/exp endpoint
```

**Flow**:
1. B2 → `_last_stability["recommended_mode"]` (e.g., "FAB1")
2. B1 → `maybe_hyst(fab_core)` extracts desired, applies dwell + rate limit
3. B1 → Returns `effective_mode` (smoother than desired)
4. Prometheus → Updates 6 hyst_* gauges for Grafana

---

## Files Created/Modified

### Core Implementation (414 lines)
- **src/orbis_fab/hysteresis_exp.py** (243 lines)
  - `HysteresisConfig`: dwell_ticks=50, rate_limit_ticks=1000, osc_window=300
  - `HysteresisState`: last_mode, last_switch_tick, dwell_counter, switch_history
  - `BitEnvelopeHysteresisExp.update()`: core dwell + rate limiting logic
  - `get_metrics()`: returns switch_rate_per_sec, oscillation_rate, dwell_counter, etc.

- **src/orbis_fab/hysteresis_hook_exp.py** (171 lines)
  - `attach_to_fab(fab_core)`: creates BitEnvelopeHysteresisExp with production config
  - `maybe_hyst(fab_core)`: extracts desired from B2, applies hysteresis, updates Prometheus
  - `extract_desired_mode()`: B2 → st.mode → default fallback chain

### Prometheus Integration (extended)
- **src/atlas/metrics/exp_prom_exporter.py** (+70 lines)
  - Added 6 hysteresis gauges: `atlas_hyst_*`
  - `update_hysteresis_metrics(metrics_dict)`: converts modes to numeric (0/1/2)

### FABCore Integration (modified)
- **src/orbis_fab/core.py** (+13 lines)
  - `__init__`: guarded `_hyst` initialization when `AURIS_HYSTERESIS=on`
  - `step_stub()`: guarded `maybe_hyst()` call after B2 stability update

### Tests (20 tests, 100% passing)
- **tests/test_hysteresis_exp.py** (9 unit tests)
  - Dwell enforcement, rate limiting, oscillation detection, metrics shape
  - Bug fix: deque maxlen now respects config.max_history

- **tests/test_hysteresis_hook_exp.py** (11 integration tests)
  - attach/detach, extract_desired, FABCore runtime, Prometheus update
  - Effective smoother than desired verification

### E2E Validation
- **scripts/hysteresis_probe_exp.py** (158 lines)
  - Simulates 150 ticks with oscillating desired modes (51 switches)
  - Result: **1 effective switch** (98% reduction!)
  - Verifies all 6 Prometheus metrics present
  - SLO check: switch_rate ≤ 1/sec ✅

---

## Metrics Exposed

**Prometheus endpoint**: `GET /metrics/exp`

### Hysteresis Metrics (6 gauges)
1. **atlas_hyst_switch_rate_per_sec{window_id}**  
   Mode switches per second (SLO: ≤1.0)

2. **atlas_hyst_oscillation_rate_per_sec{window_id}**  
   Oscillations per second (back-and-forth rapid changes)

3. **atlas_hyst_dwell_counter{window_id}**  
   Current dwell accumulator (ticks holding desired mode)

4. **atlas_hyst_last_switch_age{window_id}**  
   Ticks since last mode switch

5. **atlas_hyst_effective_mode{window_id}**  
   Effective FAB mode after hysteresis (0=FAB0, 1=FAB1, 2=FAB2)

6. **atlas_hyst_desired_mode{window_id}**  
   Desired FAB mode from B2 (0=FAB0, 1=FAB1, 2=FAB2)

---

## SLO Results

**Target**: switch_rate_p95 ≤ 1/sec, oscillation reduction ≥50%

**Achieved** (E2E probe):
- ✅ Switch rate: **0.0/sec** (≤ 1.0 SLO)
- ✅ Oscillation reduction: **98%** (vs 50% target)
- ✅ Effective switches: **1** (vs 51 desired)
- ✅ All 6 Prometheus metrics present

---

## Usage

### Enable Hysteresis
```bash
export AURIS_HYSTERESIS=on
export AURIS_METRICS_EXP=on
```

### In Code (automatic via FABCore)
```python
# In FABCore.__init__:
if os.getenv("AURIS_HYSTERESIS", "off") == "on":
    self._hyst = attach_to_fab(self)

# In FABCore.step_stub():
if self._hyst is not None:
    hyst_result = maybe_hyst(self)
    # hyst_result = {
    #   "desired_mode": "FAB1",        # From B2
    #   "effective_mode": "FAB2",      # After hysteresis
    #   "switch_rate_per_sec": 0.001,
    #   "oscillation_rate_per_sec": 0.0,
    #   "dwell_counter": 35,
    #   "last_switch_age": 1200,
    #   "osc_count": 0
    # }
```

### Verify Metrics
```bash
curl http://localhost:8000/metrics/exp | grep hyst
```

**Sample Output**:
```
atlas_hyst_switch_rate_per_sec{window_id="global"} 0.0
atlas_hyst_oscillation_rate_per_sec{window_id="global"} 0.0
atlas_hyst_dwell_counter{window_id="global"} 35
atlas_hyst_last_switch_age{window_id="global"} 1200
atlas_hyst_effective_mode{window_id="global"} 2
atlas_hyst_desired_mode{window_id="global"} 1
```

---

## Integration with Phase B

**B3 Telemetry** (Complete):
- Prometheus registry + FastAPI `/metrics/exp` endpoint
- 6 stability metrics (score, EMA, degradation_events, recommended_mode, etc.)

**B2 Runtime Integration** (Complete):
- StabilityTracker hooked into FABCore.step_stub()
- `_last_stability["recommended_mode"]` provides input to B1

**B1 Hysteresis** (Complete):
- Consumes B2 recommended_mode
- Applies dwell + rate limiting
- Exposes 6 additional Prometheus metrics
- **Unified observability**: B2 stability + B1 hysteresis on same `/metrics/exp` endpoint

**Next: B4 CI Quality Gates**  
Automated checks for:
- Tests passing (54/54 ✅)
- Pylint ≥9.3 (hysteresis_exp: 9.67, hook: 9.39 ✅)
- Black formatting ✅
- SLO enforcement (switch_rate ≤ 1/sec ✅)

---

## Key Achievements

1. ✅ **Zero FABCore behavior change** when `AURIS_HYSTERESIS=off`
2. ✅ **98% oscillation reduction** (vs 50% SLO target)
3. ✅ **All 20 tests passing** (9 unit + 11 integration)
4. ✅ **E2E probe passing** (4/4 checks)
5. ✅ **High code quality** (Pylint 9.67/9.39, Black formatted)
6. ✅ **Prometheus integration** (6 metrics, compatible with Grafana)
7. ✅ **Graceful degradation** (lazy imports, exception handling)
8. ✅ **Production-ready config** (dwell=50, rate_limit=1000, osc_window=300)

---

## Grafana Dashboard (Planned)

**Panel 1: Desired vs Effective Mode**
- Step graph showing `hyst_desired_mode` vs `hyst_effective_mode`
- Visual: effective smoother than desired

**Panel 2: Switch Rates**
- Dual line: `hyst_switch_rate_per_sec` + threshold (1.0 SLO)
- Alert: switch_rate > 1.0

**Panel 3: Oscillation Tracking**
- Line: `hyst_oscillation_rate_per_sec`
- Counter: `hyst_osc_count` (total oscillations)

**Panel 4: Dwell & Age**
- Gauge: `hyst_dwell_counter` (current accumulator)
- Line: `hyst_last_switch_age` (ticks since last switch)

---

## Bug Fixes

**Issue**: `test_switch_history_maxlen` failed — deque exceeded max_history  
**Cause**: `HysteresisState` used hardcoded `maxlen=5000` instead of `config.max_history`  
**Fix**: Modified `__init__` to create deque with `maxlen=self.config.max_history`  
**Result**: ✅ All 9 unit tests passing

---

## Phase B.1 Status: ✅ COMPLETE

**Date**: 2025-11-03  
**Delivered**:
- 2 core modules (414 lines)
- 1 Prometheus extension (+70 lines)
- 1 FABCore integration (+13 lines)
- 20 tests (100% passing)
- 1 E2E probe (4/4 checks)
- High code quality (Pylint 9.67/9.39, Black formatted)
- SLO compliance (switch_rate ≤ 1/sec, 98% oscillation reduction)

**Ready for**: B4 CI Quality Gates automation
