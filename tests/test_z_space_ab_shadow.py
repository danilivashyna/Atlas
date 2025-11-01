"""Phase 2 PR#5: Shadow A/B selector integration tests

Tests deterministic A/B routing between fab and z-space selectors.

Test Coverage:
1. Disabled shadow (ab_shadow_enabled=False) → respects base selector
2. Force shadow arm (ab_ratio=1.0) → always uses shadow_selector
3. Force base arm (ab_ratio=0.0) → never uses shadow_selector
4. Mixed routing (ab_ratio=0.5) → both arms used across ticks
"""

import pytest


def make_nodes(n, base=1.0, step=0.001):
    """Create test nodes with decreasing scores"""
    return [{"id": f"s{i:02d}", "score": base - i * step} for i in range(n)]


def make_slice(nodes, seed="ab-shadow", nodes_quota=None):
    """Create Z-slice for testing"""
    return {
        "nodes": nodes,
        "edges": [],
        "quotas": {"nodes": nodes_quota or len(nodes), "tokens": 8000, "edges": 0, "time_ms": 50},
        "seed": seed,
        "zv": "v0.1.0",
    }


def init_fab(selector="fab", session_id="ab-test", ab_enabled=False, ab_ratio=0.5, shadow_selector="z-space"):
    """Initialize FABCore with A/B configuration"""
    from orbis_fab.core import FABCore
    fab = FABCore(
        selector=selector,
        session_id=session_id,
        envelope_mode="legacy",
        ab_shadow_enabled=ab_enabled,
        ab_ratio=ab_ratio,
        shadow_selector=shadow_selector,
    )
    fab.init_tick(mode="FAB0", budgets={"tokens": 8000, "nodes": 16, "edges": 0, "time_ms": 50})
    return fab


def test_ab_shadow_disabled_respects_base_selector():
    """Test: Shadow A/B disabled → base selector used"""
    nodes = make_nodes(16)
    z = make_slice(nodes, seed="no-ab")
    fab = init_fab(selector="fab", ab_enabled=False)
    fab.fill(z)
    ctx = fab.mix()
    d = ctx["diagnostics"]["derived"]
    
    # Validate: FAB selector used, no shadow
    assert d["z_selector_used"] is False
    assert d["ab_shadow_enabled"] is False
    assert d["ab_arm"] == "fab"


def test_ab_shadow_force_shadow_arm_when_ratio_1():
    """Test: ab_ratio=1.0 → always shadow arm"""
    nodes = make_nodes(16)
    z = make_slice(nodes, seed="force-shadow")
    fab = init_fab(selector="fab", ab_enabled=True, ab_ratio=1.0, shadow_selector="z-space")
    fab.fill(z)
    ctx = fab.mix()
    d = ctx["diagnostics"]["derived"]
    
    # Validate: Shadow arm chosen (z-space)
    assert d["z_selector_used"] is True  # shadow arm chosen
    assert d["ab_shadow_enabled"] is True
    assert d["ab_arm"] == "z-space"


def test_ab_shadow_force_base_arm_when_ratio_0():
    """Test: ab_ratio=0.0 → never shadow arm, always base"""
    nodes = make_nodes(16)
    z = make_slice(nodes, seed="force-base")
    fab = init_fab(selector="z-space", ab_enabled=True, ab_ratio=0.0, shadow_selector="fab")
    fab.fill(z)
    ctx = fab.mix()
    d = ctx["diagnostics"]["derived"]
    
    # Validate: Base is z-space, shadow never selected with ratio=0
    assert d["z_selector_used"] is True  # base is z-space
    assert d["ab_shadow_enabled"] is True
    assert d["ab_arm"] == "z-space"


def test_ab_shadow_uses_both_arms_across_ticks_when_ratio_half():
    """Test: ab_ratio=0.5 → both arms used deterministically across ticks"""
    nodes = make_nodes(16)
    z = make_slice(nodes, seed="half")
    fab = init_fab(selector="fab", ab_enabled=True, ab_ratio=0.5, shadow_selector="z-space")
    used = set()
    for _ in range(10):
        fab.fill(z)
        ctx = fab.mix()
        used.add(ctx["diagnostics"]["derived"]["ab_arm"])
        fab.current_tick += 1  # advance tick to change deterministic draw
    
    # Validate: Both arms appeared at least once
    assert "fab" in used and "z-space" in used
