"""
Tests for Window Stability Counter (Phase B.2)

Coverage:
- Stable ticks accumulation
- Degradation detection (explicit + score drop)
- Exponential cool-down (2^n growth)
- Cool-down max cap
- Stability status checks
- Stability score computation
- Reset functionality
- EMA tracking and convergence (Phase B.2)
- Degradation events per hour (Phase B.2)
- FAB mode recommendation (Phase B.2)
- Property-based invariants (hypothesis)
"""

import time
from hypothesis import given, strategies as st

from src.orbis_fab.stability import (
    StabilityConfig,
    StabilityTracker,
)


def test_stability_accumulation():
    """Stable ticks accumulate when no degradation"""
    config = StabilityConfig(min_stable_ticks=10)
    tracker = StabilityTracker(config=config)

    # Tick 10 times without degradation
    for i in range(10):
        tracker.tick(current_score=0.8, degraded=False)
        assert tracker.state.stable_ticks == i + 1

    # Should be stable after 10 ticks
    assert tracker.is_stable()
    assert tracker.stability_score() == 1.0


def test_stability_degradation_resets_counter():
    """Degradation event resets stable_ticks to 0"""
    config = StabilityConfig(min_stable_ticks=10)
    tracker = StabilityTracker(config=config)

    # Accumulate 5 stable ticks
    for _ in range(5):
        tracker.tick(current_score=0.8, degraded=False)

    assert tracker.state.stable_ticks == 5

    # Degradation resets counter
    tracker.tick(current_score=0.8, degraded=True)
    assert tracker.state.stable_ticks == 0
    assert tracker.state.degradation_count == 1


def test_stability_exponential_cooldown():
    """Cool-down period grows exponentially: 2^1, 2^2, 2^3, ..."""
    config = StabilityConfig(min_stable_ticks=10, cooldown_base=2.0, cooldown_max_ticks=1000)
    tracker = StabilityTracker(config=config)

    # First degradation: cooldown = 2^1 = 2 ticks
    tracker.tick(current_score=0.8, degraded=True)
    assert tracker.state.cooldown_remaining == 2
    assert tracker.state.is_in_cooldown

    # Wait out cool-down (2 ticks)
    tracker.tick(current_score=0.8, degraded=False)  # cooldown_remaining=1
    assert tracker.state.is_in_cooldown
    tracker.tick(current_score=0.8, degraded=False)  # cooldown_remaining=0
    assert not tracker.state.is_in_cooldown

    # Second degradation: cooldown = 2^2 = 4 ticks
    tracker.tick(current_score=0.8, degraded=True)
    assert tracker.state.cooldown_remaining == 4
    assert tracker.state.degradation_count == 2

    # Third degradation (skip cooldown): cooldown = 2^3 = 8 ticks
    tracker.state.is_in_cooldown = False  # Force skip for test
    tracker.tick(current_score=0.8, degraded=True)
    assert tracker.state.cooldown_remaining == 8
    assert tracker.state.degradation_count == 3


def test_stability_cooldown_max_cap():
    """Cool-down duration capped at cooldown_max_ticks"""
    config = StabilityConfig(cooldown_base=2.0, cooldown_max_ticks=100)
    tracker = StabilityTracker(config=config)

    # Simulate many degradations to exceed cap
    # 2^10 = 1024 > 100 (cap)
    tracker.state.degradation_count = 10
    tracker.tick(current_score=0.8, degraded=True)

    # Should be capped at 100
    assert tracker.state.cooldown_remaining == 100
    assert tracker.state.degradation_count == 11


def test_stability_score_during_cooldown():
    """Stability score is 0.0 during cool-down"""
    config = StabilityConfig(min_stable_ticks=10)
    tracker = StabilityTracker(config=config)

    # Accumulate some stable ticks
    for _ in range(5):
        tracker.tick(current_score=0.8, degraded=False)

    # Before degradation: score = 5/10 = 0.5
    assert tracker.stability_score() == 0.5

    # Trigger degradation
    tracker.tick(current_score=0.8, degraded=True)

    # During cool-down: score = 0.0
    assert tracker.stability_score() == 0.0
    assert not tracker.is_stable()


def test_stability_score_partial():
    """Stability score grows linearly before reaching min_stable_ticks"""
    config = StabilityConfig(min_stable_ticks=100)
    tracker = StabilityTracker(config=config)

    # 25 stable ticks → score = 25/100 = 0.25
    for _ in range(25):
        tracker.tick(current_score=0.8, degraded=False)

    assert tracker.stability_score() == 0.25
    assert not tracker.is_stable()  # Not yet stable (25 < 100)

    # 100 stable ticks → score = 100/100 = 1.0
    for _ in range(75):
        tracker.tick(current_score=0.8, degraded=False)

    assert tracker.stability_score() == 1.0
    assert tracker.is_stable()


def test_stability_auto_detect_score_drop():
    """Degradation auto-detected from score drop >= threshold"""
    config = StabilityConfig(min_stable_ticks=10, degradation_threshold=0.1)  # 10% drop
    tracker = StabilityTracker(config=config)

    # First tick: establish baseline
    tracker.tick(current_score=0.8, degraded=False)
    assert tracker.state.stable_ticks == 1

    # Second tick: small drop (0.8 → 0.75 = 0.05 drop < 0.1 threshold)
    tracker.tick(current_score=0.75, degraded=False)
    assert tracker.state.stable_ticks == 2  # No degradation

    # Third tick: large drop (0.75 → 0.60 = 0.15 drop >= 0.1 threshold)
    tracker.tick(current_score=0.60, degraded=False)
    assert tracker.state.stable_ticks == 0  # Auto-degraded
    assert tracker.state.degradation_count == 1


def test_stability_cooldown_blocks_accumulation():
    """Stable ticks don't accumulate during cool-down"""
    config = StabilityConfig(min_stable_ticks=10, cooldown_base=2.0)
    tracker = StabilityTracker(config=config)

    # Trigger degradation (cooldown = 2^1 = 2 ticks)
    tracker.tick(current_score=0.8, degraded=True)
    assert tracker.state.cooldown_remaining == 2
    assert tracker.state.is_in_cooldown

    # First tick during cool-down
    tracker.tick(current_score=0.8, degraded=False)
    assert tracker.state.stable_ticks == 0  # Blocked
    assert tracker.state.cooldown_remaining == 1
    assert tracker.state.is_in_cooldown  # Still in cooldown

    # Second tick: cooldown ends, accumulation resumes in same tick
    tracker.tick(current_score=0.8, degraded=False)
    assert tracker.state.cooldown_remaining == 0
    assert not tracker.state.is_in_cooldown  # Cooldown ended
    assert tracker.state.stable_ticks == 1  # Accumulation resumed

    # Third tick: normal accumulation
    tracker.tick(current_score=0.8, degraded=False)
    assert tracker.state.stable_ticks == 2


def test_stability_reset():
    """Reset clears all state"""
    config = StabilityConfig(min_stable_ticks=10)
    tracker = StabilityTracker(config=config)

    # Build up state
    for _ in range(5):
        tracker.tick(current_score=0.8, degraded=False)
    tracker.tick(current_score=0.8, degraded=True)

    assert tracker.state.stable_ticks == 0
    assert tracker.state.degradation_count == 1
    assert tracker.state.is_in_cooldown

    # Reset
    tracker.reset()

    assert tracker.state.stable_ticks == 0
    assert tracker.state.degradation_count == 0
    assert tracker.state.cooldown_remaining == 0
    assert not tracker.state.is_in_cooldown
    assert tracker.state.last_score is None


def test_stability_get_cooldown_info():
    """Diagnostics info includes all key state"""
    config = StabilityConfig(min_stable_ticks=10)
    tracker = StabilityTracker(config=config)

    # Accumulate some state
    for _ in range(5):
        tracker.tick(current_score=0.8, degraded=False)
    tracker.tick(current_score=0.8, degraded=True)

    info = tracker.get_cooldown_info()

    assert info["is_in_cooldown"] is True
    assert info["cooldown_remaining"] == 2  # 2^1
    assert info["degradation_count"] == 1
    assert info["stable_ticks"] == 0


def test_stability_realistic_scenario():
    """Realistic scenario: gradual stabilization after multiple degradations"""
    config = StabilityConfig(min_stable_ticks=10, cooldown_base=2.0, degradation_threshold=0.15)
    tracker = StabilityTracker(config=config)

    # Phase 1: Initial stable period (5 ticks)
    for _ in range(5):
        tracker.tick(current_score=0.8, degraded=False)
    assert tracker.state.stable_ticks == 5

    # Phase 2: Degradation (cooldown = 2 ticks)
    tracker.tick(current_score=0.5, degraded=False)  # Auto-detects drop
    assert tracker.state.degradation_count == 1
    assert tracker.state.is_in_cooldown

    # Phase 3: Wait out cooldown (2 ticks)
    tracker.tick(current_score=0.8, degraded=False)  # cooldown=1, still blocked
    tracker.tick(current_score=0.8, degraded=False)  # cooldown=0, stable_ticks=1
    assert not tracker.state.is_in_cooldown
    assert tracker.state.stable_ticks == 1  # Accumulation started

    # Phase 4: Rebuild stability (9 more ticks to reach stable_ticks=10)
    for i in range(9):
        tracker.tick(current_score=0.8, degraded=False)
        # stable_ticks: 2, 3, ..., 10 (after 9 ticks)
        # is_stable() when stable_ticks >= 10 (at i=8, stable_ticks=10)
        if i < 8:
            assert not tracker.is_stable()
        else:
            assert tracker.is_stable()

    assert tracker.state.stable_ticks == 10

    # Phase 5: Another degradation (cooldown = 4 ticks now)
    tracker.tick(current_score=0.6, degraded=False)
    assert tracker.state.degradation_count == 2
    assert tracker.state.cooldown_remaining == 4


# ──────────────────────────────────────────────────────────
# Phase B.2 Tests: EMA, degradation_events_per_hour, mode recommendation
# ──────────────────────────────────────────────────────────


def test_stability_score_ema_updates():
    """EMA updates with each tick based on current stability_score"""
    config = StabilityConfig(min_stable_ticks=10, ema_decay=0.9)
    tracker = StabilityTracker(config=config)

    # Initial EMA should be 1.0
    assert tracker.state.stability_score_ema == 1.0

    # Tick with degradation (stability_score=0.0)
    tracker.tick(current_score=0.8, degraded=True)
    # EMA = 0.9 * 1.0 + 0.1 * 0.0 = 0.9
    assert abs(tracker.state.stability_score_ema - 0.9) < 0.01

    # Tick stable (but still in cooldown, so stability_score=0.0)
    tracker.tick(current_score=0.8, degraded=False)
    # EMA = 0.9 * 0.9 + 0.1 * 0.0 = 0.81
    assert abs(tracker.state.stability_score_ema - 0.81) < 0.01


def test_stability_score_ema_converges():
    """EMA converges to stability_score over time"""
    config = StabilityConfig(min_stable_ticks=10, ema_decay=0.95)
    tracker = StabilityTracker(config=config)

    # Run 100 stable ticks (stability_score will reach 1.0 after 10 ticks)
    for _ in range(100):
        tracker.tick(current_score=0.8, degraded=False)

    # EMA should be close to 1.0 (converged)
    assert tracker.state.stability_score_ema > 0.99


def test_get_stability_score_ema():
    """get_stability_score_ema() returns current EMA value"""
    config = StabilityConfig(ema_decay=0.9)
    tracker = StabilityTracker(config=config)

    tracker.tick(current_score=0.8, degraded=True)
    ema = tracker.get_stability_score_ema()

    assert abs(ema - tracker.state.stability_score_ema) < 0.001


def test_degradation_events_per_hour_empty():
    """degradation_events_per_hour() returns 0.0 when no events"""
    tracker = StabilityTracker()

    assert tracker.degradation_events_per_hour() == 0.0


def test_degradation_events_per_hour_tracks_events():
    """degradation_events_per_hour() counts events in last hour"""
    import time

    tracker = StabilityTracker()

    # Record 3 degradation events
    for _ in range(3):
        tracker.tick(current_score=0.8, degraded=True)
        # Small delay to avoid same timestamp
        time.sleep(0.001)

    events = tracker.degradation_events_per_hour()
    assert events == 3.0


def test_degradation_events_per_hour_sliding_window():
    """Old events (>1h) are not counted"""
    import time

    tracker = StabilityTracker()

    # Add old event (manually set timestamp to 2 hours ago)
    two_hours_ago = time.time() - 7200
    tracker.state.degradation_timestamps.append(two_hours_ago)

    # Add recent event
    tracker.tick(current_score=0.8, degraded=True)

    # Should only count recent event
    events = tracker.degradation_events_per_hour()
    assert events == 1.0

    # Old timestamp should be cleaned up
    assert len(tracker.state.degradation_timestamps) == 1


def test_should_degrade_false_when_ema_high():
    """should_degrade() returns False when ema >= threshold"""
    tracker = StabilityTracker()

    # EMA starts at 1.0
    assert not tracker.should_degrade(threshold=0.5)


def test_should_degrade_true_when_ema_low():
    """should_degrade() returns True when ema < threshold"""
    config = StabilityConfig(ema_decay=0.5)
    tracker = StabilityTracker(config=config)

    # Degrade several times to lower EMA
    for _ in range(10):
        tracker.tick(current_score=0.8, degraded=True)

    # EMA should be very low now
    assert tracker.should_degrade(threshold=0.5)


def test_recommend_mode_fab2_when_ema_high():
    """recommend_mode() returns FAB2 when ema >= 0.8"""
    tracker = StabilityTracker()

    # EMA starts at 1.0
    assert tracker.recommend_mode() == "FAB2"


def test_recommend_mode_fab1_when_ema_medium():
    """recommend_mode() returns FAB1 when 0.5 <= ema < 0.8"""
    config = StabilityConfig(ema_decay=0.9)
    tracker = StabilityTracker(config=config)

    # Degrade once to lower EMA to ~0.7-0.8 range
    for _ in range(3):
        tracker.tick(current_score=0.8, degraded=True)
        tracker.tick(current_score=0.8, degraded=False)

    # Should be in FAB1 range
    mode = tracker.recommend_mode()
    assert mode in ["FAB1", "FAB2"]  # Depends on exact EMA convergence


def test_recommend_mode_fab0_when_ema_low():
    """recommend_mode() returns FAB0 when ema < 0.5"""
    config = StabilityConfig(ema_decay=0.5)
    tracker = StabilityTracker(config=config)

    # Degrade many times
    for _ in range(10):
        tracker.tick(current_score=0.8, degraded=True)

    assert tracker.recommend_mode() == "FAB0"


def test_get_metrics_comprehensive():
    """get_metrics() returns all stability metrics"""
    tracker = StabilityTracker()

    # Run some ticks
    tracker.tick(current_score=0.8, degraded=False)
    tracker.tick(current_score=0.8, degraded=True)

    metrics = tracker.get_metrics()

    # Check all expected keys
    assert "stability_score" in metrics
    assert "stability_score_ema" in metrics
    assert "degradation_events_per_hour" in metrics
    assert "is_in_cooldown" in metrics
    assert "cooldown_remaining" in metrics
    assert "degradation_count" in metrics
    assert "stable_ticks" in metrics
    assert "recommended_mode" in metrics

    # Validate types
    assert isinstance(metrics["stability_score"], float)
    assert isinstance(metrics["stability_score_ema"], float)
    assert isinstance(metrics["degradation_events_per_hour"], float)
    assert isinstance(metrics["is_in_cooldown"], bool)
    assert isinstance(metrics["recommended_mode"], str)


# ──────────────────────────────────────────────────────────
# Property-based tests (hypothesis) - Phase B.2
# ──────────────────────────────────────────────────────────


@given(
    num_ticks=st.integers(min_value=1, max_value=500),
    degradation_rate=st.floats(min_value=0.0, max_value=1.0),
)
def test_property_stability_score_in_bounds(num_ticks, degradation_rate):
    """Property: stability_score always in [0.0, 1.0]"""
    tracker = StabilityTracker()

    for i in range(num_ticks):
        # Degrade randomly based on rate
        degraded = (i % 10) < (degradation_rate * 10)
        tracker.tick(current_score=0.8, degraded=degraded)

        # Invariant: stability_score ∈ [0, 1]
        score = tracker.stability_score()
        assert 0.0 <= score <= 1.0


@given(
    num_ticks=st.integers(min_value=1, max_value=500),
    degradation_rate=st.floats(min_value=0.0, max_value=1.0),
)
def test_property_stability_score_ema_in_bounds(num_ticks, degradation_rate):
    """Property: stability_score_ema always in [0.0, 1.0]"""
    tracker = StabilityTracker()

    for i in range(num_ticks):
        degraded = (i % 10) < (degradation_rate * 10)
        tracker.tick(current_score=0.8, degraded=degraded)

        # Invariant: EMA ∈ [0, 1]
        ema = tracker.get_stability_score_ema()
        assert 0.0 <= ema <= 1.0


@given(
    ema_decay=st.floats(min_value=0.5, max_value=0.99),
    num_stable_ticks=st.integers(min_value=50, max_value=200),
)
def test_property_ema_converges_to_one(ema_decay, num_stable_ticks):
    """Property: EMA converges to 1.0 with sustained stability"""
    config = StabilityConfig(min_stable_ticks=10, ema_decay=ema_decay)
    tracker = StabilityTracker(config=config)

    # Run many stable ticks
    for _ in range(num_stable_ticks):
        tracker.tick(current_score=0.8, degraded=False)

    # EMA should be very close to 1.0
    ema = tracker.get_stability_score_ema()
    assert ema > 0.9  # Converged to high value


@given(
    cooldown_base=st.floats(min_value=1.5, max_value=3.0),
    num_degradations=st.integers(min_value=1, max_value=5),
)
def test_property_cooldown_grows_exponentially(cooldown_base, num_degradations):
    """Property: Cooldown duration grows as cooldown_base^n"""
    config = StabilityConfig(cooldown_base=cooldown_base, cooldown_max_ticks=10000)
    tracker = StabilityTracker(config=config)

    for n in range(1, num_degradations + 1):
        # Force degradation (skip cooldown for test)
        tracker.state.is_in_cooldown = False
        tracker.tick(current_score=0.8, degraded=True)

        expected_cooldown = min(int(cooldown_base**n), 10000)

        # Allow small rounding differences
        actual_cooldown = tracker.state.cooldown_remaining
        assert abs(actual_cooldown - expected_cooldown) <= 1


@given(
    min_stable_ticks=st.integers(min_value=10, max_value=200),
    num_ticks=st.integers(min_value=50, max_value=300),
)
def test_property_stable_only_after_min_ticks(min_stable_ticks, num_ticks):
    """Property: is_stable() returns True only after min_stable_ticks accumulated"""
    config = StabilityConfig(min_stable_ticks=min_stable_ticks)
    tracker = StabilityTracker(config=config)

    for i in range(num_ticks):
        tracker.tick(current_score=0.8, degraded=False)

        if i + 1 < min_stable_ticks:
            # Should NOT be stable yet
            assert not tracker.is_stable() or tracker.state.stable_ticks >= min_stable_ticks
        else:
            # Should be stable after min_stable_ticks
            assert tracker.is_stable()


@given(
    num_recent_events=st.integers(min_value=0, max_value=20),
)
def test_property_degradation_events_matches_count(num_recent_events):
    """Property: degradation_events_per_hour() equals number of recent events"""
    tracker = StabilityTracker()

    # Add events
    for _ in range(num_recent_events):
        tracker.tick(current_score=0.8, degraded=True)
        time.sleep(0.001)  # Small delay to avoid same timestamp

    events = tracker.degradation_events_per_hour()
    assert events == float(num_recent_events)
