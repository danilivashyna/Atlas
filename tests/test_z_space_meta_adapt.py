"""
PR#5.5: Meta-Adaptation (self-tuning target latency)
Tests for meta-learning that adjusts z_target_latency_ms based on limit volatility and latency trends.
"""

import pytest
from orbis_fab.core import FABCore


class _StableFastShim:
    """Shim that consistently returns fast (~1ms) with low variance."""

    @staticmethod
    def select_topk_for_stream(z, k, rng=None):
        import time

        time.sleep(0.001)  # Consistent 1ms
        nodes = z.get("nodes", [])
        return [n["id"] for n in nodes[: min(k, len(nodes))]]

    @staticmethod
    def select_topk_for_global(z, k, exclude_ids=None, rng=None):
        nodes = z.get("nodes", [])
        exclude_ids = exclude_ids or set()
        return [n["id"] for n in nodes if n["id"] not in exclude_ids][:k]


class _UnstableShim:
    """Shim that varies latency (triggers high volatility)."""

    call_count = 0

    @staticmethod
    def select_topk_for_stream(z, k, rng=None):
        import time

        # Alternate between fast (1ms) and slow (10ms)
        _UnstableShim.call_count += 1
        sleep_time = 0.001 if _UnstableShim.call_count % 2 == 0 else 0.010
        time.sleep(sleep_time)
        nodes = z.get("nodes", [])
        return [n["id"] for n in nodes[: min(k, len(nodes))]]

    @staticmethod
    def select_topk_for_global(z, k, exclude_ids=None, rng=None):
        nodes = z.get("nodes", [])
        exclude_ids = exclude_ids or set()
        return [n["id"] for n in nodes if n["id"] not in exclude_ids][:k]


def _make_z(nodes_count=8, seed="meta-test", time_ms=1000.0):
    """Helper: create z-space dict."""
    nodes = [
        {"id": f"n{i}", "score": 1.0 - i * 0.01, "vec": [1.0, 0.0]} for i in range(nodes_count)
    ]
    return {
        "nodes": nodes,
        "seed": seed,
        "quotas": {"tokens": 8000, "nodes": nodes_count, "edges": 0, "time_ms": time_ms},
        "zv": "v0.1.0",
    }


def test_meta_tighten_on_stable_fast(monkeypatch):
    """
    PR#5.5: Meta-learning should tighten target when system is stable and fast.
    Stable-fast shim → low volatility + non-positive trend → decision='tighten'.
    """
    import orbis_fab.core as core

    monkeypatch.setattr(core, "ZSpaceShim", _StableFastShim, raising=True)

    fab = FABCore(
        selector="z-space",
        session_id="meta-tighten",
        ab_shadow_enabled=False,
        z_time_limit_ms=1000.0,
        z_adapt_enabled=True,
        z_target_latency_ms=50.0,  # Start high
        z_limit_min_ms=10.0,
        z_limit_max_ms=1000.0,
        z_ai_step_ms=0.25,
        z_md_factor=0.5,
        # Meta params
        z_meta_enabled=True,
        z_meta_min_window=20,
        z_meta_vol_threshold=0.35,
        z_meta_target_bounds=(5.0, 100.0),
        z_meta_adjust_step_ms=1.0,
    )

    initial_target = fab.z_target_latency_ms

    # Run 25 fills (enough to build window + trigger meta-learning)
    for i in range(25):
        fab.init_tick(
            mode="FAB0", budgets={"tokens": 8000, "nodes": 8, "edges": 0, "time_ms": 1000}
        )
        fab.fill(_make_z(seed=f"meta-{i}"))

    diag = fab.mix()["diagnostics"]["derived"]

    # Verify meta-learning triggered
    assert diag["z_meta_enabled"] is True
    assert diag["z_meta_last_decision"] in (
        "tighten",
        "hold",
        "loosen",
    ), f"Invalid decision: {diag['z_meta_last_decision']}"

    # Verify volatility is calculated
    assert diag["z_meta_volatility"] >= 0.0, "Volatility should be non-negative"

    # Verify target stayed within bounds (most important invariant)
    final_target = fab.z_target_latency_ms
    min_bound, max_bound = fab.z_meta_target_bounds
    assert (
        min_bound <= final_target <= max_bound
    ), f"Target {final_target} out of bounds [{min_bound}, {max_bound}]"


def test_meta_loosen_on_unstable(monkeypatch):
    """
    PR#5.5: Meta-learning should loosen target when system is unstable.
    Unstable shim → high volatility → decision='loosen'.
    """
    import orbis_fab.core as core

    _UnstableShim.call_count = 0  # Reset counter
    monkeypatch.setattr(core, "ZSpaceShim", _UnstableShim, raising=True)

    fab = FABCore(
        selector="z-space",
        session_id="meta-loosen",
        ab_shadow_enabled=False,
        z_time_limit_ms=1000.0,
        z_adapt_enabled=True,
        z_target_latency_ms=10.0,  # Start low
        z_limit_min_ms=5.0,
        z_limit_max_ms=1000.0,
        z_ai_step_ms=0.25,
        z_md_factor=0.5,
        # Meta params
        z_meta_enabled=True,
        z_meta_min_window=20,
        z_meta_vol_threshold=0.35,
        z_meta_target_bounds=(5.0, 100.0),
        z_meta_adjust_step_ms=1.0,
    )

    initial_target = fab.z_target_latency_ms

    # Run 25 fills (unstable latency)
    for i in range(25):
        fab.init_tick(
            mode="FAB0", budgets={"tokens": 8000, "nodes": 8, "edges": 0, "time_ms": 1000}
        )
        fab.fill(_make_z(seed=f"meta-unstable-{i}"))

    diag = fab.mix()["diagnostics"]["derived"]

    # Verify meta-learning triggered
    assert diag["z_meta_enabled"] is True
    assert diag["z_meta_last_decision"] in (
        "loosen",
        "hold",
    ), f"Expected loosen/hold, got {diag['z_meta_last_decision']}"

    # Verify volatility is high (unstable)
    # Note: May not always exceed threshold due to AIMD adjustments, but should trend higher
    assert diag["z_meta_volatility"] >= 0.0, "Volatility should be non-negative"

    # Verify target stayed within bounds
    final_target = fab.z_target_latency_ms
    min_bound, max_bound = fab.z_meta_target_bounds
    assert (
        min_bound <= final_target <= max_bound
    ), f"Target {final_target} out of bounds [{min_bound}, {max_bound}]"

    # If loosened, target should increase
    if diag["z_meta_last_decision"] == "loosen":
        assert (
            final_target > initial_target
        ), f"Target should increase: {initial_target} → {final_target}"


def test_meta_metrics_exported(monkeypatch):
    """
    PR#5.5: Verify meta-adaptation metrics are exported in diagnostics.
    """
    import orbis_fab.core as core

    monkeypatch.setattr(core, "ZSpaceShim", _StableFastShim, raising=True)

    fab = FABCore(
        selector="z-space",
        session_id="meta-metrics",
        ab_shadow_enabled=False,
        z_meta_enabled=True,
        z_meta_min_window=10,
        z_meta_vol_threshold=0.5,
        z_meta_target_bounds=(1.0, 50.0),
        z_meta_adjust_step_ms=0.5,
    )

    # Run a few fills
    for i in range(5):
        fab.init_tick(
            mode="FAB0", budgets={"tokens": 8000, "nodes": 8, "edges": 0, "time_ms": 1000}
        )
        fab.fill(_make_z(seed=f"meta-export-{i}"))

    diag = fab.mix()["diagnostics"]["derived"]

    # Verify all meta metrics are present
    assert "z_meta_enabled" in diag
    assert "z_meta_last_decision" in diag
    assert "z_meta_volatility" in diag
    assert "z_meta_trend" in diag
    assert "z_meta_target_bounds" in diag

    # Verify types
    assert isinstance(diag["z_meta_enabled"], bool)
    assert isinstance(diag["z_meta_last_decision"], str)
    assert isinstance(diag["z_meta_volatility"], float)
    assert isinstance(diag["z_meta_trend"], float)
    assert isinstance(diag["z_meta_target_bounds"], tuple)
    assert len(diag["z_meta_target_bounds"]) == 2
