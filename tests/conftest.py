# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Pytest configuration and fixtures for Atlas tests.
"""

import random
import pytest

from atlas.api import app as app_module
from atlas.hierarchical import HierarchicalDecoder, HierarchicalEncoder

# Import type coercion helpers (PR#6.1: shared test utilities)
from tests.test_helpers import (
    as_str, as_opt_str, as_bool, as_int, as_float, 
    as_bounds_tuple, as_weights4
)


@pytest.fixture(scope="session", autouse=True)
def initialize_hierarchical():
    """Initialize hierarchical encoder/decoder globally for all tests."""
    # Manually set global variables since TestClient doesn't trigger lifespan
    app_module.hierarchical_encoder = HierarchicalEncoder()
    app_module.hierarchical_decoder = HierarchicalDecoder()
    yield
    # Cleanup
    app_module.hierarchical_encoder = None
    app_module.hierarchical_decoder = None


@pytest.fixture(autouse=True)
def _stable_env(monkeypatch):
    """PR#5.6: Stabilize test environment for deterministic runs."""
    # Disable .pyc to prevent bytecode cache from affecting test order
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    # Fix random seed for reproducibility
    random.seed(1337)


@pytest.fixture
def fab_clean():
    """PR#5.6: Clean FABCore for AIMD/META tests (policy/CB/A/B disabled)."""
    from orbis_fab.core import FABCore
    from typing import Any
    
    def _mk(**kw: Any):
        # Build typed dict for FABCore
        typed_args: dict[str, Any] = {}
        
        # Explicit type coercion for each parameter
        typed_args["policy_enabled"] = as_bool(kw.get("policy_enabled", False))
        typed_args["z_cb_cooldown_ticks"] = as_int(kw.get("z_cb_cooldown_ticks", 0))
        typed_args["ab_shadow_enabled"] = as_bool(kw.get("ab_shadow_enabled", False))
        
        # Coerce all other known parameters
        if "envelope_mode" in kw:
            typed_args["envelope_mode"] = as_str(kw["envelope_mode"])
        if "session_id" in kw:
            typed_args["session_id"] = as_opt_str(kw["session_id"])
        if "selector" in kw:
            typed_args["selector"] = as_str(kw["selector"])
        if "shadow_selector" in kw:
            typed_args["shadow_selector"] = as_str(kw["shadow_selector"])
        
        # Boolean params
        for param in ("z_adapt_enabled", "z_meta_enabled", "reward_enabled", "selfloop_enabled"):
            if param in kw:
                typed_args[param] = as_bool(kw[param])
        
        # Integer params
        for param in ("hold_ms", "hysteresis_dwell", "hysteresis_rate_limit", "min_stream_for_upgrade",
                      "z_meta_min_window", "policy_dwell_ticks", "reward_window"):
            if param in kw:
                typed_args[param] = as_int(kw[param])
        
        # Float params
        for param in ("ab_ratio", "z_time_limit_ms", "z_target_latency_ms", "z_limit_min_ms", "z_limit_max_ms",
                      "z_ai_step_ms", "z_md_factor", "z_meta_vol_threshold", "z_meta_adjust_step_ms",
                      "policy_aggr_vol_max", "policy_cons_vol_min", "policy_error_cons_min",
                      "policy_aggr_ai_mult", "policy_aggr_md_mult", "policy_aggr_cb_mult", "policy_aggr_ab_mult",
                      "policy_cons_ai_mult", "policy_cons_md_mult", "policy_cons_cb_mult", "policy_cons_ab_mult",
                      "reward_alpha", "reward_pressure_ai", "reward_pressure_target",
                      "self_presence_alpha", "self_presence_high", "self_presence_low"):
            if param in kw:
                typed_args[param] = as_float(kw[param])
        
        # Tuple params
        if "z_meta_target_bounds" in kw:
            typed_args["z_meta_target_bounds"] = as_bounds_tuple(kw["z_meta_target_bounds"], default=(1.0, 8.0))
        if "reward_weights" in kw:
            typed_args["reward_weights"] = as_weights4(kw["reward_weights"], default=(1.0, -1.0, -1.0, -1.0))
        
        return FABCore(**typed_args)
    
    return _mk


@pytest.fixture
def fab_zspace():
    """PR#5.6: Z-Space-only FABCore (no A/B, CB, policy interference)."""
    from orbis_fab.core import FABCore
    from typing import Any
    
    def _mk(**kw: Any):
        # Build typed dict for FABCore
        typed_args: dict[str, Any] = {}
        
        # Explicit defaults for z-space fixture
        typed_args["selector"] = as_str(kw.get("selector", "z-space"))
        typed_args["policy_enabled"] = as_bool(kw.get("policy_enabled", False))
        typed_args["ab_shadow_enabled"] = as_bool(kw.get("ab_shadow_enabled", False))
        typed_args["ab_ratio"] = as_float(kw.get("ab_ratio", 1.0))
        typed_args["z_cb_cooldown_ticks"] = as_int(kw.get("z_cb_cooldown_ticks", 0))
        
        # Coerce all other known parameters
        if "envelope_mode" in kw:
            typed_args["envelope_mode"] = as_str(kw["envelope_mode"])
        if "session_id" in kw:
            typed_args["session_id"] = as_opt_str(kw["session_id"])
        if "shadow_selector" in kw:
            typed_args["shadow_selector"] = as_str(kw["shadow_selector"])
        
        # Boolean params
        for param in ("z_adapt_enabled", "z_meta_enabled", "reward_enabled", "selfloop_enabled"):
            if param in kw:
                typed_args[param] = as_bool(kw[param])
        
        # Integer params
        for param in ("hold_ms", "hysteresis_dwell", "hysteresis_rate_limit", "min_stream_for_upgrade",
                      "z_meta_min_window", "policy_dwell_ticks", "reward_window"):
            if param in kw:
                typed_args[param] = as_int(kw[param])
        
        # Float params
        for param in ("z_time_limit_ms", "z_target_latency_ms", "z_limit_min_ms", "z_limit_max_ms",
                      "z_ai_step_ms", "z_md_factor", "z_meta_vol_threshold", "z_meta_adjust_step_ms",
                      "policy_aggr_vol_max", "policy_cons_vol_min", "policy_error_cons_min",
                      "policy_aggr_ai_mult", "policy_aggr_md_mult", "policy_aggr_cb_mult", "policy_aggr_ab_mult",
                      "policy_cons_ai_mult", "policy_cons_md_mult", "policy_cons_cb_mult", "policy_cons_ab_mult",
                      "reward_alpha", "reward_pressure_ai", "reward_pressure_target",
                      "self_presence_alpha", "self_presence_high", "self_presence_low"):
            if param in kw:
                typed_args[param] = as_float(kw[param])
        
        # Tuple params
        if "z_meta_target_bounds" in kw:
            typed_args["z_meta_target_bounds"] = as_bounds_tuple(kw["z_meta_target_bounds"], default=(1.0, 8.0))
        if "reward_weights" in kw:
            typed_args["reward_weights"] = as_weights4(kw["reward_weights"], default=(1.0, -1.0, -1.0, -1.0))
        
        return FABCore(**typed_args)
    
    return _mk

