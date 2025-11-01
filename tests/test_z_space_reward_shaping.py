# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
PR#5.7: Reward Shaping tests.

Tests soft gradient overlay on AIMD/META via reward signal.
"""

from orbis_fab.core import FABCore


def test_reward_increases_ai_step_on_good_states():
    """Reward pressure increases AI step when reward_ema > 0.5 (good states)."""
    fab = FABCore(
        selector="fab",
        reward_enabled=True,
        reward_alpha=1.0,  # Immediate update
        reward_weights=(+1.0, -0.01, -1.0, -1.0),  # High diversity weight, low latency weight
        reward_pressure_ai=0.05,
        policy_enabled=False,
        z_adapt_enabled=False
    )
    
    # Simulate high diversity gain → positive reward
    fab.z_last_diversity_gain = 2.0  # High diversity
    fab.z_last_latency_ms = 10.0     # Low latency (weighted lightly)
    fab.z_cb_remaining = 0           # No CB
    fab.st.metrics = {"error_rate": 0.0}
    
    fab._reward_update()
    
    # reward = (+1.0 * 2.0) + (-0.01 * 10.0) + 0 + 0 = 2.0 - 0.1 = 1.9 > 0.5
    assert fab.reward_ema > 0.5, f"Expected reward_ema > 0.5, got {fab.reward_ema}"
    
    # AI step should be boosted by pressure
    base_ai = fab.z_ai_step_ms  # 0.25 default
    effective_ai = fab._policy_ai_step_ms()
    assert effective_ai > base_ai, f"Expected effective_ai ({effective_ai}) > base ({base_ai})"
    assert abs(effective_ai - (base_ai + fab.reward_pressure_ai)) < 0.01


def test_reward_decreases_target_on_good_states():
    """Reward pressure tightens target latency when reward_ema > 0.5 (system doing well)."""
    fab = FABCore(
        selector="fab",
        reward_enabled=True,
        reward_alpha=1.0,
        reward_weights=(+1.0, -0.01, -1.0, -1.0),
        reward_pressure_target=1.0,
        policy_enabled=False,
        z_meta_enabled=True,
        z_target_latency_ms=10.0,
        z_meta_target_bounds=(5.0, 15.0),
        z_meta_min_window=1  # Trigger meta immediately
    )
    
    # Simulate good state + build history for meta
    fab.z_last_diversity_gain = 2.0
    fab.z_last_latency_ms = 5.0
    fab.z_cb_remaining = 0
    fab.st.metrics["error_rate"] = 0.0
    
    # Build limit history (stable, low volatility)
    for _ in range(10):
        fab.z_limit_history.append(10.0)
    
    fab._reward_update()
    initial_target = fab.z_target_latency_ms
    
    # Trigger meta-learn (should apply reward pressure)
    fab._z_meta_learn(observed_latency_ms=5.0)
    
    # Target should decrease (tightened) due to positive reward
    assert fab.z_target_latency_ms < initial_target, \
        f"Expected target to decrease, got {fab.z_target_latency_ms} vs {initial_target}"


def test_reward_metrics_exposed_in_mix():
    """Reward metrics exported in diagnostics.derived."""
    fab = FABCore(
        selector="fab",
        reward_enabled=True,
        reward_window=10,
        policy_enabled=False
    )
    
    budgets = {"tokens": 8000, "nodes": 4, "edges": 0, "time_ms": 50}
    fab.init_tick(mode="FAB0", budgets=budgets)  # type: ignore[arg-type]
    result = fab.mix()
    
    derived = result["diagnostics"]["derived"]
    assert "reward_enabled" in derived
    assert "reward_last" in derived
    assert "reward_ema" in derived
    assert "reward_window_avg" in derived
    
    assert derived["reward_enabled"] is True
    assert isinstance(derived["reward_last"], (int, float))
    assert isinstance(derived["reward_ema"], (int, float))
    assert isinstance(derived["reward_window_avg"], (int, float))
