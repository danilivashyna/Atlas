import pytest
from orbis_fab.core import FABCore

class _BoomShim:
    @staticmethod
    def select_topk_for_stream(z, k, rng=None):
        raise RuntimeError("boom")
    @staticmethod
    def select_topk_for_global(z, k, exclude_ids=None, rng=None):
        return []

def _make_z(nodes_count=8, seed="cb-test", time_ms=50):
    nodes = [{"id": f"n{i}", "score": 1.0 - i*0.01, "vec": [1.0, 0.0]} for i in range(nodes_count)]
    return {
        "nodes": nodes,
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": nodes_count, "edges": 0, "time_ms": time_ms},
        "seed": seed,
        "zv": "v0.1.0",
    }

def test_cb_opens_on_exception(monkeypatch):
    import orbis_fab.core as core
    monkeypatch.setattr(core, "ZSpaceShim", _BoomShim, raising=True)
    fab = FABCore(selector="z-space", session_id="cb1", ab_shadow_enabled=False)
    fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 8, "edges": 0, "time": 50, "time_ms": 50})
    fab.fill(_make_z())
    d = fab.mix()["diagnostics"]["derived"]
    assert d["zspace_cb_open"] is True
    assert d["z_diversity_gain"] == 0.0

def test_cb_forces_fallback_for_n_ticks(monkeypatch):
    import orbis_fab.core as core
    monkeypatch.setattr(core, "ZSpaceShim", _BoomShim, raising=True)
    fab = FABCore(selector="z-space", session_id="cb2", ab_shadow_enabled=False, z_cb_cooldown_ticks=3)
    fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 8, "edges": 0, "time": 50, "time_ms": 50})
    fab.fill(_make_z())
    fab.mix()
    for t in range(3):
        fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 8, "edges": 0, "time": 50, "time_ms": 50})
        fab.fill(_make_z(seed=f"cb2-{t}"))
        d = fab.mix()["diagnostics"]["derived"]
        assert d["ab_arm"] == "fab"
        # остаётся ли ещё кулдаун — проверяем знак/остаток
        assert isinstance(d["zspace_cb_cooldown_remaining"], int)

def test_timeout_triggers_cb():
    fab = FABCore(selector="z-space", session_id="cb3", ab_shadow_enabled=False, z_time_limit_ms=0.0001)
    fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 8, "edges": 0, "time": 0, "time_ms": 0})
    fab.fill(_make_z(time_ms=0))
    d = fab.mix()["diagnostics"]["derived"]
    assert d["zspace_cb_open"] is True
    assert d["ab_arm"] == "fab"
