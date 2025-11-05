"""
Tests for Stability Hook (Experimental) - Phase B.2 Runtime Integration

Verifies:
- Feature flag behavior
- Attach/detach logic
- FAB state extraction (minimal contract)
- Degradation detection
- Tick integration
"""

import os
import pytest
from unittest.mock import Mock


@pytest.fixture(autouse=True)
def reset_module():
    """Reset module state before each test."""
    import importlib
    import src.orbis_fab.stability_hook_exp as hook_mod

    importlib.reload(hook_mod)
    yield
    importlib.reload(hook_mod)


def test_is_enabled_when_flag_on(monkeypatch):
    """Feature flag on → is_enabled() returns True"""
    monkeypatch.setenv("AURIS_STABILITY_HOOK", "on")

    # Reload module to pick up env var
    import importlib
    import src.orbis_fab.stability_hook_exp as hook_mod

    importlib.reload(hook_mod)

    assert hook_mod.is_enabled() is True


def test_is_enabled_when_flag_off(monkeypatch):
    """Feature flag off → is_enabled() returns False"""
    monkeypatch.setenv("AURIS_STABILITY_HOOK", "off")

    import importlib
    import src.orbis_fab.stability_hook_exp as hook_mod

    importlib.reload(hook_mod)

    assert hook_mod.is_enabled() is False


def test_attach_disabled(monkeypatch):
    """attach() returns None when disabled"""
    monkeypatch.setenv("AURIS_STABILITY_HOOK", "off")

    import importlib
    import src.orbis_fab.stability_hook_exp as hook_mod

    importlib.reload(hook_mod)

    fab_core = Mock()
    result = hook_mod.attach(fab_core)

    assert result is None


def test_attach_enabled(monkeypatch):
    """attach() returns (tracker, tick_fn) when enabled"""
    monkeypatch.setenv("AURIS_STABILITY_HOOK", "on")

    import importlib
    import src.orbis_fab.stability_hook_exp as hook_mod

    importlib.reload(hook_mod)

    fab_core = Mock()
    result = hook_mod.attach(fab_core, decay=0.9, min_stable_ticks=50)

    assert result is not None
    tracker, tick_fn = result

    # Verify tracker is StabilityTracker instance
    assert tracker is not None
    assert callable(tick_fn)

    # Verify config applied
    assert tracker.config.ema_decay == 0.9
    assert tracker.config.min_stable_ticks == 50


def test_extract_fab_score_coherence():
    """extract_fab_score() uses coherence_score if available"""
    from src.orbis_fab.stability_hook_exp import extract_fab_score

    fab_core = Mock()
    fab_core.coherence_score = 0.75

    score = extract_fab_score(fab_core)
    assert score == 0.75


def test_extract_fab_score_quality():
    """extract_fab_score() falls back to quality_score"""
    from src.orbis_fab.stability_hook_exp import extract_fab_score

    fab_core = Mock(spec=[])  # No coherence_score
    fab_core.quality_score = 0.85

    score = extract_fab_score(fab_core)
    assert score == 0.85


def test_extract_fab_score_default():
    """extract_fab_score() returns 0.8 as default"""
    from src.orbis_fab.stability_hook_exp import extract_fab_score

    fab_core = Mock(spec=[])  # No score attributes

    score = extract_fab_score(fab_core)
    assert score == 0.8


def test_detect_degradation_explicit_flag():
    """detect_degradation() uses explicit degraded flag"""
    from src.orbis_fab.stability_hook_exp import detect_degradation

    fab_core = Mock()
    fab_core.degraded = True

    assert detect_degradation(fab_core) is True

    fab_core.degraded = False
    assert detect_degradation(fab_core) is False


def test_detect_degradation_mode_downgrade():
    """detect_degradation() detects mode downgrade (FAB2 → FAB1)"""
    from src.orbis_fab.stability_hook_exp import detect_degradation

    fab_core = Mock()
    fab_core.degraded = None  # No explicit flag
    fab_core.mode = "FAB1"
    fab_core._prev_mode = "FAB2"

    assert detect_degradation(fab_core) is True


def test_detect_degradation_mode_upgrade():
    """detect_degradation() returns False on mode upgrade (FAB1 → FAB2)"""
    from src.orbis_fab.stability_hook_exp import detect_degradation

    fab_core = Mock()
    fab_core.degraded = None
    fab_core.mode = "FAB2"
    fab_core._prev_mode = "FAB1"

    assert detect_degradation(fab_core) is False


def test_detect_degradation_default():
    """detect_degradation() returns False when no indicators"""
    from src.orbis_fab.stability_hook_exp import detect_degradation

    fab_core = Mock(spec=[])  # No degraded, mode attributes

    assert detect_degradation(fab_core) is False


def test_maybe_tick_disabled(monkeypatch):
    """maybe_tick() returns None when disabled"""
    monkeypatch.setenv("AURIS_STABILITY_HOOK", "off")

    import importlib
    import src.orbis_fab.stability_hook_exp as hook_mod

    importlib.reload(hook_mod)

    fab_core = Mock()
    tracker = Mock()

    result = hook_mod.maybe_tick(fab_core, tracker)
    assert result is None


def test_maybe_tick_enabled(monkeypatch):
    """maybe_tick() ticks tracker and returns metrics when enabled"""
    monkeypatch.setenv("AURIS_STABILITY_HOOK", "on")

    import importlib
    import src.orbis_fab.stability_hook_exp as hook_mod

    importlib.reload(hook_mod)

    # Setup FABCore
    fab_core = Mock()
    fab_core.current_tick = 0
    fab_core.coherence_score = 0.9
    fab_core.degraded = False

    # Setup tracker
    from src.orbis_fab.stability import StabilityTracker, StabilityConfig

    config = StabilityConfig(min_stable_ticks=10, ema_decay=0.9)
    tracker = StabilityTracker(config=config)

    # Tick
    result = hook_mod.maybe_tick(fab_core, tracker)

    # Verify metrics returned
    assert result is not None
    assert "stability_score_ema" in result
    assert "recommended_mode" in result


def test_maybe_tick_interval(monkeypatch):
    """maybe_tick() respects tick_interval parameter"""
    monkeypatch.setenv("AURIS_STABILITY_HOOK", "on")

    import importlib
    import src.orbis_fab.stability_hook_exp as hook_mod

    importlib.reload(hook_mod)

    fab_core = Mock()
    fab_core.current_tick = 1  # Not divisible by 5
    fab_core.coherence_score = 0.9

    from src.orbis_fab.stability import StabilityTracker, StabilityConfig

    config = StabilityConfig(min_stable_ticks=10)
    tracker = StabilityTracker(config=config)

    # Should skip (tick_interval=5, current_tick=1)
    result = hook_mod.maybe_tick(fab_core, tracker, tick_interval=5)
    assert result is None

    # Should tick (tick_interval=5, current_tick=5)
    fab_core.current_tick = 5
    result = hook_mod.maybe_tick(fab_core, tracker, tick_interval=5)
    assert result is not None


def test_tick_fn_integration(monkeypatch):
    """tick_fn from attach() updates tracker correctly"""
    monkeypatch.setenv("AURIS_STABILITY_HOOK", "on")

    import importlib
    import src.orbis_fab.stability_hook_exp as hook_mod

    importlib.reload(hook_mod)

    # Setup FABCore
    fab_core = Mock()
    fab_core.coherence_score = 0.85
    fab_core.degraded = False

    # Attach
    tracker, tick_fn = hook_mod.attach(fab_core, decay=0.9)

    # Tick 10 times
    for _ in range(10):
        metrics = tick_fn()

    # Verify EMA updated
    assert metrics["stability_score_ema"] > 0.0
    assert metrics["stable_ticks"] == 10


def test_tick_fn_with_degradation(monkeypatch):
    """tick_fn detects degradation events"""
    monkeypatch.setenv("AURIS_STABILITY_HOOK", "on")

    import importlib
    import src.orbis_fab.stability_hook_exp as hook_mod

    importlib.reload(hook_mod)

    fab_core = Mock()
    fab_core.coherence_score = 0.9
    fab_core.degraded = False

    tracker, tick_fn = hook_mod.attach(fab_core, decay=0.9)

    # Tick 5 stable
    for _ in range(5):
        tick_fn()

    # Trigger degradation
    fab_core.degraded = True
    metrics = tick_fn()

    # Verify degradation recorded
    assert metrics["degradation_count"] == 1
    assert metrics["stable_ticks"] == 0  # Reset


def test_fabcore_runtime_integration(monkeypatch):
    """200-tick FABCore integration: verify EMA evolution and mode recommendations"""
    monkeypatch.setenv("AURIS_STABILITY_HOOK", "on")
    monkeypatch.setenv("AURIS_STABILITY", "on")
    monkeypatch.setenv("AURIS_METRICS_EXP", "on")

    # Reload modules to pick up env vars
    import importlib
    import src.orbis_fab.stability_hook_exp as hook_mod
    import src.orbis_fab.core as core_mod

    importlib.reload(hook_mod)
    importlib.reload(core_mod)

    # Import FABCore and StabilityTracker
    from src.orbis_fab.core import FABCore
    from src.orbis_fab.types import Budgets

    # Create FABCore with stability hook enabled
    fab = FABCore(session_id="test-runtime-integration")

    # Verify stability tracker attached
    assert fab._stability is not None

    # Initial metrics
    assert fab._last_stability is None

    # Budgets for init_tick
    budgets: Budgets = {
        "tokens": 2048,
        "nodes": 256,
        "edges": 512,
        "time_ms": 100.0,
    }

    # Phase 1: 100 stable ticks (low stress, no errors)
    for i in range(100):
        fab.init_tick(mode="FAB2", budgets=budgets)
        result = fab.step_stub(stress=0.3, self_presence=0.85, error_rate=0.0)

        # Verify metrics updated
        assert fab._last_stability is not None
        assert "stability_score_ema" in fab._last_stability
        assert "recommended_mode" in fab._last_stability

    # Verify EMA stabilized (should be high after 100 stable ticks)
    ema_stable = fab._last_stability["stability_score_ema"]
    assert ema_stable > 0.6, f"EMA should be high after stable phase: {ema_stable:.3f}"

    # Phase 2: Inject degradation event (high stress)
    fab.step_stub(stress=0.8, self_presence=0.85, error_rate=0.0)

    # Verify degradation recorded
    assert fab._last_stability["degradation_count"] >= 1
    assert fab._last_stability["stable_ticks"] == 0  # Reset after degradation

    # Phase 3: 100 more stable ticks (recovery)
    for i in range(100):
        fab.step_stub(stress=0.3, self_presence=0.85, error_rate=0.0)

    # Verify EMA recovered
    ema_recovered = fab._last_stability["stability_score_ema"]
    assert ema_recovered > 0.5, f"EMA should recover: {ema_recovered:.3f}"

    # Phase 4: Verify mode recommendations align with EMA
    recommended_mode = fab._last_stability["recommended_mode"]
    if ema_recovered >= 0.8:
        assert recommended_mode == "FAB2"
    elif ema_recovered >= 0.5:
        assert recommended_mode == "FAB1"
    else:
        assert recommended_mode == "FAB0"

    # Phase 5: Inject multiple degradations
    for _ in range(3):
        fab.step_stub(stress=0.8, self_presence=0.85, error_rate=0.0)
        fab.step_stub(stress=0.3, self_presence=0.85, error_rate=0.0)  # Recovery tick

    # Verify degradation count increased
    assert fab._last_stability["degradation_count"] >= 4

    # Phase 6: Verify degradation_events_per_hour calculated
    events_per_hour = fab._last_stability["degradation_events_per_hour"]
    assert events_per_hour >= 0.0  # Should be non-negative

