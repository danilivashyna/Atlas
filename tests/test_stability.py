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
"""

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
    config = StabilityConfig(
        min_stable_ticks=10,
        cooldown_base=2.0,
        cooldown_max_ticks=1000
    )
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
    config = StabilityConfig(
        cooldown_base=2.0,
        cooldown_max_ticks=100
    )
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
    config = StabilityConfig(
        min_stable_ticks=10,
        degradation_threshold=0.1  # 10% drop
    )
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
    config = StabilityConfig(
        min_stable_ticks=10,
        cooldown_base=2.0
    )
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
    config = StabilityConfig(
        min_stable_ticks=10,
        cooldown_base=2.0,
        degradation_threshold=0.15
    )
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
