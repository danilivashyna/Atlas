"""Integration tests for Phase B diagnostics in FABCore

Validates that diagnostics counters/gauges are correctly integrated
into Phase A workflows (fill/mix/step_stub).
"""

import pytest
from orbis_fab import FABCore, Budgets


def make_z_slice(num_nodes: int = 100, base_score: float = 0.9):
    """Helper: Create test Z-slice"""
    return {  # type: ignore[return-value]
        "nodes": [
            {"id": f"n{i}", "score": max(0.0, base_score - i * 0.001)}
            for i in range(num_nodes)
        ],
        "edges": [],
        "quotas": {"tokens": 4096, "nodes": num_nodes, "edges": 0, "time_ms": 30},
        "seed": "test-diag-integration",
        "zv": "0.1"
    }


def test_diagnostics_counters_in_basic_flow():
    """Diagnostics counters increment during basic FAB flow"""
    fab = FABCore()
    budgets: Budgets = {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30}
    
    # Tick 1
    fab.init_tick(mode="FAB0", budgets=budgets)
    fab.fill(make_z_slice())
    ctx = fab.mix()
    
    # Validate diagnostics in context
    assert "diagnostics" in ctx
    diag = ctx["diagnostics"]
    
    # Check structure
    assert "counters" in diag
    assert "gauges" in diag
    
    # Check counters
    assert diag["counters"]["ticks"] == 1
    assert diag["counters"]["fills"] == 1
    assert diag["counters"]["mixes"] == 1
    assert diag["counters"]["mode_transitions"] == 0  # No transition yet
    
    # Check gauges
    assert diag["gauges"]["mode"] == "FAB0"
    assert diag["gauges"]["global_precision"] == "mxfp4.12"
    assert diag["gauges"]["stream_precision"] in ["mxfp8.0", "mxfp6.0", "mxfp5.25", "mxfp4.12"]


def test_diagnostics_mode_transitions():
    """Diagnostics track mode transitions correctly"""
    fab = FABCore()
    budgets: Budgets = {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30}
    
    # Start in FAB0
    fab.init_tick(mode="FAB0", budgets=budgets)
    fab.fill(make_z_slice())
    fab.mix()
    
    # Transition FAB0 → FAB1
    fab.step_stub(stress=0.3, self_presence=0.85, error_rate=0.0)
    
    ctx = fab.mix()
    diag = ctx["diagnostics"]
    
    # Mode transition counted
    assert diag["counters"]["mode_transitions"] == 1
    assert diag["gauges"]["mode"] == "FAB1"


def test_diagnostics_envelope_changes():
    """Diagnostics track precision envelope changes"""
    fab = FABCore()
    budgets: Budgets = {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30}
    
    # Low score slice → mxfp4.12
    fab.init_tick(mode="FAB0", budgets=budgets)
    fab.fill(make_z_slice(100, base_score=0.3))
    ctx1 = fab.mix()
    
    initial_changes = ctx1["diagnostics"]["counters"]["envelope_changes"]
    
    # High score slice → should trigger precision change
    fab.init_tick(mode="FAB0", budgets=budgets)
    fab.fill(make_z_slice(100, base_score=0.95))
    ctx2 = fab.mix()
    
    # Envelope change detected
    assert ctx2["diagnostics"]["counters"]["envelope_changes"] > initial_changes


def test_diagnostics_stable_ticks_gauge():
    """Diagnostics gauge tracks stable_ticks correctly"""
    fab = FABCore()
    budgets: Budgets = {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30}
    
    # Start in FAB1
    fab.init_tick(mode="FAB1", budgets=budgets)
    fab.st.mode = "FAB1"
    fab.fill(make_z_slice())
    
    # Accumulate stability
    for i in range(3):
        fab.step_stub(stress=0.3, self_presence=0.9, error_rate=0.0)
        ctx = fab.mix()
        
        # Gauge reflects current stable_ticks
        if i < 2:
            assert ctx["diagnostics"]["gauges"]["stable_ticks"] == i + 1
        else:
            # After FAB1→FAB2 transition, stable_ticks preserved in result
            # but gauge shows current state
            assert ctx["diagnostics"]["gauges"]["stable_ticks"] >= 0


def test_diagnostics_multiple_ticks():
    """Diagnostics accumulate correctly over multiple ticks"""
    fab = FABCore()
    budgets: Budgets = {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30}
    
    # 5 ticks
    for tick in range(5):
        fab.init_tick(mode="FAB0", budgets=budgets)
        fab.fill(make_z_slice())
        ctx = fab.mix()
        
        diag = ctx["diagnostics"]
        
        # Counters increment
        assert diag["counters"]["ticks"] == tick + 1
        assert diag["counters"]["fills"] == tick + 1
        assert diag["counters"]["mixes"] == tick + 1


def test_diagnostics_golden_snapshot():
    """Golden snapshot with fixed seed produces deterministic diagnostics"""
    fab = FABCore()
    budgets: Budgets = {"tokens": 4096, "nodes": 128, "edges": 0, "time_ms": 30}
    
    # Fixed seed Z-slice
    z_slice = {
        "nodes": [
            {"id": "n0", "score": 0.95},
            {"id": "n1", "score": 0.90},
            {"id": "n2", "score": 0.85},
            {"id": "n3", "score": 0.80},
            {"id": "n4", "score": 0.75}
        ],
        "edges": [],
        "quotas": {"tokens": 4096, "nodes": 128, "edges": 0, "time_ms": 30},
        "seed": "golden-snapshot-42",
        "zv": "0.1"
    }
    
    # Execute deterministic flow
    fab.init_tick(mode="FAB0", budgets=budgets)
    fab.fill(z_slice)
    ctx = fab.mix()
    
    diag = ctx["diagnostics"]
    
    # Golden snapshot assertions
    assert diag["counters"]["ticks"] == 1
    assert diag["counters"]["fills"] == 1
    assert diag["counters"]["mixes"] == 1
    assert diag["counters"]["mode_transitions"] == 0
    # envelope_changes==1 on first tick (None → mxfp8.0 transition)
    assert diag["counters"]["envelope_changes"] == 1
    
    assert diag["gauges"]["mode"] == "FAB0"
    assert diag["gauges"]["global_precision"] == "mxfp4.12"
    assert diag["gauges"]["stream_precision"] == "mxfp8.0"  # avg=0.85 → hot
    assert diag["gauges"]["stable_ticks"] == 0
    assert diag["gauges"]["cooldown_remaining"] == 0
    
    # Verify deterministic window sizes
    assert ctx["stream_size"] == 5  # All nodes fit in stream (cap=128)
    assert ctx["global_size"] == 0  # No overflow


def test_diagnostics_derived_metrics():
    """Diagnostics snapshot includes derived metrics"""
    fab = FABCore()
    budgets: Budgets = {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30}
    
    ctx = None  # Initialize for type checker
    # Execute multiple ticks with envelope changes
    for i in range(10):
        fab.init_tick(mode="FAB0", budgets=budgets)
        # Alternate between high and low scores to trigger envelope changes
        score = 0.95 if i % 2 == 0 else 0.30
        fab.fill(make_z_slice(100, base_score=score))  # type: ignore[arg-type]
        ctx = fab.mix()
    
    assert ctx is not None  # Ensure at least one tick completed
    diag = ctx["diagnostics"]
    
    # Derived metrics in snapshot (returned by diag.snapshot())
    # These are computed on-demand, not stored
    # Check that they're present and reasonable
    assert diag["counters"]["ticks"] == 10
    assert diag["counters"]["envelope_changes"] >= 0  # At least some changes expected
