"""Test FAB backpressure classification - Phase A MVP

Tests token-bucket backpressure control:
- ok: tokens <2000 (normal operation)
- slow: 2000 ≤ tokens <5000 (degraded)
- reject: tokens ≥5000 (reject new requests)

Invariants:
- Classification is pure function (no state)
- Thresholds are configurable
- Future: token-bucket with refill rate
"""

from orbis_fab import classify_backpressure


def test_backpressure_ok_band():
    """Tokens <2000 → ok (normal operation)"""
    assert classify_backpressure(0) == "ok"
    assert classify_backpressure(500) == "ok"
    assert classify_backpressure(1000) == "ok"
    assert classify_backpressure(1999) == "ok"


def test_backpressure_slow_band():
    """2000 ≤ tokens <5000 → slow (degraded)"""
    assert classify_backpressure(2000) == "slow"
    assert classify_backpressure(3000) == "slow"
    assert classify_backpressure(4000) == "slow"
    assert classify_backpressure(4999) == "slow"


def test_backpressure_reject_band():
    """Tokens ≥5000 → reject"""
    assert classify_backpressure(5000) == "reject"
    assert classify_backpressure(6000) == "reject"
    assert classify_backpressure(10000) == "reject"


def test_backpressure_custom_thresholds():
    """Custom thresholds work correctly"""
    # Lower thresholds (more aggressive)
    assert classify_backpressure(500, threshold_ok=1000, threshold_reject=2000) == "ok"
    assert classify_backpressure(1500, threshold_ok=1000, threshold_reject=2000) == "slow"
    assert classify_backpressure(2500, threshold_ok=1000, threshold_reject=2000) == "reject"

    # Higher thresholds (more permissive)
    assert classify_backpressure(3000, threshold_ok=5000, threshold_reject=10000) == "ok"
    assert classify_backpressure(7000, threshold_ok=5000, threshold_reject=10000) == "slow"
    assert classify_backpressure(12000, threshold_ok=5000, threshold_reject=10000) == "reject"


def test_backpressure_boundary_conditions():
    """Verify exact boundary behavior"""
    # Default thresholds: ok=2000, reject=5000

    # Just below ok threshold
    assert classify_backpressure(1999) == "ok"
    # At ok threshold
    assert classify_backpressure(2000) == "slow"

    # Just below reject threshold
    assert classify_backpressure(4999) == "slow"
    # At reject threshold
    assert classify_backpressure(5000) == "reject"
