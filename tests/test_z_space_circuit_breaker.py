import pytest
from typing import cast
from orbis_fab.core import FABCore
from orbis_fab.types import Budgets, ZSliceLite


def _budgets(tokens=8000, nodes=8, edges=0, time_ms=50) -> Budgets:
    """Create type-safe Budgets for testing."""
    return cast(Budgets, {
        "tokens": tokens,
        "nodes": nodes,
        "edges": edges,
        "time_ms": time_ms
    })

class _BoomShim:
    @staticmethod
    def select_topk_for_stream(z, k, rng=None):
        raise RuntimeError("boom")
    @staticmethod
    def select_topk_for_global(z, k, exclude_ids=None, rng=None):
        return []

def _make_z(nodes_count=8, seed="cb-test", time_ms=50) -> ZSliceLite:
    """Create type-safe ZSliceLite for testing."""
    nodes = [{"id": f"n{i}", "score": 1.0 - i*0.01, "vec": [1.0, 0.0]} for i in range(nodes_count)]
    return cast(ZSliceLite, {
        "nodes": nodes,
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": nodes_count, "edges": 0, "time_ms": time_ms},
        "seed": seed,
        "zv": "v0.1.0",
    })

def test_cb_opens_on_exception(monkeypatch):
    import orbis_fab.core as core
    monkeypatch.setattr(core, "ZSpaceShim", _BoomShim, raising=True)
    fab = FABCore(selector="z-space", session_id="cb1", ab_shadow_enabled=False)
    budgets = cast(Budgets, {"tokens": 8000, "nodes": 8, "edges": 0, "time_ms": 50})
    fab.init_tick(mode="FAB0", budgets=budgets)
    fab.fill(_make_z())
    d = fab.mix()["diagnostics"]["derived"]
    assert d["zspace_cb_open"] is True
    assert d["z_diversity_gain"] == 0.0

def test_cb_forces_fallback_for_n_ticks(monkeypatch):
    import orbis_fab.core as core
    monkeypatch.setattr(core, "ZSpaceShim", _BoomShim, raising=True)
    fab = FABCore(selector="z-space", session_id="cb2", ab_shadow_enabled=False, z_cb_cooldown_ticks=3)
    fab.init_tick(mode="FAB0", budgets=_budgets())
    fab.fill(_make_z())
    fab.mix()
    for t in range(3):
        fab.init_tick(mode="FAB0", budgets=_budgets())
        fab.fill(_make_z(seed=f"cb2-{t}"))
        d = fab.mix()["diagnostics"]["derived"]
        assert d["ab_arm"] == "fab"
        # остаётся ли ещё кулдаун — проверяем знак/остаток
        assert isinstance(d["zspace_cb_cooldown_remaining"], int)

def test_timeout_triggers_cb():
    fab = FABCore(selector="z-space", session_id="cb3", ab_shadow_enabled=False, z_time_limit_ms=0.0001)
    fab.init_tick(mode="FAB0", budgets=_budgets(time_ms=0))
    fab.fill(_make_z(time_ms=0))
    d = fab.mix()["diagnostics"]["derived"]
    assert d["zspace_cb_open"] is True
    assert d["ab_arm"] == "fab"

# PR#5.3.1: CB Reason Tracking Tests

def test_cb_reason_timeout(monkeypatch):
    """CB opened by timeout should set reason='timeout'"""
    fab = FABCore(selector="z-space", session_id="cb-reason-1", ab_shadow_enabled=False, z_time_limit_ms=0.0001)
    fab.init_tick(mode="FAB0", budgets=_budgets(time_ms=0))
    fab.fill(_make_z(time_ms=0))
    d = fab.mix()["diagnostics"]["derived"]
    assert d["zspace_cb_reason"] == "timeout"
    assert d["zspace_cb_open_count"] == 1
    assert d["zspace_cb_reason_counts"]["timeout"] == 1
    assert d["zspace_cb_reason_counts"]["exception"] == 0

def test_cb_reason_exception(monkeypatch):
    """CB opened by exception should set reason='exception'"""
    import orbis_fab.core as core
    monkeypatch.setattr(core, "ZSpaceShim", _BoomShim, raising=True)
    fab = FABCore(selector="z-space", session_id="cb-reason-2", ab_shadow_enabled=False)
    fab.init_tick(mode="FAB0", budgets=_budgets())
    fab.fill(_make_z())
    d = fab.mix()["diagnostics"]["derived"]
    assert d["zspace_cb_reason"] == "exception"
    assert d["zspace_cb_open_count"] == 1
    assert d["zspace_cb_reason_counts"]["exception"] == 1
    assert d["zspace_cb_reason_counts"]["timeout"] == 0

def test_cb_reason_unavailable(monkeypatch):
    """CB opened by HAS_ZSPACE=False should set reason='unavailable'"""
    import orbis_fab.core as core
    original_has_zspace = core.HAS_ZSPACE
    monkeypatch.setattr(core, "HAS_ZSPACE", False, raising=False)
    fab = FABCore(selector="z-space", session_id="cb-reason-3", ab_shadow_enabled=False)
    fab.init_tick(mode="FAB0", budgets=_budgets())
    fab.fill(_make_z())
    d = fab.mix()["diagnostics"]["derived"]
    assert d["zspace_cb_reason"] == "unavailable"
    assert d["zspace_cb_open_count"] == 1
    assert d["zspace_cb_reason_counts"]["unavailable"] == 1
    monkeypatch.setattr(core, "HAS_ZSPACE", original_has_zspace, raising=False)

def test_cb_reason_counts_accumulate(monkeypatch):
    """Multiple CB opens should accumulate counts correctly"""
    import orbis_fab.core as core
    monkeypatch.setattr(core, "ZSpaceShim", _BoomShim, raising=True)
    fab = FABCore(selector="z-space", session_id="cb-accum", ab_shadow_enabled=False, z_cb_cooldown_ticks=2)
    
    # First open: exception
    fab.init_tick(mode="FAB0", budgets=_budgets())
    fab.fill(_make_z(seed="accum-1"))
    d = fab.mix()["diagnostics"]["derived"]
    assert d["zspace_cb_open_count"] == 1
    assert d["zspace_cb_reason_counts"]["exception"] == 1
    
    # Wait 2 ticks for CB to close
    for i in range(2):
        fab.current_tick += 1
        fab.init_tick(mode="FAB0", budgets=_budgets())
        fab.fill(_make_z(seed=f"accum-wait-{i}"))
        fab.mix()
    
    # Second open: exception again
    fab.current_tick += 1
    fab.init_tick(mode="FAB0", budgets=_budgets())
    fab.fill(_make_z(seed="accum-2"))
    d = fab.mix()["diagnostics"]["derived"]
    assert d["zspace_cb_open_count"] == 2
    assert d["zspace_cb_reason_counts"]["exception"] == 2
