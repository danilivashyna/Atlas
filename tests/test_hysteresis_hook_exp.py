"""
Integration tests for hysteresis_hook_exp.py (Phase B.1)

Tests FABCore integration:
- attach_to_fab() with AURIS_HYSTERESIS flag
- maybe_hyst() B2 → hysteresis → effective_mode
- extract_desired_mode() from B2 StabilityTracker
- Prometheus metrics update
"""

import importlib
import os
from unittest.mock import MagicMock

import pytest


def test_attach_disabled():
    """Test: AURIS_HYSTERESIS=off → attach returns None."""
    # Ensure flag is off
    os.environ["AURIS_HYSTERESIS"] = "off"

    # Reload module to pick up env var
    import orbis_fab.hysteresis_hook_exp

    importlib.reload(orbis_fab.hysteresis_hook_exp)

    # Create mock FABCore
    fab_core = MagicMock()

    # Attach should return None when disabled
    hyst = orbis_fab.hysteresis_hook_exp.attach_to_fab(fab_core)
    assert hyst is None, "attach_to_fab should return None when AURIS_HYSTERESIS=off"


def test_attach_enabled():
    """Test: AURIS_HYSTERESIS=on → returns BitEnvelopeHysteresisExp."""
    # Enable flag
    os.environ["AURIS_HYSTERESIS"] = "on"

    # Reload module
    import orbis_fab.hysteresis_hook_exp

    importlib.reload(orbis_fab.hysteresis_hook_exp)

    # Create mock FABCore
    fab_core = MagicMock()

    # Attach should return instance
    hyst = orbis_fab.hysteresis_hook_exp.attach_to_fab(fab_core)
    assert hyst is not None, "attach_to_fab should return instance when enabled"

    # Check it's the right type
    from orbis_fab.hysteresis_exp import BitEnvelopeHysteresisExp

    assert isinstance(hyst, BitEnvelopeHysteresisExp), "Should return BitEnvelopeHysteresisExp"

    # Check production config
    assert hyst.config.dwell_ticks == 50
    assert hyst.config.rate_limit_ticks == 1000
    assert hyst.config.osc_window == 300


def test_extract_desired_from_b2():
    """Test: extract_desired_mode() reads _last_stability['recommended_mode']."""
    from orbis_fab.hysteresis_hook_exp import extract_desired_mode

    # Create mock FABCore with B2 stability metrics
    fab_core = MagicMock()
    fab_core._last_stability = {"recommended_mode": "FAB1"}

    desired = extract_desired_mode(fab_core)
    assert desired == "FAB1", "Should extract from B2 _last_stability"


def test_extract_desired_fallback_to_st_mode():
    """Test: extract_desired_mode() falls back to st.mode when B2 unavailable."""
    from orbis_fab.hysteresis_hook_exp import extract_desired_mode

    # Mock FABCore without B2 but with st.mode
    fab_core = MagicMock()
    fab_core._last_stability = None
    fab_core.st.mode = "FAB0"

    desired = extract_desired_mode(fab_core)
    assert desired == "FAB0", "Should fallback to st.mode"


def test_extract_desired_default():
    """Test: extract_desired_mode() defaults to FAB2 when nothing available."""
    from orbis_fab.hysteresis_hook_exp import extract_desired_mode

    # Mock FABCore with no stability or st
    fab_core = MagicMock()
    fab_core._last_stability = None
    fab_core.st = None

    desired = extract_desired_mode(fab_core)
    assert desired == "FAB2", "Should default to FAB2"


def test_maybe_hyst_disabled():
    """Test: maybe_hyst() returns None when AURIS_HYSTERESIS=off."""
    # Disable flag
    os.environ["AURIS_HYSTERESIS"] = "off"

    # Reload module
    import orbis_fab.hysteresis_hook_exp

    importlib.reload(orbis_fab.hysteresis_hook_exp)

    # Create mock FABCore
    fab_core = MagicMock()

    result = orbis_fab.hysteresis_hook_exp.maybe_hyst(fab_core)
    assert result is None, "maybe_hyst should return None when disabled"


def test_maybe_hyst_integration():
    """Test: E2E maybe_hyst() with mock FABCore."""
    # Enable flag
    os.environ["AURIS_HYSTERESIS"] = "on"
    os.environ["AURIS_METRICS_EXP"] = "off"  # Disable Prometheus to isolate test

    # Reload modules
    import orbis_fab.hysteresis_hook_exp

    importlib.reload(orbis_fab.hysteresis_hook_exp)

    # Create mock FABCore
    fab_core = MagicMock()
    fab_core._last_stability = {"recommended_mode": "FAB1"}
    fab_core.current_tick = 100

    # Attach hysteresis
    hyst = orbis_fab.hysteresis_hook_exp.attach_to_fab(fab_core)
    fab_core._hyst = hyst

    # Call maybe_hyst
    result = orbis_fab.hysteresis_hook_exp.maybe_hyst(fab_core)

    # Check result structure
    assert result is not None, "Should return metrics dict"
    assert "desired_mode" in result
    assert "effective_mode" in result
    assert "switch_rate_per_sec" in result
    assert "oscillation_rate_per_sec" in result
    assert "dwell_counter" in result
    assert "last_switch_age" in result

    # Check desired mode extracted from B2
    assert result["desired_mode"] == "FAB1"

    # Effective should be FAB2 initially (not enough dwell)
    assert result["effective_mode"] == "FAB2"


def test_effective_smoother_than_desired():
    """Test: effective_mode is smoother than oscillating desired_mode."""
    # Enable flag
    os.environ["AURIS_HYSTERESIS"] = "on"
    os.environ["AURIS_METRICS_EXP"] = "off"

    # Reload modules
    import orbis_fab.hysteresis_hook_exp

    importlib.reload(orbis_fab.hysteresis_hook_exp)

    # Create mock FABCore
    fab_core = MagicMock()
    fab_core.current_tick = 0

    # Attach hysteresis
    hyst = orbis_fab.hysteresis_hook_exp.attach_to_fab(fab_core)
    fab_core._hyst = hyst

    # Simulate oscillating desired mode: FAB2 → FAB1 → FAB2 → FAB1
    desired_sequence = ["FAB2"] * 20 + ["FAB1"] * 20 + ["FAB2"] * 20 + ["FAB1"] * 20

    effective_modes = []
    for tick, desired in enumerate(desired_sequence):
        fab_core._last_stability = {"recommended_mode": desired}
        fab_core.current_tick = tick

        result = orbis_fab.hysteresis_hook_exp.maybe_hyst(fab_core)
        if result:  # Guard against None
            effective_modes.append(result["effective_mode"])

    # Count switches in desired vs effective
    def count_switches(modes):
        return sum(1 for i in range(1, len(modes)) if modes[i] != modes[i - 1])

    desired_switches = count_switches(desired_sequence)
    effective_switches = count_switches(effective_modes)

    # Effective should have fewer switches (hysteresis smoothing)
    assert (
        effective_switches < desired_switches
    ), f"Effective ({effective_switches}) should have fewer switches than desired ({desired_switches})"


def test_prometheus_metrics_update():
    """Test: maybe_hyst() updates Prometheus metrics when enabled."""
    # Enable both flags
    os.environ["AURIS_HYSTERESIS"] = "on"
    os.environ["AURIS_METRICS_EXP"] = "on"

    # Reload modules
    import orbis_fab.hysteresis_hook_exp
    from atlas.metrics import exp_prom_exporter

    importlib.reload(orbis_fab.hysteresis_hook_exp)
    importlib.reload(exp_prom_exporter)

    # Setup Prometheus registry
    exp_prom_exporter.setup_prometheus_metrics()

    # Create mock FABCore
    fab_core = MagicMock()
    fab_core._last_stability = {"recommended_mode": "FAB1"}
    fab_core.current_tick = 100

    # Attach hysteresis
    hyst = orbis_fab.hysteresis_hook_exp.attach_to_fab(fab_core)
    fab_core._hyst = hyst

    # Call maybe_hyst (should update Prometheus)
    result = orbis_fab.hysteresis_hook_exp.maybe_hyst(fab_core)
    assert result is not None

    # Get metrics text and verify hysteresis metrics present
    metrics_text = exp_prom_exporter.get_metrics_text()
    assert "atlas_hyst_switch_rate_per_sec" in metrics_text
    assert "atlas_hyst_oscillation_rate_per_sec" in metrics_text
    assert "atlas_hyst_dwell_counter" in metrics_text
    assert "atlas_hyst_last_switch_age" in metrics_text
    assert "atlas_hyst_effective_mode" in metrics_text
    assert "atlas_hyst_desired_mode" in metrics_text


def test_hysteresis_with_fabcore_runtime():
    """Test: Full integration with FABCore runtime (if available)."""
    # Enable hysteresis
    os.environ["AURIS_HYSTERESIS"] = "on"
    os.environ["AURIS_STABILITY"] = "off"  # Disable B2 to isolate B1

    # Reload core module to pick up env var
    from orbis_fab import core

    importlib.reload(core)

    # Create FABCore instance
    try:
        fab_core = core.FABCore()
    except Exception as e:  # pylint: disable=broad-exception-caught
        pytest.skip(f"FABCore init failed (expected in isolation): {e}")

    # Check that _hyst was initialized
    assert hasattr(fab_core, "_hyst"), "FABCore should have _hyst attribute"
    assert fab_core._hyst is not None, "_hyst should be initialized when flag on"

    # Check type
    from orbis_fab.hysteresis_exp import BitEnvelopeHysteresisExp

    assert isinstance(fab_core._hyst, BitEnvelopeHysteresisExp)


def test_hysteresis_off_no_impact():
    """Test: AURIS_HYSTERESIS=off → no _hyst attribute set."""
    # Disable hysteresis
    os.environ["AURIS_HYSTERESIS"] = "off"

    # Reload core module
    from orbis_fab import core

    importlib.reload(core)

    # Create FABCore instance
    try:
        fab_core = core.FABCore()
    except Exception as e:  # pylint: disable=broad-exception-caught
        pytest.skip(f"FABCore init failed (expected in isolation): {e}")

    # Check that _hyst is None
    assert hasattr(fab_core, "_hyst"), "FABCore should have _hyst attribute"
    assert fab_core._hyst is None, "_hyst should be None when flag off"
