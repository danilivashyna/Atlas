"""
PR#5.4: AIMD Adaptive Time Limit
Tests for additive-increase / multiplicative-decrease adaptive budget.
"""

import pytest
from orbis_fab.core import FABCore


class _FastShim:
    """Shim that returns quickly (1ms latency)."""
    @staticmethod
    def select_topk_for_stream(z, k, rng=None):
        import time
        time.sleep(0.001)  # 1ms
        # Return IDs of top k nodes
        nodes = z.get("nodes", [])
        return [n["id"] for n in nodes[:min(k, len(nodes))]]
    
    @staticmethod
    def select_topk_for_global(z, k, exclude_ids=None, rng=None):
        nodes = z.get("nodes", [])
        exclude_ids = exclude_ids or set()
        return [n["id"] for n in nodes if n["id"] not in exclude_ids][:k]


class _SlowShim:
    """Shim that sleeps long enough to trigger timeout."""
    @staticmethod
    def select_topk_for_stream(z, k, rng=None):
        import time
        time.sleep(0.050)  # 50ms (way over any limit)
        nodes = z.get("nodes", [])
        return [n["id"] for n in nodes[:min(k, len(nodes))]]
    
    @staticmethod
    def select_topk_for_global(z, k, exclude_ids=None, rng=None):
        nodes = z.get("nodes", [])
        exclude_ids = exclude_ids or set()
        return [n["id"] for n in nodes if n["id"] not in exclude_ids][:k]


def _make_z(nodes_count=8, seed="aimd-test", time_ms=50.0):
    """Helper: create z-space dict."""
    nodes = [{"id": f"n{i}", "score": 1.0 - i*0.01, "vec": [1.0, 0.0]} for i in range(nodes_count)]
    return {
        "nodes": nodes,
        "seed": seed,
        "quotas": {"tokens": 8000, "nodes": nodes_count, "edges": 0, "time_ms": time_ms},
        "zv": "v0.1.0"
    }


def test_adapt_increase_on_success(monkeypatch):
    """
    PR#5.4: AI (Additive Increase) when latency <= target.
    Fast z-space calls → limit grows by +0.25ms each tick.
    """
    import orbis_fab.core as core
    monkeypatch.setattr(core, "ZSpaceShim", _FastShim, raising=True)
    
    fab = FABCore(
        selector="z-space",
        session_id="aimd-ai",
        ab_shadow_enabled=False,
        z_time_limit_ms=1000.0,  # Very high hard cap
        z_adapt_enabled=True,
        z_target_latency_ms=500.0,  # High target (will always be met)
        z_limit_min_ms=10.0,
        z_limit_max_ms=1000.0,
        z_ai_step_ms=0.25,
        z_md_factor=0.5
    )
    
    # Set initial limit to something below max
    fab.z_limit_current_ms = 100.0
    initial_limit = fab.z_limit_current_ms
    
    # Three fast fills (latency will be ~1-5ms, well below 500ms target)
    fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 8, "edges": 0, "time_ms": 1000})
    fab.fill(_make_z(time_ms=1000.0))
    limit_after_1 = fab.z_limit_current_ms
    
    fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 8, "edges": 0, "time_ms": 1000})
    fab.fill(_make_z(time_ms=1000.0))
    limit_after_2 = fab.z_limit_current_ms
    
    fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 8, "edges": 0, "time_ms": 1000})
    fab.fill(_make_z(time_ms=1000.0))
    limit_after_3 = fab.z_limit_current_ms
    
    # Verify additive increase: +0.25ms each time (latency << target)
    assert limit_after_1 == pytest.approx(initial_limit + 0.25, abs=0.01), f"Expected {initial_limit + 0.25}, got {limit_after_1}"
    assert limit_after_2 == pytest.approx(initial_limit + 0.50, abs=0.01), f"Expected {initial_limit + 0.50}, got {limit_after_2}"
    assert limit_after_3 == pytest.approx(initial_limit + 0.75, abs=0.01), f"Expected {initial_limit + 0.75}, got {limit_after_3}"
    assert fab.z_limit_last_adjust == "increase"


def test_adapt_decrease_on_timeout(monkeypatch):
    """
    PR#5.4: MD (Multiplicative Decrease) on timeout.
    Timeout triggers CB → limit shrinks by *0.5.
    """
    import orbis_fab.core as core
    monkeypatch.setattr(core, "ZSpaceShim", _SlowShim, raising=True)
    
    fab = FABCore(
        selector="z-space",
        session_id="aimd-md",
        ab_shadow_enabled=False,
        z_time_limit_ms=10.0,
        z_adapt_enabled=True,
        z_target_latency_ms=2.0,
        z_limit_min_ms=1.0,
        z_limit_max_ms=10.0,
        z_ai_step_ms=0.25,
        z_md_factor=0.5
    )
    
    initial_limit = fab.z_limit_current_ms
    
    fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 8, "edges": 0, "time_ms": 1})
    fab.fill(_make_z(time_ms=1.0))
    
    # Verify multiplicative decrease: limit *= 0.5
    expected_limit = initial_limit * 0.5
    assert fab.z_limit_current_ms == pytest.approx(expected_limit, abs=0.01)
    assert fab.z_limit_last_adjust == "decrease"
    assert fab.z_cb_remaining > 0  # CB opened


def test_adapt_clamped_within_bounds(monkeypatch):
    """
    PR#5.4: Adaptive limit always clamped to [min, max].
    Test both lower and upper bounds.
    """
    import orbis_fab.core as core
    
    # Lower bound test with SlowShim
    monkeypatch.setattr(core, "ZSpaceShim", _SlowShim, raising=True)
    
    fab = FABCore(
        selector="z-space",
        session_id="aimd-clamp",
        ab_shadow_enabled=False,
        z_time_limit_ms=100.0,
        z_adapt_enabled=True,
        z_target_latency_ms=50.0,
        z_limit_min_ms=1.0,
        z_limit_max_ms=100.0,
        z_ai_step_ms=0.25,
        z_md_factor=0.5
    )
    
    # Lower bound: decrease until hitting min (1.0ms)
    # Start at 2.0ms, MD factor 0.5:
    # 2.0 * 0.5 = 1.0 (at min)
    fab.z_limit_current_ms = 2.0
    fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 8, "edges": 0, "time_ms": 1})
    fab.fill(_make_z(time_ms=1.0))
    assert fab.z_limit_current_ms == pytest.approx(1.0, abs=0.01)  # At min
    
    # Try to decrease again (should stay at min)
    fab._z_adapt("timeout", None)
    assert fab.z_limit_current_ms == pytest.approx(1.0, abs=0.01)  # Clamped at min
    
    # Upper bound test with FastShim
    monkeypatch.setattr(core, "ZSpaceShim", _FastShim, raising=True)
    
    fab2 = FABCore(
        selector="z-space",
        session_id="aimd-clamp-2",
        ab_shadow_enabled=False,
        z_time_limit_ms=100.0,
        z_adapt_enabled=True,
        z_target_latency_ms=50.0,
        z_limit_min_ms=1.0,
        z_limit_max_ms=100.0,
        z_ai_step_ms=0.25,
        z_md_factor=0.5
    )
    
    # Upper bound: increase until hitting max (100.0ms)
    fab2.z_limit_current_ms = 99.0
    fab2.z_cb_remaining = 0  # Clear CB
    
    fab2.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 8, "edges": 0, "time_ms": 100})
    fab2.fill(_make_z(time_ms=100.0))
    assert fab2.z_limit_current_ms == pytest.approx(99.25, abs=0.01)  # 99.0 + 0.25
    
    # Try to increase beyond max (100.0)
    fab2.z_limit_current_ms = 99.9
    fab2.z_cb_remaining = 0
    
    fab2.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 8, "edges": 0, "time_ms": 100})
    fab2.fill(_make_z(time_ms=100.0))
    # 99.9 + 0.25 = 100.15 → clamped to 100.0 (max)
    assert fab2.z_limit_current_ms == pytest.approx(100.0, abs=0.01)  # Clamped at max

