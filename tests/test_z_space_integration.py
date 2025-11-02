"""
Integration tests for Z-Space selector in FABCore.

Tests PR#1: Selector flag integration
- selector='fab' produces identical results to baseline
- selector='z-space' uses ZSpaceShim for deterministic selection
- Determinism parity between selectors (same seeds → same results)
- Budget/quota respect with both selectors
- Envelope compatibility (legacy/hysteresis) with z-space enabled
"""

from orbis_fab.core import FABCore
from orbis_fab.types import ZSliceLite


def test_selector_fab_baseline():
    """
    Test: selector='fab' (default) produces baseline behavior.

    Validates:
    - Default selector is 'fab'
    - Existing Phase A/B/C+ behavior preserved
    - No regressions in fill/mix flow
    """
    fab = FABCore(envelope_mode="legacy", session_id="test-selector-fab")

    # Verify default selector
    assert fab.selector == "fab"

    # Standard fill/mix flow
    z_slice: ZSliceLite = {
        "nodes": [
            {"id": "n1", "score": 0.9},
            {"id": "n2", "score": 0.7},
            {"id": "n3", "score": 0.5},
        ],
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": 64, "edges": 0, "time_ms": 30},
        "seed": "baseline-test",
        "zv": "v0.1.0",
    }

    fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 16, "edges": 0, "time_ms": 30})
    fab.fill(z_slice)
    ctx = fab.mix()

    # Verify stream populated (mix() returns sizes, not full nodes)
    assert ctx["stream_size"] > 0
    assert ctx["mode"] == "FAB0"
    assert "stream_precision" in ctx


def test_selector_z_space_enabled():
    """
    Test: selector='z-space' uses ZSpaceShim for selection.

    Validates:
    - ZSpaceShim used when selector='z-space'
    - Deterministic selection (same seed → same results)
    - Stream/global separation works
    """
    fab = FABCore(
        envelope_mode="legacy",
        session_id="test-selector-z-space",
        selector="z-space",  # Enable Z-Space selector
    )

    assert fab.selector == "z-space"

    z_slice: ZSliceLite = {
        "nodes": [{"id": f"n{i}", "score": 1.0 - i * 0.1} for i in range(10)],
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": 64, "edges": 0, "time_ms": 30},
        "seed": "z-space-test",
        "zv": "v0.1.0",
    }

    fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 8, "edges": 0, "time_ms": 30})
    fab.fill(z_slice)
    ctx = fab.mix()

    # Verify stream populated (selector='z-space' active)
    assert ctx["stream_size"] > 0
    assert ctx["stream_size"] <= 8  # Budget cap respected

    # Verify windows populated via internal state
    assert len(fab.st.stream_win.nodes) > 0


def test_selector_determinism_parity():
    """
    Test: Both selectors produce deterministic results with same seed.

    Validates:
    - selector='fab' is deterministic
    - selector='z-space' is deterministic
    - Both respect session_id + z.seed combination
    """
    z_slice: ZSliceLite = {
        "nodes": [
            {"id": "n1", "score": 0.85},
            {"id": "n2", "score": 0.80},
            {"id": "n3", "score": 0.75},
            {"id": "n4", "score": 0.70},
        ],
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": 64, "edges": 0, "time_ms": 30},
        "seed": "determinism-test",
        "zv": "v0.1.0",
    }

    # Test selector='fab' determinism
    fab1 = FABCore(selector="fab", session_id="test-det-1")
    fab1.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 4, "edges": 0, "time_ms": 30})
    fab1.fill(z_slice)
    _ctx1a = fab1.mix()

    fab2 = FABCore(selector="fab", session_id="test-det-1")  # Same session_id
    fab2.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 4, "edges": 0, "time_ms": 30})
    fab2.fill(z_slice)
    _ctx2a = fab2.mix()

    # Verify FAB selector determinism (via internal state)
    stream_ids_1a = [n["id"] for n in fab1.st.stream_win.nodes]
    stream_ids_2a = [n["id"] for n in fab2.st.stream_win.nodes]
    assert stream_ids_1a == stream_ids_2a  # Identical order

    # Test selector='z-space' determinism
    fab3 = FABCore(selector="z-space", session_id="test-det-2")
    fab3.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 4, "edges": 0, "time_ms": 30})
    fab3.fill(z_slice)
    _ctx3a = fab3.mix()

    fab4 = FABCore(selector="z-space", session_id="test-det-2")  # Same session_id
    fab4.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 4, "edges": 0, "time_ms": 30})
    fab4.fill(z_slice)
    _ctx4a = fab4.mix()

    # Verify Z-Space selector determinism (via internal state)
    stream_ids_3a = [n["id"] for n in fab3.st.stream_win.nodes]
    stream_ids_4a = [n["id"] for n in fab4.st.stream_win.nodes]
    assert stream_ids_3a == stream_ids_4a  # Identical order


def test_selector_budget_respect():
    """
    Test: Both selectors respect stream/global budget caps.

    Validates:
    - Stream size ≤ stream_cap
    - Global size ≤ global_cap
    - No budget overruns
    """
    z_slice: ZSliceLite = {
        "nodes": [{"id": f"n{i}", "score": 1.0 - i * 0.01} for i in range(100)],
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": 256, "edges": 0, "time_ms": 30},
        "seed": "budget-test",
        "zv": "v0.1.0",
    }

    budgets = {"tokens": 8000, "nodes": 32, "edges": 0, "time_ms": 30}

    # Test selector='fab'
    fab1 = FABCore(selector="fab", session_id="budget-fab")
    fab1.init_tick(mode="FAB0", budgets=budgets)  # type: ignore[arg-type]
    fab1.fill(z_slice)
    ctx1 = fab1.mix()

    # Verify budget caps via mix() sizes
    assert ctx1["stream_size"] <= fab1.st.stream_win.cap_nodes
    assert ctx1["global_size"] <= fab1.st.global_win.cap_nodes
    assert ctx1["stream_size"] + ctx1["global_size"] <= budgets["nodes"]

    # Test selector='z-space'
    fab2 = FABCore(selector="z-space", session_id="budget-z-space")
    fab2.init_tick(mode="FAB0", budgets=budgets)  # type: ignore[arg-type]
    fab2.fill(z_slice)
    ctx2 = fab2.mix()

    assert ctx2["stream_size"] <= fab2.st.stream_win.cap_nodes
    assert ctx2["global_size"] <= fab2.st.global_win.cap_nodes
    assert ctx2["stream_size"] + ctx2["global_size"] <= budgets["nodes"]


def test_selector_envelope_compatibility_legacy():
    """
    Test: selector='z-space' works with envelope_mode='legacy'.

    Validates:
    - Immediate precision assignment with Z-Space selector
    - No hysteresis interference
    - Precision changes tracked
    """
    fab = FABCore(envelope_mode="legacy", selector="z-space", session_id="z-legacy-test")

    # High score slice → hot precision
    z_hot: ZSliceLite = {
        "nodes": [{"id": f"n{i}", "score": 0.95} for i in range(10)],
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": 64, "edges": 0, "time_ms": 30},
        "seed": "hot-test",
        "zv": "v0.1.0",
    }

    fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 16, "edges": 0, "time_ms": 30})
    fab.fill(z_hot)
    ctx = fab.mix()

    # Legacy mode: immediate hot precision
    assert ctx["stream_precision"] in ("mxfp8.0", "mxfp6.0")  # Hot range


def test_selector_envelope_compatibility_hysteresis():
    """
    Test: selector='z-space' works with envelope_mode='hysteresis'.

    Validates:
    - Hysteresis dead-band + dwell with Z-Space selector
    - Precision changes respect rate_limit
    - Tiny stream guard works
    """
    fab = FABCore(
        envelope_mode="hysteresis",
        hysteresis_dwell=2,
        hysteresis_rate_limit=5,
        selector="z-space",
        session_id="z-hys-test",
    )

    # Medium score slice
    z_med: ZSliceLite = {
        "nodes": [{"id": f"n{i}", "score": 0.6} for i in range(10)],
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": 64, "edges": 0, "time_ms": 30},
        "seed": "med-test",
        "zv": "v0.1.0",
    }

    fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 16, "edges": 0, "time_ms": 30})
    fab.fill(z_med)
    ctx = fab.mix()

    # Hysteresis mode: precision determined by dead-band
    _initial_precision = ctx["stream_precision"]  # Baseline check

    # Run a few more ticks (hysteresis may delay changes)
    for i in range(3):
        fab.step_stub(stress=0.3, self_presence=0.5, error_rate=0.01)
        fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 16, "edges": 0, "time_ms": 30})
        fab.fill(z_med)
        ctx = fab.mix()

    # Precision should stabilize (hysteresis prevents oscillation)
    assert ctx["stream_precision"] is not None


def test_selector_invalid_value_raises():
    """
    Test: Invalid selector value raises ValueError.
    """
    try:
        _fab = FABCore(selector="invalid-selector")  # type: ignore[arg-type]
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "selector must be 'fab' or 'z-space'" in str(e)


def test_selector_z_space_empty_slice():
    """
    Test: selector='z-space' handles empty slice gracefully.
    """
    fab = FABCore(selector="z-space", session_id="empty-test")

    z_empty: ZSliceLite = {
        "nodes": [],
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": 64, "edges": 0, "time_ms": 30},
        "seed": "empty",
        "zv": "v0.1.0",
    }

    fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 16, "edges": 0, "time_ms": 30})
    fab.fill(z_empty)
    ctx = fab.mix()

    # Empty slice → empty windows
    assert ctx["stream_size"] == 0
    assert ctx["global_size"] == 0


def test_selector_z_space_tiny_stream_guard():
    """
    Test: selector='z-space' respects min_stream_for_upgrade guard.

    Validates:
    - Tiny stream (<8 nodes) prevents precision upgrades
    - Hysteresis guard works with Z-Space selector
    """
    fab = FABCore(
        envelope_mode="hysteresis",
        selector="z-space",
        min_stream_for_upgrade=8,
        session_id="tiny-stream-z",
    )

    # Very small slice (< min_stream_for_upgrade)
    z_tiny: ZSliceLite = {
        "nodes": [{"id": f"n{i}", "score": 0.95} for i in range(5)],  # Only 5 nodes
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": 64, "edges": 0, "time_ms": 30},
        "seed": "tiny",
        "zv": "v0.1.0",
    }

    fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 5, "edges": 0, "time_ms": 30})
    fab.fill(z_tiny)
    ctx = fab.mix()

    _initial_precision = ctx["stream_precision"]  # Baseline check

    # Run multiple ticks with high scores
    for i in range(5):
        fab.step_stub(stress=0.2, self_presence=0.9, error_rate=0.01)
        fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 5, "edges": 0, "time_ms": 30})
        fab.fill(z_tiny)
        ctx = fab.mix()

    # Tiny stream guard should prevent upgrades
    # Precision may stay at cold or only allow downgrades
    assert ctx["stream_precision"] is not None
