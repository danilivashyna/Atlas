"""Integration tests for Z-Space diagnostics (Phase 2 PR#2)

Tests for Z-Space selector diagnostics metrics:
- z_selector_used: bool flag for selector='z-space'
- z_diversity_gain: variance of stream scores (diversity metric)
- z_latency_ms: selection latency in milliseconds

Validates:
- Metrics exported correctly in ctx['diagnostics']['derived']
- selector='fab': z_selector_used=False, metrics=0.0
- selector='z-space': z_selector_used=True, metrics tracked
- Diversity gain range validation (0.0 for empty/single, >0.0 for diverse)
"""

from orbis_fab.core import FABCore
from orbis_fab.types import ZSliceLite


def test_diagnostics_fab_selector_metrics():
    """
    Test: selector='fab' produces z_selector_used=False, metrics=0.0
    
    Validates:
    - z_selector_used == False (FAB selector active)
    - z_diversity_gain == 0.0 (not applicable for FAB)
    - z_latency_ms == 0.0 (no Z-Space overhead)
    """
    fab = FABCore(selector="fab", session_id="test-diag-fab")
    
    z_slice: ZSliceLite = {
        "nodes": [
            {"id": "n1", "score": 0.9},
            {"id": "n2", "score": 0.7},
            {"id": "n3", "score": 0.5},
        ],
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": 64, "edges": 0, "time_ms": 30},
        "seed": "fab-diag-test",
        "zv": "v0.1.0"
    }
    
    fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 16, "edges": 0, "time_ms": 30})
    fab.fill(z_slice)
    ctx = fab.mix()
    
    # Verify diagnostics structure
    assert "diagnostics" in ctx
    assert "derived" in ctx["diagnostics"]
    
    derived = ctx["diagnostics"]["derived"]
    
    # Verify Z-Space metrics for FAB selector
    assert "z_selector_used" in derived
    assert "z_diversity_gain" in derived
    assert "z_latency_ms" in derived
    
    assert derived["z_selector_used"] is False  # FAB selector active
    assert derived["z_diversity_gain"] == 0.0  # Not applicable
    assert derived["z_latency_ms"] == 0.0  # No Z-Space overhead


def test_diagnostics_z_space_selector_active():
    """
    Test: selector='z-space' produces z_selector_used=True, metrics tracked
    
    Validates:
    - z_selector_used == True (Z-Space selector active)
    - z_latency_ms >= 0.0 (selection has some latency)
    - z_diversity_gain >= 0.0 (variance metric)
    """
    fab = FABCore(selector="z-space", session_id="test-diag-z-space")
    
    z_slice: ZSliceLite = {
        "nodes": [
            {"id": f"n{i}", "score": 1.0 - i * 0.1}
            for i in range(10)
        ],
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": 64, "edges": 0, "time_ms": 30},
        "seed": "z-space-diag-test",
        "zv": "v0.1.0"
    }
    
    fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 8, "edges": 0, "time_ms": 30})
    fab.fill(z_slice)
    ctx = fab.mix()
    
    derived = ctx["diagnostics"]["derived"]
    
    # Verify Z-Space selector active
    assert derived["z_selector_used"] is True
    
    # Verify latency tracked (should be positive, even if very small)
    assert derived["z_latency_ms"] >= 0.0
    
    # Verify diversity gain tracked (variance of stream scores)
    assert derived["z_diversity_gain"] >= 0.0


def test_diagnostics_diversity_gain_empty_stream():
    """
    Test: Empty stream → z_diversity_gain == 0.0
    
    Edge case: No nodes selected
    """
    fab = FABCore(selector="z-space", session_id="test-diag-empty")
    
    z_empty: ZSliceLite = {
        "nodes": [],
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": 64, "edges": 0, "time_ms": 30},
        "seed": "empty",
        "zv": "v0.1.0"
    }
    
    fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 16, "edges": 0, "time_ms": 30})
    fab.fill(z_empty)
    ctx = fab.mix()
    
    derived = ctx["diagnostics"]["derived"]
    
    # Empty stream → no diversity
    assert derived["z_diversity_gain"] == 0.0
    assert derived["z_latency_ms"] >= 0.0  # Still tracked (even if minimal)


def test_diagnostics_diversity_gain_single_node():
    """
    Test: Single node in stream → z_diversity_gain == 0.0
    
    Edge case: No variance with single element
    """
    fab = FABCore(selector="z-space", session_id="test-diag-single")
    
    z_single: ZSliceLite = {
        "nodes": [{"id": "n1", "score": 0.85}],
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": 64, "edges": 0, "time_ms": 30},
        "seed": "single",
        "zv": "v0.1.0"
    }
    
    fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 16, "edges": 0, "time_ms": 30})
    fab.fill(z_single)
    ctx = fab.mix()
    
    derived = ctx["diagnostics"]["derived"]
    
    # Single node → no variance
    assert derived["z_diversity_gain"] == 0.0
    assert derived["z_latency_ms"] >= 0.0


def test_diagnostics_diversity_gain_diverse_stream():
    """
    Test: Diverse scores → z_diversity_gain > 0.0
    
    Validates variance calculation for mixed scores
    """
    fab = FABCore(selector="z-space", session_id="test-diag-diverse")
    
    z_diverse: ZSliceLite = {
        "nodes": [
            {"id": "n1", "score": 0.95},  # High
            {"id": "n2", "score": 0.50},  # Medium
            {"id": "n3", "score": 0.20},  # Low
            {"id": "n4", "score": 0.85},  # High-ish
        ],
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": 64, "edges": 0, "time_ms": 30},
        "seed": "diverse",
        "zv": "v0.1.0"
    }
    
    fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 4, "edges": 0, "time_ms": 30})
    fab.fill(z_diverse)
    ctx = fab.mix()
    
    derived = ctx["diagnostics"]["derived"]
    
    # Diverse scores → positive variance
    assert derived["z_diversity_gain"] > 0.0
    assert derived["z_latency_ms"] >= 0.0
    
    # Verify all 4 nodes selected (budget allows)
    assert ctx["stream_size"] == 4


def test_diagnostics_latency_range():
    """
    Test: z_latency_ms is reasonable (< 10ms for small slices)
    
    SLO validation: Selection should be fast (<5ms target for Shadow API)
    """
    fab = FABCore(selector="z-space", session_id="test-diag-latency")
    
    z_slice: ZSliceLite = {
        "nodes": [{"id": f"n{i}", "score": 1.0 - i * 0.01} for i in range(50)],
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": 128, "edges": 0, "time_ms": 30},
        "seed": "latency-test",
        "zv": "v0.1.0"
    }
    
    fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 32, "edges": 0, "time_ms": 30})
    fab.fill(z_slice)
    ctx = fab.mix()
    
    derived = ctx["diagnostics"]["derived"]
    
    # Latency should be measurable but small
    assert derived["z_latency_ms"] >= 0.0
    assert derived["z_latency_ms"] < 10.0  # Should be very fast for 50 nodes
    
    # Diversity gain should be positive (mixed scores)
    assert derived["z_diversity_gain"] > 0.0


def test_diagnostics_persistence_across_ticks():
    """
    Test: Diagnostics persist across multiple ticks
    
    Validates that metrics are updated on each fill()
    """
    fab = FABCore(selector="z-space", session_id="test-diag-persist")
    
    z_slice: ZSliceLite = {
        "nodes": [
            {"id": "n1", "score": 0.9},
            {"id": "n2", "score": 0.8},
            {"id": "n3", "score": 0.7},
        ],
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": 64, "edges": 0, "time_ms": 30},
        "seed": "persist-test",
        "zv": "v0.1.0"
    }
    
    # Tick 1
    fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 3, "edges": 0, "time_ms": 30})
    fab.fill(z_slice)
    ctx1 = fab.mix()
    
    derived1 = ctx1["diagnostics"]["derived"]
    assert derived1["z_selector_used"] is True
    assert derived1["z_latency_ms"] >= 0.0
    latency1 = derived1["z_latency_ms"]
    
    # Tick 2 (advance time)
    fab.step_stub(stress=0.3, self_presence=0.9, error_rate=0.01)
    fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 3, "edges": 0, "time_ms": 30})
    fab.fill(z_slice)
    ctx2 = fab.mix()
    
    derived2 = ctx2["diagnostics"]["derived"]
    assert derived2["z_selector_used"] is True
    assert derived2["z_latency_ms"] >= 0.0
    
    # Latency might vary slightly (timing precision)
    # Both should be small and positive
    assert latency1 >= 0.0
    assert derived2["z_latency_ms"] >= 0.0


def test_diagnostics_fab_to_z_space_switch():
    """
    Test: Switching selectors updates metrics correctly
    
    Validates selector='fab' → selector='z-space' transition
    (requires recreating FABCore, selector is init-time parameter)
    """
    # Start with FAB selector
    fab_fab = FABCore(selector="fab", session_id="test-switch-1")
    
    z_slice: ZSliceLite = {
        "nodes": [
            {"id": "n1", "score": 0.9},
            {"id": "n2", "score": 0.7},
        ],
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": 64, "edges": 0, "time_ms": 30},
        "seed": "switch-test",
        "zv": "v0.1.0"
    }
    
    fab_fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 2, "edges": 0, "time_ms": 30})
    fab_fab.fill(z_slice)
    ctx_fab = fab_fab.mix()
    
    # Verify FAB metrics
    assert ctx_fab["diagnostics"]["derived"]["z_selector_used"] is False
    assert ctx_fab["diagnostics"]["derived"]["z_latency_ms"] == 0.0
    
    # Switch to Z-Space selector (new instance)
    fab_z = FABCore(selector="z-space", session_id="test-switch-2")
    
    fab_z.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 2, "edges": 0, "time_ms": 30})
    fab_z.fill(z_slice)
    ctx_z = fab_z.mix()
    
    # Verify Z-Space metrics
    assert ctx_z["diagnostics"]["derived"]["z_selector_used"] is True
    assert ctx_z["diagnostics"]["derived"]["z_latency_ms"] >= 0.0
    assert ctx_z["diagnostics"]["derived"]["z_diversity_gain"] >= 0.0
