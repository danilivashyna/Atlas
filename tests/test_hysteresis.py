"""Test FAB hysteresis envelope - Phase B

Tests precision hysteresis to prevent oscillation:
- Dwell time before upgrade (3 ticks default)
- Dead band prevents dithering
- Immediate downgrade on drop below down_threshold
- Rate limit: ≤1 change per rate_limit_ticks

Invariants:
- Precision stable in dead band [down, up]
- Upgrade requires dwell_time consecutive ticks
- Downgrade immediate (but rate-limited)
- No mid-tick changes
"""

from orbis_fab.hysteresis import (
    assign_precision_hysteresis,
    HysteresisState,
    HysteresisConfig,
)


def test_hysteresis_upgrade_requires_dwell():
    """Upgrade from cold→warm requires 3 ticks dwell"""
    config = HysteresisConfig(dwell_time=3, rate_limit_ticks=1)
    state = HysteresisState(current_precision="mxfp4.12")

    # Tick 1: score crosses warm_low_up (0.45)
    precision, state = assign_precision_hysteresis(0.50, state, config, current_tick=100)
    assert precision == "mxfp4.12"  # Still cold, dwelling
    assert state.dwell_counter == 1
    assert state.target_precision == "mxfp5.25"

    # Tick 2: score still above threshold
    precision, state = assign_precision_hysteresis(0.51, state, config, current_tick=101)
    assert precision == "mxfp4.12"  # Still cold, dwelling
    assert state.dwell_counter == 2

    # Tick 3: dwell time reached → upgrade
    precision, state = assign_precision_hysteresis(0.52, state, config, current_tick=102)
    assert precision == "mxfp5.25"  # Upgraded to warm-low
    assert state.dwell_counter == 0
    assert state.last_change_tick == 102


def test_hysteresis_downgrade_immediate():
    """Downgrade is immediate when score drops below down_threshold"""
    config = HysteresisConfig(rate_limit_ticks=1)
    state = HysteresisState(current_precision="mxfp5.25", last_change_tick=0)

    # Score drops below warm_low_down (0.35) → immediate downgrade
    precision, state = assign_precision_hysteresis(0.30, state, config, current_tick=100)
    assert precision == "mxfp4.12"  # Immediate downgrade to cold
    assert state.last_change_tick == 100


def test_hysteresis_dead_band_prevents_dithering():
    """Score hovering in dead band [down, up] holds current precision"""
    config = HysteresisConfig(
        warm_low_up=0.45, warm_low_down=0.35, dwell_time=3, rate_limit_ticks=1
    )

    # Start at warm-low precision (already upgraded earlier)
    state = HysteresisState(
        current_precision="mxfp5.25", last_change_tick=50  # Changed 50 ticks ago (>rate_limit)
    )

    # Score oscillates in dead band [0.35, 0.45]
    # 0.40, 0.42 are above warm_low_down (0.35), so should hold mxfp5.25
    # 0.38, 0.41, 0.39 are also in dead band
    for score in [0.40, 0.42, 0.38, 0.41, 0.39]:
        precision, state = assign_precision_hysteresis(score, state, config, current_tick=100)
        assert precision == "mxfp5.25", f"Should hold mxfp5.25 in dead band (score={score})"


def test_hysteresis_rate_limit_enforced():
    """Rate limit prevents changes within rate_limit_ticks window"""
    config = HysteresisConfig(
        warm_low_up=0.45,
        warm_low_down=0.35,
        dwell_time=2,  # Need 2 ticks to upgrade
        rate_limit_ticks=1000,  # 1000 ticks between changes
    )

    # Start at cold, upgrade to warm over 2 ticks
    state = HysteresisState(current_precision="mxfp4.12", last_change_tick=0)

    # Tick 0: start dwelling
    precision, state = assign_precision_hysteresis(0.50, state, config, current_tick=0)
    assert precision == "mxfp4.12"  # Still cold, dwell=1

    # Tick 1: upgrade (dwell=2)
    precision, state = assign_precision_hysteresis(0.50, state, config, current_tick=1)
    assert precision == "mxfp5.25"  # Upgraded to warm-low
    assert state.last_change_tick == 1

    # Try to downgrade at tick 100 (too soon, <1000 ticks since change)
    prec, state = assign_precision_hysteresis(0.30, state, config, current_tick=100)
    assert prec == "mxfp5.25"  # Still warm, rate limit blocks downgrade

    # Try again at tick 1001 (1001-1=1000, exactly at rate limit)
    precision, state = assign_precision_hysteresis(0.30, state, config, current_tick=1001)
    assert precision == "mxfp4.12"  # Now downgrade allowed


def test_hysteresis_target_change_resets_dwell():
    """Changing target score resets dwell counter"""
    config = HysteresisConfig(dwell_time=3, rate_limit_ticks=1)
    state = HysteresisState(current_precision="mxfp4.12")

    # Tick 1: target warm-low (0.50)
    _precision, state = assign_precision_hysteresis(0.50, state, config, current_tick=100)
    assert state.dwell_counter == 1
    assert state.target_precision == "mxfp5.25"

    # Tick 2: target changes to warm-high (0.70)
    _precision, state = assign_precision_hysteresis(0.70, state, config, current_tick=101)
    assert state.dwell_counter == 1  # Reset to 1
    assert state.target_precision == "mxfp6.0"  # New target


def test_hysteresis_hot_to_cold_gradual():
    """Downgrade from hot follows intermediate steps"""
    config = HysteresisConfig(rate_limit_ticks=1)

    # Start at hot
    state = HysteresisState(current_precision="mxfp8.0", last_change_tick=0)

    # Score drops to warm-high range (0.65)
    precision, state = assign_precision_hysteresis(0.65, state, config, current_tick=100)
    assert precision == "mxfp6.0"  # Downgrade to warm-high

    # Score drops further to warm-low range (0.50)
    precision, state = assign_precision_hysteresis(0.50, state, config, current_tick=200)
    assert precision == "mxfp5.25"  # Downgrade to warm-low

    # Score drops to cold range (0.30)
    precision, state = assign_precision_hysteresis(0.30, state, config, current_tick=300)
    assert precision == "mxfp4.12"  # Downgrade to cold


def test_hysteresis_stable_at_target():
    """Holding at target score resets dwell counter"""
    config = HysteresisConfig(dwell_time=3, rate_limit_ticks=1)

    # Start at warm-low
    state = HysteresisState(current_precision="mxfp5.25", last_change_tick=50)

    # Score stable at 0.50 (matches current precision)
    for tick in range(100, 105):
        prec, state = assign_precision_hysteresis(0.50, state, config, current_tick=tick)
        assert prec == "mxfp5.25"
        assert state.dwell_counter == 0  # Always 0 when at target


def test_hysteresis_realistic_scenario():
    """Realistic score progression with multiple transitions"""
    config = HysteresisConfig(
        dwell_time=3,
        rate_limit_ticks=10,  # Faster for testing
        hot_up=0.85,
        hot_down=0.75,
        warm_high_up=0.65,
        warm_high_down=0.55,
    )

    state = HysteresisState(current_precision="mxfp4.12", last_change_tick=0)

    # Gradual score increase
    scores = [0.40, 0.50, 0.52, 0.54, 0.56, 0.70, 0.72, 0.74, 0.76, 0.90, 0.92, 0.94]

    tick = 0
    final_precision = None
    for score in scores:
        final_precision, state = assign_precision_hysteresis(
            score, state, config, current_tick=tick
        )
        tick += 1

    # After 12 ticks with increasing scores:
    # - Should have upgraded through warm-low, warm-high, eventually to hot
    # - Exact final state depends on dwell and rate limits
    # - Key: no dithering, smooth transitions

    # Final precision should be hot or warm-high (score=0.94 is ≥0.85)
    assert final_precision in ["mxfp8.0", "mxfp6.0"]


def test_hysteresis_no_change_when_stable():
    """No precision change when score stable within band"""
    config = HysteresisConfig(dwell_time=3, rate_limit_ticks=1)
    state = HysteresisState(current_precision="mxfp6.0", last_change_tick=0)

    # Score stable in warm-high range [0.65, 0.85)
    for score in [0.70, 0.72, 0.75, 0.78, 0.80]:
        precision, state = assign_precision_hysteresis(score, state, config, current_tick=100)
        assert precision == "mxfp6.0", f"Should hold mxfp6.0 (score={score})"
        assert state.dwell_counter == 0
