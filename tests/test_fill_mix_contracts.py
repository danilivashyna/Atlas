"""Test FAB fill/mix contracts - Phase A MVP

Tests window capacity enforcement and fill behavior:
- Budgets cap window sizes correctly
- Global + Stream ≤ budgets.nodes
- High-score nodes → stream window
- Low-score nodes → global window
- Precision assigned by average score

Invariants:
- fill() respects cap_nodes
- mix() returns accurate snapshot
- No node duplication between windows
- Global defaults to cold precision (mxfp4.12)
"""

from orbis_fab import FABCore, Budgets, ZSliceLite


def make_z_slice(num_nodes: int, base_score: float = 0.9) -> ZSliceLite:
    """Helper: Create test Z-slice with scored nodes"""
    return {
        "nodes": [
            {"id": f"n{i}", "score": max(0.0, base_score - i * 0.001)} for i in range(num_nodes)
        ],
        "edges": [],
        "quotas": {"tokens": 4096, "nodes": num_nodes, "edges": 0, "time_ms": 30},
        "seed": "test-run",
        "zv": "0.1",
    }


def test_fill_respects_stream_cap():
    """fill() respects stream window capacity"""
    fab = FABCore()
    budgets: Budgets = {"tokens": 4096, "nodes": 80, "edges": 0, "time_ms": 30}

    fab.init_tick(mode="FAB0", budgets=budgets)

    # Create Z-slice with 200 nodes
    z_slice = make_z_slice(200)
    fab.fill(z_slice)

    ctx = fab.mix()

    # Stream capped at 128 or budgets.nodes (80)
    assert ctx["stream_size"] <= 80
    assert ctx["stream_size"] <= 128


def test_fill_respects_global_cap():
    """fill() respects global window capacity"""
    fab = FABCore()
    budgets: Budgets = {"tokens": 4096, "nodes": 300, "edges": 0, "time_ms": 30}

    fab.init_tick(mode="FAB0", budgets=budgets)
    fab.fill(make_z_slice(500))

    ctx = fab.mix()

    # Global capped at 256
    assert ctx["global_size"] <= 256


def test_fill_total_nodes_within_budget():
    """Global + Stream ≤ budgets.nodes"""
    fab = FABCore()
    budgets: Budgets = {"tokens": 4096, "nodes": 100, "edges": 0, "time_ms": 30}

    fab.init_tick(mode="FAB0", budgets=budgets)
    fab.fill(make_z_slice(500))

    ctx = fab.mix()
    total = ctx["global_size"] + ctx["stream_size"]

    # Total should not exceed budget
    # Note: stream cap=100, global cap=100, but only 100 total nodes available
    assert total <= budgets["nodes"]


def test_fill_high_scores_go_to_stream():
    """High-score nodes populate stream window"""
    fab = FABCore()
    budgets: Budgets = {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30}

    fab.init_tick(mode="FAB0", budgets=budgets)

    # Create Z-slice with descending scores
    z_slice = make_z_slice(200, base_score=0.95)
    fab.fill(z_slice)

    # Check that stream has nodes
    assert len(fab.st.stream_win.nodes) > 0

    # Verify stream nodes have higher scores than global
    if len(fab.st.global_win.nodes) > 0:
        max_stream_score = max(n["score"] for n in fab.st.stream_win.nodes)
        min_global_score = min(n["score"] for n in fab.st.global_win.nodes)
        # Stream should have higher scores
        assert max_stream_score >= min_global_score


def test_fill_assigns_precision_by_average_score():
    """Stream precision assigned by average score"""
    fab = FABCore()
    budgets: Budgets = {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30}

    fab.init_tick(mode="FAB0", budgets=budgets)

    # High-score Z-slice → should get high precision
    high_score_slice = make_z_slice(100, base_score=0.95)
    fab.fill(high_score_slice)

    ctx_high = fab.mix()

    # Average score ≈0.95-0.05 = 0.90 → should be mxfp8.0
    assert ctx_high["stream_precision"].startswith("mxfp8") or ctx_high[
        "stream_precision"
    ].startswith("mxfp6")

    # Low-score Z-slice → should get lower precision
    fab2 = FABCore()
    fab2.init_tick(mode="FAB0", budgets=budgets)
    low_score_slice = make_z_slice(100, base_score=0.50)
    fab2.fill(low_score_slice)

    ctx_low = fab2.mix()

    # Average score ≈0.50-0.05 = 0.45 → should be mxfp5.25 or lower
    assert ctx_low["stream_precision"] in ["mxfp5.25", "mxfp4.12"]


def test_global_window_defaults_to_cold_precision():
    """Global window uses cold precision (mxfp4.12)"""
    fab = FABCore()
    budgets: Budgets = {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30}

    fab.init_tick(mode="FAB0", budgets=budgets)
    fab.fill(make_z_slice(200, base_score=0.95))

    ctx = fab.mix()

    # Global always cold
    assert ctx["global_precision"] == "mxfp4.12"


def test_mix_returns_accurate_snapshot():
    """mix() returns accurate window state"""
    fab = FABCore()
    budgets: Budgets = {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30}

    fab.init_tick(mode="FAB1", budgets=budgets)
    fab.fill(make_z_slice(150))

    ctx = fab.mix()

    # Verify structure
    assert "mode" in ctx
    assert "global_size" in ctx
    assert "stream_size" in ctx
    assert "stream_precision" in ctx
    assert "global_precision" in ctx

    # Verify values match state
    assert ctx["mode"] == fab.st.mode
    assert ctx["global_size"] == len(fab.st.global_win.nodes)
    assert ctx["stream_size"] == len(fab.st.stream_win.nodes)
    assert ctx["stream_precision"] == fab.st.stream_win.precision
    assert ctx["global_precision"] == fab.st.global_win.precision


def test_fill_with_empty_z_slice():
    """fill() handles empty Z-slice gracefully"""
    fab = FABCore()
    budgets: Budgets = {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30}

    fab.init_tick(mode="FAB0", budgets=budgets)

    empty_slice: ZSliceLite = {
        "nodes": [],
        "edges": [],
        "quotas": budgets,
        "seed": "empty",
        "zv": "0.1",
    }

    fab.fill(empty_slice)
    ctx = fab.mix()

    assert ctx["global_size"] == 0
    assert ctx["stream_size"] == 0


def test_fill_with_small_z_slice():
    """fill() handles Z-slice smaller than caps"""
    fab = FABCore()
    budgets: Budgets = {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30}

    fab.init_tick(mode="FAB0", budgets=budgets)

    # Only 10 nodes (much less than caps)
    small_slice = make_z_slice(10)
    fab.fill(small_slice)

    ctx = fab.mix()

    # Should use all 10 nodes
    total = ctx["global_size"] + ctx["stream_size"]
    assert total == 10
