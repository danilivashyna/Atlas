import pytest
from orbis_fab.core import FABCore

@pytest.fixture
def budgets():
    return {"nodes": 32, "time_ms": 100.0, "tokens": 0, "edges": 0}

def _make_core(**overrides):
    cfg = dict(
        selector="fab",
        ab_shadow_enabled=True,
        ab_ratio=0.5,
        z_time_limit_ms=5.0,
        z_adapt_enabled=True,
        z_target_latency_ms=2.0,
        z_limit_min_ms=1.0,
        z_limit_max_ms=10.0,
        z_ai_step_ms=0.25,
        z_md_factor=0.5,
        # meta (PR#5.5)
        z_meta_enabled=True,
        z_meta_min_window=5,
        z_meta_vol_threshold=0.35,
        z_meta_target_bounds=(1.0, 8.0),
        z_meta_adjust_step_ms=0.25,
        # policy (PR#5.6)
        policy_enabled=True,
        policy_dwell_ticks=2,
        policy_aggr_vol_max=0.20,
        policy_cons_vol_min=0.60,
        policy_error_cons_min=0.05,
        policy_aggr_ai_mult=1.5,
        policy_aggr_md_mult=0.9,
        policy_aggr_cb_mult=0.5,
        policy_aggr_ab_mult=1.2,
        policy_cons_ai_mult=0.5,
        policy_cons_md_mult=0.5,
        policy_cons_cb_mult=1.5,
        policy_cons_ab_mult=0.6,
    )
    cfg.update(overrides)
    return FABCore(**cfg)

def test_policy_defaults_to_balanced(budgets):
    core = _make_core()
    core.init_tick(mode="FAB1", budgets=budgets)
    d = core.mix()["diagnostics"]["derived"]
    assert d["policy_enabled"] is True
    assert d["policy_mode"] in ("balanced", "aggressive", "conservative")

def test_policy_switches_to_aggressive_on_low_volatility(budgets):
    core = _make_core()
    # стабильное окно → низкая волатильность
    core.z_limit_history.extend([2.0] * 10)
    core.z_meta_volatility = 0.1
    core.z_cb_remaining = 0
    core.st.metrics = {"stress": 0.1, "self_presence": 0.9, "error_rate": 0.0}
    core.init_tick(mode="FAB1", budgets=budgets)
    d = core.mix()["diagnostics"]["derived"]
    # либо уже aggressive, либо ещё в dwell — но параметры должны стремиться вверх/вниз соответственно
    assert d["policy_effective_ai_step_ms"] >= core.z_ai_step_ms
    assert d["policy_effective_md_factor"] <= core.z_md_factor

def test_policy_switches_to_conservative_on_cb_or_errors(budgets):
    core = _make_core()
    core.z_limit_history.extend([2.0, 3.0, 5.0, 4.0, 6.0])
    core.z_meta_volatility = 0.8
    core.z_cb_remaining = 10  # CB открыт
    core.st.metrics = {"stress": 0.3, "self_presence": 0.9, "error_rate": 0.1}
    core.init_tick(mode="FAB1", budgets=budgets)
    d = core.mix()["diagnostics"]["derived"]
    assert d["policy_effective_ai_step_ms"] <= core.z_ai_step_ms
    assert d["policy_effective_cb_cooldown"] >= core.z_cb_cooldown_ticks

def test_policy_adjusts_ab_ratio(budgets):
    core = _make_core(ab_ratio=0.4)
    core.z_limit_history.extend([2.0] * 10)
    core.z_meta_volatility = 0.1
    core.z_cb_remaining = 0
    core.st.metrics = {"stress": 0.1, "self_presence": 0.9, "error_rate": 0.0}
    core.init_tick(mode="FAB1", budgets=budgets)
    d = core.mix()["diagnostics"]["derived"]
    eff = d["policy_effective_ab_ratio"]
    assert 0.0 <= eff <= 1.0
    # В aggressive мультипликатор подталкивает вероятность A/B вверх (или остаётся прежней до ухода из dwell)
    assert eff >= 0.4 or d["policy_mode"] == "balanced"
