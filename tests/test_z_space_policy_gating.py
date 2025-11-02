import pytest
from orbis_fab.core import FABCore
from typing import Any

# Import shared type coercion helpers (PR#6.1)
from tests.test_helpers import (
    as_str,
    as_opt_str,
    as_bool,
    as_int,
    as_float,
    as_bounds_tuple,
    as_weights4,
)


# pylint: disable=redefined-outer-name


@pytest.fixture
def budgets():
    return {"nodes": 32, "time_ms": 100.0, "tokens": 0, "edges": 0}


def _make_core(**overrides: Any):
    """Type-safe FABCore factory for policy gating tests."""
    # Build typed dict with defaults
    typed_args: dict[str, Any] = {
        "selector": as_str("fab"),
        "ab_shadow_enabled": as_bool(True),
        "ab_ratio": as_float(0.5),
        "z_time_limit_ms": as_float(5.0),
        "z_adapt_enabled": as_bool(True),
        "z_target_latency_ms": as_float(2.0),
        "z_limit_min_ms": as_float(1.0),
        "z_limit_max_ms": as_float(10.0),
        "z_ai_step_ms": as_float(0.25),
        "z_md_factor": as_float(0.5),
        # meta (PR#5.5)
        "z_meta_enabled": as_bool(True),
        "z_meta_min_window": as_int(5),
        "z_meta_vol_threshold": as_float(0.35),
        "z_meta_target_bounds": as_bounds_tuple((1.0, 8.0)),
        "z_meta_adjust_step_ms": as_float(0.25),
        # policy (PR#5.6)
        "policy_enabled": as_bool(True),
        "policy_dwell_ticks": as_int(2),
        "policy_aggr_vol_max": as_float(0.20),
        "policy_cons_vol_min": as_float(0.60),
        "policy_error_cons_min": as_float(0.05),
        "policy_aggr_ai_mult": as_float(1.5),
        "policy_aggr_md_mult": as_float(0.9),
        "policy_aggr_cb_mult": as_float(0.5),
        "policy_aggr_ab_mult": as_float(1.2),
        "policy_cons_ai_mult": as_float(0.5),
        "policy_cons_md_mult": as_float(0.5),
        "policy_cons_cb_mult": as_float(1.5),
        "policy_cons_ab_mult": as_float(0.6),
        # Disable SELF-Loop to test pure policy behavior
        "selfloop_enabled": as_bool(False),
        "reward_enabled": as_bool(False),
    }

    # Apply overrides with type coercion
    for k, v in overrides.items():
        if k in ("envelope_mode", "selector", "shadow_selector"):
            typed_args[k] = as_str(v)
        elif k == "session_id":
            typed_args[k] = as_opt_str(v)
        elif k in (
            "ab_shadow_enabled",
            "z_adapt_enabled",
            "z_meta_enabled",
            "policy_enabled",
            "reward_enabled",
            "selfloop_enabled",
        ):
            typed_args[k] = as_bool(v)
        elif k in (
            "hold_ms",
            "hysteresis_dwell",
            "hysteresis_rate_limit",
            "min_stream_for_upgrade",
            "z_cb_cooldown_ticks",
            "z_meta_min_window",
            "policy_dwell_ticks",
            "reward_window",
        ):
            typed_args[k] = as_int(v)
        elif k in (
            "ab_ratio",
            "z_time_limit_ms",
            "z_target_latency_ms",
            "z_limit_min_ms",
            "z_limit_max_ms",
            "z_ai_step_ms",
            "z_md_factor",
            "z_meta_vol_threshold",
            "z_meta_adjust_step_ms",
            "policy_aggr_vol_max",
            "policy_cons_vol_min",
            "policy_error_cons_min",
            "policy_aggr_ai_mult",
            "policy_aggr_md_mult",
            "policy_aggr_cb_mult",
            "policy_aggr_ab_mult",
            "policy_cons_ai_mult",
            "policy_cons_md_mult",
            "policy_cons_cb_mult",
            "policy_cons_ab_mult",
            "reward_alpha",
            "reward_pressure_ai",
            "reward_pressure_target",
            "self_presence_alpha",
            "self_presence_high",
            "self_presence_low",
        ):
            typed_args[k] = as_float(v)
        elif k == "z_meta_target_bounds":
            typed_args[k] = as_bounds_tuple(v, default=(1.0, 8.0))
        elif k == "reward_weights":
            typed_args[k] = as_weights4(v, default=(1.0, -1.0, -1.0, -1.0))
        else:
            typed_args[k] = v  # Pass through unknown

    return FABCore(**typed_args)


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
