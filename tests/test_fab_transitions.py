"""Test FAB state transitions - Phase A MVP

Tests FAB state machine transitions:
- FAB0 → FAB1: self_presence ≥0.8 ∧ stress <0.7 ∧ ok
- FAB1 → FAB2: stable 3 ticks ∧ stress <0.5 ∧ ok
- FAB2 → FAB1: stress >0.7 ∨ error_rate >0.05 (degradation)
- FAB1 stability reset on stress spike

Invariants:
- Mode transitions respect thresholds
- Stability counter resets on degradation
- Budgets cap window sizes correctly
"""

from orbis_fab import FABCore, Budgets, ZSliceLite


def make_z_slice(num_nodes: int = 200) -> ZSliceLite:
    """Helper: Create test Z-slice with scored nodes"""
    return {
        "nodes": [{"id": f"n{i}", "score": 0.9 - i * 0.001} for i in range(num_nodes)],
        "edges": [],
        "quotas": {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30},
        "seed": "test-run",
        "zv": "0.1"
    }


def test_fab0_to_fab1_on_self_presence():
    """FAB0 → FAB1 when self_presence ≥0.8 and stress <0.7"""
    fab = FABCore()
    budgets: Budgets = {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30}
    
    fab.init_tick(mode="FAB0", budgets=budgets)
    fab.fill(make_z_slice())
    
    ctx = fab.mix()
    assert ctx["stream_size"] > 0
    
    # Tick 1: High self_presence, low stress → FAB1
    result = fab.step_stub(stress=0.3, self_presence=0.85, error_rate=0.0)
    assert result["mode"] == "FAB1"
    assert result["stable_ticks"] == 0


def test_fab1_to_fab2_after_stable_ticks():
    """FAB1 → FAB2 after 3 stable ticks with stress <0.5"""
    fab = FABCore()
    budgets: Budgets = {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30}
    
    fab.init_tick(mode="FAB1", budgets=budgets)
    fab.st.mode = "FAB1"  # Start in FAB1
    
    # Ticks 1-2: Stable but not enough
    for i in range(2):
        result = fab.step_stub(stress=0.3, self_presence=0.9, error_rate=0.0)
        assert result["mode"] == "FAB1", f"Should stay FAB1 at tick {i+1}"
        assert result["stable_ticks"] == i + 1
    
    # Tick 3: Stable for 3rd time → FAB2
    result = fab.step_stub(stress=0.3, self_presence=0.9, error_rate=0.0)
    assert result["mode"] == "FAB2"
    assert result["stable_ticks"] == 3


def test_fab2_degrades_to_fab1_on_stress():
    """FAB2 → FAB1 when stress >0.7"""
    fab = FABCore()
    budgets: Budgets = {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30}
    
    fab.init_tick(mode="FAB2", budgets=budgets)
    fab.st.mode = "FAB2"
    fab.st.stable_ticks = 3
    
    # Stress spike → degrade to FAB1
    result = fab.step_stub(stress=0.8, self_presence=0.9, error_rate=0.0)
    assert result["mode"] == "FAB1"
    assert result["stable_ticks"] == 0  # Reset counter


def test_fab2_degrades_to_fab1_on_error_rate():
    """FAB2 → FAB1 when error_rate >0.05"""
    fab = FABCore()
    fab.st.mode = "FAB2"
    fab.st.stable_ticks = 3
    
    # Error rate spike → degrade to FAB1
    result = fab.step_stub(stress=0.3, self_presence=0.9, error_rate=0.1)
    assert result["mode"] == "FAB1"
    assert result["stable_ticks"] == 0


def test_fab1_resets_stability_on_stress():
    """FAB1 resets stable_ticks on stress spike"""
    fab = FABCore()
    fab.st.mode = "FAB1"
    fab.st.stable_ticks = 2
    
    # Stress spike → reset stability, stay FAB1
    result = fab.step_stub(stress=0.75, self_presence=0.9, error_rate=0.0)
    assert result["mode"] == "FAB1"
    assert result["stable_ticks"] == 0


def test_fab0_to_fab1_to_fab2_happy_path():
    """Full happy path: FAB0 → FAB1 → FAB2"""
    fab = FABCore()
    budgets: Budgets = {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30}
    
    # Start in FAB0
    fab.init_tick(mode="FAB0", budgets=budgets)
    fab.fill(make_z_slice())
    assert fab.mix()["stream_size"] > 0
    
    # Tick 1: FAB0 → FAB1
    result = fab.step_stub(stress=0.3, self_presence=0.85, error_rate=0.0)
    assert result["mode"] == "FAB1"
    
    # Ticks 2-4: FAB1 → FAB2 (3 stable ticks)
    for i in range(2):
        result = fab.step_stub(stress=0.3, self_presence=0.9, error_rate=0.0)
        assert result["mode"] == "FAB1", f"Tick {i+2}: Still FAB1"
    
    result = fab.step_stub(stress=0.3, self_presence=0.9, error_rate=0.0)
    assert result["mode"] == "FAB2", "Tick 4: Transition to FAB2"


def test_fab0_stays_fab0_without_self_presence():
    """FAB0 stays FAB0 when self_presence <0.8"""
    fab = FABCore()
    budgets: Budgets = {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30}
    
    fab.init_tick(mode="FAB0", budgets=budgets)
    
    # Low self_presence → stay FAB0
    result = fab.step_stub(stress=0.3, self_presence=0.5, error_rate=0.0)
    assert result["mode"] == "FAB0"


def test_fab1_requires_very_low_stress_for_fab2():
    """FAB1 → FAB2 requires stress <0.5 (not just <0.7)"""
    fab = FABCore()
    fab.st.mode = "FAB1"
    
    # Stress at 0.6 (ok for FAB1, but not for FAB2)
    result = None
    for _ in range(5):
        result = fab.step_stub(stress=0.6, self_presence=0.9, error_rate=0.0)
    
    # Should stay FAB1 (stress not low enough for FAB2)
    assert result is not None
    assert result["mode"] == "FAB1"
    assert result["stable_ticks"] >= 3  # Accumulates ticks but doesn't transition
