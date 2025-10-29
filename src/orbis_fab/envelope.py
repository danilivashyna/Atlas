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
