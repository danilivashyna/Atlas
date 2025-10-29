"""Test FAB bit-envelope precision assignment - Phase A MVP

Tests precision assignment based on node score:
- hot: score ≥0.80 → mxfp8.0 (highest precision)
- warm-high: score ≥0.60 → mxfp6.0
- warm-low: score ≥0.40 → mxfp5.25
- cold: score <0.40 → mxfp4.12 (global default)

Invariants:
- Precision increases with score
- Global window defaults to cold (mxfp4.12)
- Stream window uses score-based assignment
- Phase A: Simple step function (no hysteresis)
"""

from orbis_fab import assign_precision


def test_precision_hot_band():
    """Score ≥0.80 → mxfp8.0 (hot)"""
    assert assign_precision(0.80).startswith("mxfp8")
    assert assign_precision(0.85).startswith("mxfp8")
    assert assign_precision(0.90).startswith("mxfp8")
    assert assign_precision(0.95).startswith("mxfp8")
    assert assign_precision(1.00).startswith("mxfp8")


def test_precision_warm_high_band():
    """0.60 ≤ score <0.80 → mxfp6.0 (warm-high)"""
    assert assign_precision(0.60).startswith("mxfp6")
    assert assign_precision(0.65).startswith("mxfp6")
    assert assign_precision(0.70).startswith("mxfp6")
    assert assign_precision(0.75).startswith("mxfp6")
    assert assign_precision(0.79).startswith("mxfp6")


def test_precision_warm_low_band():
    """0.40 ≤ score <0.60 → mxfp5.25 (warm-low)"""
    assert assign_precision(0.40).startswith("mxfp5")
    assert assign_precision(0.45).startswith("mxfp5")
    assert assign_precision(0.50).startswith("mxfp5")
    assert assign_precision(0.55).startswith("mxfp5")
    assert assign_precision(0.59).startswith("mxfp5")


def test_precision_cold_band():
    """Score <0.40 → mxfp4.12 (cold/global default)"""
    assert assign_precision(0.00).startswith("mxfp4")
    assert assign_precision(0.10).startswith("mxfp4")
    assert assign_precision(0.20).startswith("mxfp4")
    assert assign_precision(0.30).startswith("mxfp4")
    assert assign_precision(0.39).startswith("mxfp4")


def test_precision_boundary_conditions():
    """Verify exact boundary behavior"""
    # Just below hot threshold
    assert assign_precision(0.79) == "mxfp6.0"
    # At hot threshold
    assert assign_precision(0.80) == "mxfp8.0"
    
    # Just below warm-high threshold
    assert assign_precision(0.59) == "mxfp5.25"
    # At warm-high threshold
    assert assign_precision(0.60) == "mxfp6.0"
    
    # Just below warm-low threshold
    assert assign_precision(0.39) == "mxfp4.12"
    # At warm-low threshold
    assert assign_precision(0.40) == "mxfp5.25"


def test_precision_monotonic_increase():
    """Precision increases monotonically with score"""
    scores = [0.1, 0.3, 0.5, 0.7, 0.9]
    precisions = [assign_precision(s) for s in scores]
    
    # Extract numeric part (e.g., "mxfp6.0" → 6.0)
    def extract_bits(p: str) -> float:
        return float(p.replace("mxfp", ""))
    
    bits = [extract_bits(p) for p in precisions]
    
    # Verify monotonic increase
    assert bits == sorted(bits), "Precision should increase with score"
    
    # Expected: [4.12, 4.12, 5.25, 6.0, 8.0]
    assert bits[0] == 4.12  # cold
    assert bits[2] == 5.25  # warm-low
    assert bits[3] == 6.0   # warm-high
    assert bits[4] == 8.0   # hot


def test_precision_realistic_scores():
    """Test with realistic score distribution"""
    # High-relevance stream nodes
    assert assign_precision(0.92) == "mxfp8.0"
    assert assign_precision(0.88) == "mxfp8.0"
    assert assign_precision(0.81) == "mxfp8.0"
    
    # Medium-relevance nodes
    assert assign_precision(0.72) == "mxfp6.0"
    assert assign_precision(0.68) == "mxfp6.0"
    
    # Background/global nodes
    assert assign_precision(0.35) == "mxfp4.12"
    assert assign_precision(0.15) == "mxfp4.12"
