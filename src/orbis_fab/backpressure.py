"""FAB Backpressure Classification - Phase A MVP

Token-bucket based backpressure control.

Bands:
- ok: tokens < threshold_ok (2000) - normal operation
- slow: threshold_ok ≤ tokens < threshold_reject (5000) - degraded
- reject: tokens ≥ threshold_reject (5000) - reject new requests

Used by FABCore to throttle fill() operations and prevent overload.

Invariants:
- Thresholds are fixed per deployment
- Classification is pure function (no state)
- Future: token-bucket with refill rate
"""


def classify_backpressure(
    tokens: int, threshold_ok: int = 2000, threshold_reject: int = 5000
) -> str:
    """Classify backpressure based on token count

    Args:
        tokens: Current token count in context
        threshold_ok: Normal operation threshold (default: 2000)
        threshold_reject: Rejection threshold (default: 5000)

    Returns:
        "ok" | "slow" | "reject"

    Examples:
        >>> classify_backpressure(1000)
        'ok'
        >>> classify_backpressure(3000)
        'slow'
        >>> classify_backpressure(6000)
        'reject'
    """
    if tokens >= threshold_reject:
        return "reject"
    if tokens >= threshold_ok:
        return "slow"
    return "ok"
