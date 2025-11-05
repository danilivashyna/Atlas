"""
Unit tests for hysteresis_exp.py (Phase B.1)

Tests BitEnvelopeHysteresisExp core logic:
- Dwell time enforcement (50 ticks)
- Global rate limiting (1000 ticks)
- Oscillation detection (300 tick window)
- Metrics output shape and validity
"""

from orbis_fab.hysteresis_exp import (
    BitEnvelopeHysteresisExp,
    HysteresisConfig,
)


def test_no_switch_before_dwell():
    """Test: desired mode changes but dwell_counter < 50 → stays in last_mode."""
    config = HysteresisConfig(
        dwell_ticks=50,
        rate_limit_ticks=1000,
        osc_window=300,
        max_history=5000,
    )
    hyst = BitEnvelopeHysteresisExp(config)

    # Start in FAB2
    current_tick = 0
    assert hyst.update("FAB2", current_tick) == "FAB2"

    # Request FAB1 but hold for only 30 ticks
    for i in range(1, 31):
        effective = hyst.update("FAB1", current_tick + i)
        assert effective == "FAB2", f"Should stay FAB2 until dwell satisfied (tick {i})"

    # Check dwell_counter
    metrics = hyst.get_metrics()
    assert metrics["dwell_counter"] == 30


def test_switch_after_dwell_satisfied():
    """Test: desired mode changes and dwell >= 50 → switch occurs."""
    config = HysteresisConfig(
        dwell_ticks=50,
        rate_limit_ticks=100,  # Lower rate limit for easier testing
        osc_window=300,
        max_history=5000,
    )
    hyst = BitEnvelopeHysteresisExp(config)

    # Start in FAB2
    current_tick = 0
    hyst.update("FAB2", current_tick)

    # Request FAB1 for 50 ticks
    for i in range(1, 50):
        effective = hyst.update("FAB1", current_tick + i)
        assert effective == "FAB2", f"Should stay FAB2 before dwell satisfied (tick {i})"

    # Tick 50: dwell satisfied + rate limit ok → switch
    effective = hyst.update("FAB1", current_tick + 50)
    assert effective == "FAB1", "Should switch to FAB1 after dwell satisfied"

    # Check metrics
    metrics = hyst.get_metrics()
    assert metrics["last_mode"] == "FAB1"
    assert metrics["last_switch_age"] == 0  # Just switched


def test_rate_limit_strict():
    """Test: two switches < 1000 ticks apart → second switch blocked."""
    config = HysteresisConfig(
        dwell_ticks=50,
        rate_limit_ticks=1000,
        osc_window=300,
        max_history=5000,
    )
    hyst = BitEnvelopeHysteresisExp(config)

    # Start in FAB2, tick=0
    current_tick = 0
    hyst.update("FAB2", current_tick)

    # Switch to FAB1 at tick=50 (dwell satisfied)
    for i in range(1, 51):
        hyst.update("FAB1", current_tick + i)
    assert hyst.update("FAB1", current_tick + 50) == "FAB1"

    # Now try to switch back to FAB2 at tick=150 (only 100 ticks later)
    # Dwell satisfied (50 ticks) but rate_limit NOT satisfied (< 1000)
    for i in range(51, 151):
        effective = hyst.update("FAB2", current_tick + i)
        if i < 51 + 50:
            # Still accumulating dwell
            assert effective == "FAB1"
        else:
            # Dwell satisfied but rate limit blocks
            assert effective == "FAB1", f"Rate limit should block switch (tick {i})"

    # Switch should succeed at tick=1050 (1000 ticks after first switch)
    for i in range(151, 1001):
        hyst.update("FAB2", current_tick + i)

    effective = hyst.update("FAB2", current_tick + 1050)
    assert effective == "FAB2", "Switch allowed after rate limit satisfied"


def test_dwell_reset_on_desired_equals_last():
    """Test: desired == last_mode → dwell_counter reset to 0."""
    config = HysteresisConfig(
        dwell_ticks=50,
        rate_limit_ticks=1000,
        osc_window=300,
        max_history=5000,
    )
    hyst = BitEnvelopeHysteresisExp(config)

    # Start in FAB2
    current_tick = 0
    hyst.update("FAB2", current_tick)

    # Request FAB1 for 30 ticks (dwell_counter = 30)
    for i in range(1, 31):
        hyst.update("FAB1", current_tick + i)

    metrics = hyst.get_metrics()
    assert metrics["dwell_counter"] == 30

    # Change desired back to FAB2 → dwell_counter should reset
    hyst.update("FAB2", current_tick + 31)
    metrics = hyst.get_metrics()
    assert metrics["dwell_counter"] == 0, "dwell_counter should reset when desired == last"


def test_oscillation_detection():
    """Test: FAB2↔FAB1↔FAB2 rapid switches → oscillation count increases."""
    config = HysteresisConfig(
        dwell_ticks=50,
        rate_limit_ticks=100,  # Low rate limit to allow rapid switches
        osc_window=300,
        max_history=5000,
    )
    hyst = BitEnvelopeHysteresisExp(config)

    current_tick = 0
    hyst.update("FAB2", current_tick)

    # Switch 1: FAB2 → FAB1 at tick 50
    for i in range(1, 51):
        hyst.update("FAB1", current_tick + i)
    hyst.update("FAB1", current_tick + 50)

    # Switch 2: FAB1 → FAB2 at tick 200 (150 ticks later, within osc_window)
    for i in range(51, 201):
        hyst.update("FAB2", current_tick + i)
    hyst.update("FAB2", current_tick + 200)

    # Switch 3: FAB2 → FAB1 at tick 350 (150 ticks later, within osc_window from switch 2)
    for i in range(201, 351):
        hyst.update("FAB1", current_tick + i)
    hyst.update("FAB1", current_tick + 350)

    # Check oscillation count
    metrics = hyst.get_metrics()
    assert metrics["osc_count"] >= 1, "Should detect at least one oscillation"


def test_metrics_shape():
    """Test: get_metrics() returns all expected keys with valid types."""
    config = HysteresisConfig(
        dwell_ticks=50,
        rate_limit_ticks=1000,
        osc_window=300,
        max_history=5000,
    )
    hyst = BitEnvelopeHysteresisExp(config)

    # Perform some updates
    hyst.update("FAB2", 0)
    hyst.update("FAB1", 10)

    metrics = hyst.get_metrics()

    # Check all keys present
    expected_keys = {
        "switch_rate_per_sec",
        "oscillation_rate_per_sec",
        "last_switch_age",
        "dwell_counter",
        "last_mode",
        "osc_count",
    }
    assert (
        set(metrics.keys()) == expected_keys
    ), f"Missing keys: {expected_keys - set(metrics.keys())}"

    # Check types
    assert isinstance(metrics["switch_rate_per_sec"], float)
    assert isinstance(metrics["oscillation_rate_per_sec"], float)
    assert isinstance(metrics["last_switch_age"], int)
    assert isinstance(metrics["dwell_counter"], int)
    assert isinstance(metrics["last_mode"], str)
    assert isinstance(metrics["osc_count"], int)

    # Check value ranges
    assert metrics["switch_rate_per_sec"] >= 0.0
    assert metrics["oscillation_rate_per_sec"] >= 0.0
    assert metrics["last_switch_age"] >= 0
    assert metrics["dwell_counter"] >= 0
    assert metrics["last_mode"] in {"FAB0", "FAB1", "FAB2"}
    assert metrics["osc_count"] >= 0


def test_switch_history_maxlen():
    """Test: switch_history deque doesn't exceed max_history."""
    config = HysteresisConfig(
        dwell_ticks=50,
        rate_limit_ticks=100,
        osc_window=300,
        max_history=10,  # Small limit for testing
    )
    hyst = BitEnvelopeHysteresisExp(config)

    current_tick = 0
    hyst.update("FAB2", current_tick)

    # Perform 15 switches (> max_history)
    modes = ["FAB1", "FAB2"] * 8  # Alternating modes
    for idx, mode in enumerate(modes):
        tick = current_tick + (idx + 1) * 150  # Sufficient spacing for rate limit
        for i in range(50):
            hyst.update(mode, tick + i)
        hyst.update(mode, tick + 50)

    # Check that history length <= max_history
    history_len = len(hyst.state.switch_history)
    assert history_len <= config.max_history, f"History exceeded max_history: {history_len}"


def test_initial_state_defaults():
    """Test: initial state is FAB2 with no switches."""
    config = HysteresisConfig(
        dwell_ticks=50,
        rate_limit_ticks=1000,
        osc_window=300,
        max_history=5000,
    )
    hyst = BitEnvelopeHysteresisExp(config)

    metrics = hyst.get_metrics()
    assert metrics["last_mode"] == "FAB2", "Initial mode should be FAB2"
    assert metrics["dwell_counter"] == 0
    assert metrics["osc_count"] == 0
    assert metrics["switch_rate_per_sec"] == 0.0
    assert metrics["oscillation_rate_per_sec"] == 0.0


def test_multiple_mode_switches():
    """Test: FAB2 → FAB1 → FAB0 → FAB2 sequence with proper spacing."""
    config = HysteresisConfig(
        dwell_ticks=50,
        rate_limit_ticks=1000,
        osc_window=300,
        max_history=5000,
    )
    hyst = BitEnvelopeHysteresisExp(config)

    current_tick = 0
    hyst.update("FAB2", current_tick)

    # Switch to FAB1 at tick 50
    for i in range(1, 51):
        hyst.update("FAB1", current_tick + i)
    assert hyst.update("FAB1", current_tick + 50) == "FAB1"

    # Switch to FAB0 at tick 1100 (1000 ticks later)
    for i in range(51, 1151):
        hyst.update("FAB0", current_tick + i)
    assert hyst.update("FAB0", current_tick + 1100) == "FAB0"

    # Switch to FAB2 at tick 2150 (1000 ticks later)
    for i in range(1101, 2201):
        hyst.update("FAB2", current_tick + i)
    assert hyst.update("FAB2", current_tick + 2150) == "FAB2"

    # Check final state
    metrics = hyst.get_metrics()
    assert metrics["last_mode"] == "FAB2"
    assert len(hyst.state.switch_history) == 3  # Three switches total
