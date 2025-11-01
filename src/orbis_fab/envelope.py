"""FAB Bit-Envelope Policy - Phase A MVP

Dynamic precision assignment based on node score.

Precision bands (mxfp format):
- hot: score ≥0.80 → mxfp8.0 (highest precision)
- warm-high: score ≥0.60 → mxfp6.0
- warm-low: score ≥0.40 → mxfp5.25
- cold: score <0.40 → mxfp4.12 (background/global default)

Hysteresis:
- Phase A: Simple step function (no hysteresis yet)
- Phase B: Add cooldown rate ≤1 change/sec/layer
- Phase C: Add spike-up fast, cool-down slow policy

Invariants:
- Precision never increases during cooldown
- Global window defaults to cold (mxfp4.12)
- Stream window uses score-based assignment
"""

# Precision level mapping (Phase C+)
# Used for safe comparison of precision strings
PRECISION_LEVELS = {
    "mxfp4.12": 0,  # cold
    "mxfp5.25": 1,  # warm-low
    "mxfp6.0": 2,   # warm-high
    "mxfp8.0": 3,   # hot
}


def precision_level(precision: str) -> int:
    """Get numeric level for precision comparison
    
    Args:
        precision: Precision format string (e.g., "mxfp6.0")
    
    Returns:
        Numeric level (0-3), or -1 if unknown
    
    Examples:
        >>> precision_level("mxfp8.0")
        3
        >>> precision_level("mxfp4.12")
        0
        >>> precision_level("unknown")
        -1
    
    Note:
        Use this for safe precision comparison instead of string comparison.
        Higher level = higher precision.
    """
    return PRECISION_LEVELS.get(precision, -1)


def assign_precision(score: float) -> str:
    """Assign bit-envelope precision based on node score
    
    Args:
        score: Node relevance score [0.0, 1.0]
    
    Returns:
        Precision format string (mxfp4.12 - mxfp8.0)
    
    Examples:
        >>> assign_precision(0.85)
        'mxfp8.0'
        >>> assign_precision(0.65)
        'mxfp6.0'
        >>> assign_precision(0.45)
        'mxfp5.25'
        >>> assign_precision(0.10)
        'mxfp4.12'
    
    Note:
        Phase A uses simple step function.
        Future: Add hysteresis to prevent oscillation.
    """
    if score >= 0.80:
        return "mxfp8.0"   # hot - highest precision
    if score >= 0.60:
        return "mxfp6.0"   # warm-high
    if score >= 0.40:
        return "mxfp5.25"  # warm-low
    return "mxfp4.12"      # cold - global default
