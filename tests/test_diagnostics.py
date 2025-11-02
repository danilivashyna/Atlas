"""
Tests for Diagnostics Counters (Phase B.5)

Coverage:
- Counter increments (ticks, fills, mixes)
- Envelope changes tracking
- Mode transitions tracking
- Rebalance events tracking
- Gauge updates
- Snapshot shape and values
- Reset functionality
- Derived metrics (changes_per_1k_ticks, rebalance_per_fill)
"""

from src.orbis_fab.diagnostics import Diagnostics


def test_diagnostics_counters_increment():
    """Counters increment on method calls"""
    diag = Diagnostics()

    # Initial state
    assert diag.ticks == 0
    assert diag.fills == 0
    assert diag.mixes == 0

    # Increment
    diag.inc_ticks()
    diag.inc_fills()
    diag.inc_mixes()

    assert diag.ticks == 1
    assert diag.fills == 1
    assert diag.mixes == 1

    # Multiple increments
    diag.inc_ticks(5)
    diag.inc_fills(2)

    assert diag.ticks == 6
    assert diag.fills == 3


def test_diagnostics_envelope_changes():
    """Envelope changes increment on precision shifts"""
    diag = Diagnostics()

    assert diag.envelope_changes == 0

    # Simulate precision changes
    diag.inc_envelope_changes()
    assert diag.envelope_changes == 1

    diag.inc_envelope_changes()
    assert diag.envelope_changes == 2

    # Multiple changes
    diag.inc_envelope_changes(3)
    assert diag.envelope_changes == 5


def test_diagnostics_mode_transitions():
    """Mode transitions increment on FAB mode changes"""
    diag = Diagnostics()

    assert diag.mode_transitions == 0
    assert diag.mode == "FAB0"

    # Transition FAB0 → FAB1
    diag.inc_mode_transitions()
    diag.set_gauge(mode="FAB1")

    assert diag.mode_transitions == 1
    assert diag.mode == "FAB1"

    # Transition FAB1 → FAB2
    diag.inc_mode_transitions()
    diag.set_gauge(mode="FAB2")

    assert diag.mode_transitions == 2
    assert diag.mode == "FAB2"


def test_diagnostics_rebalance_events():
    """Rebalance events track MMR penalties"""
    diag = Diagnostics()

    assert diag.rebalance_events == 0

    # Add rebalance events (e.g., nodes_penalized from MMR)
    diag.add_rebalance_events(5)
    assert diag.rebalance_events == 5

    diag.add_rebalance_events(3)
    assert diag.rebalance_events == 8

    # Zero events (no-op)
    diag.add_rebalance_events(0)
    assert diag.rebalance_events == 8


def test_diagnostics_gauges_update():
    """Gauges update via set_gauge"""
    diag = Diagnostics()

    # Initial gauges
    assert diag.mode == "FAB0"
    assert diag.global_precision == "mxfp4.12"
    assert diag.stream_precision == "mxfp4.12"
    assert diag.stable_ticks == 0
    assert diag.cooldown_remaining == 0

    # Update multiple gauges
    diag.set_gauge(
        mode="FAB1",
        global_precision="mxfp6.0",
        stream_precision="mxfp8.0",
        stable_ticks=100,
        cooldown_remaining=5,
    )

    assert diag.mode == "FAB1"
    assert diag.global_precision == "mxfp6.0"
    assert diag.stream_precision == "mxfp8.0"
    assert diag.stable_ticks == 100
    assert diag.cooldown_remaining == 5


def test_diagnostics_snapshot_shape():
    """Snapshot returns correct JSON structure"""
    diag = Diagnostics()

    # Setup some state
    diag.inc_ticks(10)
    diag.inc_fills(3)
    diag.inc_mixes(5)
    diag.inc_envelope_changes(2)
    diag.inc_mode_transitions(1)
    diag.add_rebalance_events(7)
    diag.set_gauge(
        mode="FAB1",
        global_precision="mxfp5.25",
        stream_precision="mxfp6.0",
        stable_ticks=50,
        cooldown_remaining=2,
    )

    snapshot = diag.snapshot()

    # Check structure
    assert "counters" in snapshot
    assert "gauges" in snapshot

    # Check counters
    counters = snapshot["counters"]
    assert counters["ticks"] == 10
    assert counters["fills"] == 3
    assert counters["mixes"] == 5
    assert counters["envelope_changes"] == 2
    assert counters["mode_transitions"] == 1
    assert counters["rebalance_events"] == 7

    # Check gauges
    gauges = snapshot["gauges"]
    assert gauges["mode"] == "FAB1"
    assert gauges["global_precision"] == "mxfp5.25"
    assert gauges["stream_precision"] == "mxfp6.0"
    assert gauges["stable_ticks"] == 50
    assert gauges["cooldown_remaining"] == 2


def test_diagnostics_reset():
    """Reset zeros counters, preserves gauges"""
    diag = Diagnostics()

    # Build state
    diag.inc_ticks(20)
    diag.inc_fills(5)
    diag.inc_mixes(10)
    diag.inc_envelope_changes(3)
    diag.inc_mode_transitions(2)
    diag.add_rebalance_events(15)
    diag.set_gauge(mode="FAB2", global_precision="mxfp8.0", stable_ticks=200)

    # Reset
    diag.reset()

    # Counters zeroed
    assert diag.ticks == 0
    assert diag.fills == 0
    assert diag.mixes == 0
    assert diag.envelope_changes == 0
    assert diag.mode_transitions == 0
    assert diag.rebalance_events == 0

    # Gauges preserved
    assert diag.mode == "FAB2"
    assert diag.global_precision == "mxfp8.0"
    assert diag.stable_ticks == 200


def test_diagnostics_changes_per_1k_ticks():
    """Derived metric: envelope changes per 1000 ticks"""
    diag = Diagnostics()

    # No ticks → 0.0
    assert diag.changes_per_1k_ticks() == 0.0

    # 10 ticks, 2 changes → (2/10)*1000 = 200.0
    diag.inc_ticks(10)
    diag.inc_envelope_changes(2)
    assert diag.changes_per_1k_ticks() == 200.0

    # 1000 ticks, 5 changes → (5/1000)*1000 = 5.0
    diag.reset()
    diag.inc_ticks(1000)
    diag.inc_envelope_changes(5)
    assert diag.changes_per_1k_ticks() == 5.0


def test_diagnostics_rebalance_per_fill():
    """Derived metric: rebalance events per fill"""
    diag = Diagnostics()

    # No fills → 0.0
    assert diag.rebalance_per_fill() == 0.0

    # 5 fills, 15 rebalances → 15/5 = 3.0
    diag.inc_fills(5)
    diag.add_rebalance_events(15)
    assert diag.rebalance_per_fill() == 3.0

    # 10 fills, 5 rebalances → 5/10 = 0.5
    diag.reset()
    diag.inc_fills(10)
    diag.add_rebalance_events(5)
    assert diag.rebalance_per_fill() == 0.5


def test_diagnostics_realistic_scenario():
    """Realistic scenario: tracking FAB operations"""
    diag = Diagnostics()

    # Phase 1: FAB0 initialization (5 ticks, 2 fills, 1 mix)
    for _ in range(5):
        diag.inc_ticks()
    diag.inc_fills(2)
    diag.inc_mixes()
    diag.set_gauge(mode="FAB0", global_precision="mxfp4.12")

    snapshot1 = diag.snapshot()
    assert snapshot1["counters"]["ticks"] == 5
    assert snapshot1["counters"]["fills"] == 2
    assert snapshot1["gauges"]["mode"] == "FAB0"

    # Phase 2: Transition to FAB1 (10 more ticks, 3 fills, envelope change)
    for _ in range(10):
        diag.inc_ticks()
    diag.inc_fills(3)
    diag.inc_envelope_changes()  # Precision upgrade
    diag.inc_mode_transitions()  # FAB0 → FAB1
    diag.set_gauge(mode="FAB1", stream_precision="mxfp6.0", stable_ticks=50)
    diag.inc_mixes()

    snapshot2 = diag.snapshot()
    assert snapshot2["counters"]["ticks"] == 15
    assert snapshot2["counters"]["fills"] == 5
    assert snapshot2["counters"]["envelope_changes"] == 1
    assert snapshot2["counters"]["mode_transitions"] == 1
    assert snapshot2["gauges"]["mode"] == "FAB1"
    assert snapshot2["gauges"]["stream_precision"] == "mxfp6.0"

    # Phase 3: MMR rebalancing (5 fills, 12 nodes penalized)
    diag.inc_fills(5)
    diag.add_rebalance_events(12)
    diag.inc_mixes()

    snapshot3 = diag.snapshot()
    assert snapshot3["counters"]["fills"] == 10
    assert snapshot3["counters"]["rebalance_events"] == 12
    assert diag.rebalance_per_fill() == 1.2  # 12/10

    # Phase 4: Reset and verify
    diag.reset()
    snapshot4 = diag.snapshot()
    assert snapshot4["counters"]["ticks"] == 0
    assert snapshot4["counters"]["rebalance_events"] == 0
    assert snapshot4["gauges"]["mode"] == "FAB1"  # Preserved
