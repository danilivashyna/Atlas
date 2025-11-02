# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
PR#6.0: SELF-Token Loop tests.

Tests self-referencing loop: self_presence → policy/META.
"""

from orbis_fab.core import FABCore


def test_selfloop_pushes_aggressive_when_presence_high():
    """High self_presence_ema pushes policy to aggressive."""
    fab = FABCore(
        selector="fab",
        selfloop_enabled=True,
        self_presence_alpha=1.0,  # Immediate update
        self_presence_high=0.8,
        policy_enabled=True,
        policy_dwell_ticks=0,  # No dwell for immediate switch
    )

    # Simulate high self_presence
    fab.step_stub(stress=0.3, self_presence=0.9, error_rate=0.0)

    # Check EMA updated
    assert (
        fab.self_presence_ema >= 0.8
    ), f"Expected self_presence_ema >= 0.8, got {fab.self_presence_ema}"

    # Trigger policy update (should go aggressive due to high self_presence)
    fab.z_meta_volatility = 0.3  # Moderate volatility
    fab.z_cb_remaining = 0
    fab._policy_update()

    # Policy should be aggressive (self-intensification)
    assert fab.policy_mode == "aggressive", f"Expected aggressive mode, got {fab.policy_mode}"


def test_selfloop_pushes_conservative_when_presence_low():
    """Low self_presence_ema pushes policy to conservative."""
    fab = FABCore(
        selector="fab",
        selfloop_enabled=True,
        self_presence_alpha=1.0,
        self_presence_low=0.3,
        policy_enabled=True,
        policy_dwell_ticks=0,
    )

    # Simulate low self_presence
    fab.step_stub(stress=0.3, self_presence=0.1, error_rate=0.0)

    assert (
        fab.self_presence_ema <= 0.3
    ), f"Expected self_presence_ema <= 0.3, got {fab.self_presence_ema}"

    # Trigger policy update (should go conservative due to low self_presence)
    fab.z_meta_volatility = 0.3  # Moderate volatility
    fab.z_cb_remaining = 0
    fab._policy_update()

    assert fab.policy_mode == "conservative", f"Expected conservative mode, got {fab.policy_mode}"


def test_selfloop_exposed_metrics():
    """SELF-Loop metrics exported in diagnostics.derived."""
    fab = FABCore(selector="fab", selfloop_enabled=True, policy_enabled=False)

    budgets = {"tokens": 8000, "nodes": 4, "edges": 0, "time_ms": 50}
    fab.init_tick(mode="FAB0", budgets=budgets)  # type: ignore[arg-type]

    # Update self_presence
    fab.step_stub(stress=0.5, self_presence=0.7, error_rate=0.0)

    result = fab.mix()
    derived = result["diagnostics"]["derived"]

    assert "selfloop_enabled" in derived
    assert "self_presence_ema" in derived

    assert derived["selfloop_enabled"] is True
    assert isinstance(derived["self_presence_ema"], (int, float))
    assert 0.0 <= derived["self_presence_ema"] <= 1.0
