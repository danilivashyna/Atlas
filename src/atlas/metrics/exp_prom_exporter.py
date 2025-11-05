"""
Experimental Prometheus Exporter (Phase B.3 + B.1)

Собирает метрики из StabilityTracker и Hysteresis компонентов
для экспорта в Prometheus. Изолировано от основного metrics модуля.

Feature flag: AURIS_METRICS_EXP=on

Metrics exported:

Stability (B.3):
- stability_score: instantaneous stability [0.0, 1.0]
- stability_score_ema: exponential moving average [0.0, 1.0]
- degradation_events_per_hour: events/h in last hour
- recommended_fab_mode: 0=FAB0, 1=FAB1, 2=FAB2
- stable_ticks: consecutive stable ticks
- degradation_count: total degradation events

Hysteresis (B.1):
- hyst_switch_rate_per_sec: mode switches per second
- hyst_oscillation_rate_per_sec: oscillations per second
- hyst_dwell_counter: ticks holding desired mode
- hyst_last_switch_age: ticks since last switch
- hyst_effective_mode: effective mode after hysteresis (0/1/2)
- hyst_desired_mode: desired mode from B2 (0/1/2)

Usage:
    # Register metrics
    registry = setup_prometheus_metrics()

    # Update from StabilityTracker
    update_stability_metrics(tracker, window_id="global")

    # Update from Hysteresis
    update_hysteresis_metrics(metrics_dict, window_id="global")

    # Expose via HTTP
    from prometheus_client import generate_latest
    metrics_output = generate_latest(registry)
"""

import os
from typing import Optional

try:
    from prometheus_client import (
        CollectorRegistry,
        Gauge,
        Counter,
        generate_latest,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

    # Stub classes for when prometheus_client not installed
    class CollectorRegistry:
        """Stub for prometheus_client.CollectorRegistry."""

    class Gauge:
        """Stub for prometheus_client.Gauge."""

        def __init__(self, *args, **kwargs):
            """Stub init."""

        def labels(self, **kwargs):
            """Stub labels."""
            return self

        def set(self, value):
            """Stub set."""

    class Counter:
        """Stub for prometheus_client.Counter."""

        def __init__(self, *args, **kwargs):
            """Stub init."""

        def labels(self, **kwargs):
            """Stub labels."""
            return self

        def inc(self, amount=1):
            """Stub inc."""


# Feature flag check
METRICS_ENABLED = os.getenv("AURIS_METRICS_EXP", "off").lower() in (
    "on",
    "true",
    "1",
)

# Global registry
_registry: Optional[CollectorRegistry] = None

# Prometheus metrics (initialized in setup_prometheus_metrics)
_stability_score: Optional[Gauge] = None
_stability_score_ema: Optional[Gauge] = None
_degradation_events_per_hour: Optional[Gauge] = None
_recommended_fab_mode: Optional[Gauge] = None
_stable_ticks: Optional[Gauge] = None
_degradation_count: Optional[Counter] = None

# Hysteresis metrics (Phase B.1)
_hyst_switch_rate: Optional[Gauge] = None
_hyst_oscillation_rate: Optional[Gauge] = None
_hyst_dwell_counter: Optional[Gauge] = None
_hyst_last_switch_age: Optional[Gauge] = None
_hyst_effective_mode: Optional[Gauge] = None
_hyst_desired_mode: Optional[Gauge] = None

# SELF metrics (Phase C)
_self_coherence: Optional[Gauge] = None
_self_continuity: Optional[Gauge] = None
_self_presence: Optional[Gauge] = None
_self_stress: Optional[Gauge] = None


def is_enabled() -> bool:
    """Check if experimental metrics are enabled."""
    return METRICS_ENABLED and PROMETHEUS_AVAILABLE


def setup_prometheus_metrics() -> Optional[CollectorRegistry]:
    """
    Setup Prometheus metrics registry and gauges.

    Returns:
        CollectorRegistry instance or None if disabled

    Raises:
        ImportError: if prometheus_client not installed and metrics enabled
    """
    global _registry
    global _stability_score
    global _stability_score_ema
    global _degradation_events_per_hour
    global _recommended_fab_mode
    global _stable_ticks
    global _degradation_count
    global _hyst_switch_rate
    global _hyst_oscillation_rate
    global _hyst_dwell_counter
    global _hyst_last_switch_age
    global _hyst_effective_mode
    global _hyst_desired_mode
    global _self_coherence
    global _self_continuity
    global _self_presence
    global _self_stress

    if not METRICS_ENABLED:
        return None

    if not PROMETHEUS_AVAILABLE:
        raise ImportError(
            "prometheus_client not installed. " "Install with: pip install prometheus-client"
        )

    # Create registry
    _registry = CollectorRegistry()

    # Stability metrics
    _stability_score = Gauge(
        "atlas_stability_score",
        "Instantaneous stability score [0.0, 1.0]",
        ["window_id"],
        registry=_registry,
    )

    _stability_score_ema = Gauge(
        "atlas_stability_score_ema",
        "Exponential moving average of stability score [0.0, 1.0]",
        ["window_id"],
        registry=_registry,
    )

    _degradation_events_per_hour = Gauge(
        "atlas_degradation_events_per_hour",
        "Degradation events in last hour",
        ["window_id"],
        registry=_registry,
    )

    _recommended_fab_mode = Gauge(
        "atlas_recommended_fab_mode",
        "Recommended FAB mode (0=FAB0, 1=FAB1, 2=FAB2)",
        ["window_id"],
        registry=_registry,
    )

    _stable_ticks = Gauge(
        "atlas_stable_ticks",
        "Consecutive stable ticks",
        ["window_id"],
        registry=_registry,
    )

    _degradation_count = Counter(
        "atlas_degradation_count_total",
        "Total degradation events",
        ["window_id"],
        registry=_registry,
    )

    # Hysteresis metrics (Phase B.1)
    _hyst_switch_rate = Gauge(
        "atlas_hyst_switch_rate_per_sec",
        "Mode switch rate (switches per second)",
        ["window_id"],
        registry=_registry,
    )

    _hyst_oscillation_rate = Gauge(
        "atlas_hyst_oscillation_rate_per_sec",
        "Oscillation rate (oscillations per second)",
        ["window_id"],
        registry=_registry,
    )

    _hyst_dwell_counter = Gauge(
        "atlas_hyst_dwell_counter",
        "Current dwell counter (ticks holding desired mode)",
        ["window_id"],
        registry=_registry,
    )

    _hyst_last_switch_age = Gauge(
        "atlas_hyst_last_switch_age",
        "Ticks since last mode switch",
        ["window_id"],
        registry=_registry,
    )

    _hyst_effective_mode = Gauge(
        "atlas_hyst_effective_mode",
        "Effective FAB mode after hysteresis (0=FAB0, 1=FAB1, 2=FAB2)",
        ["window_id"],
        registry=_registry,
    )

    _hyst_desired_mode = Gauge(
        "atlas_hyst_desired_mode",
        "Desired FAB mode from stability tracker (0=FAB0, 1=FAB1, 2=FAB2)",
        ["window_id"],
        registry=_registry,
    )

    # SELF metrics (Phase C)
    _self_coherence = Gauge(
        "self_coherence",
        "SELF coherence score [0.0, 1.0]",
        ["token_id"],
        registry=_registry,
    )

    _self_continuity = Gauge(
        "self_continuity",
        "SELF continuity score [0.0, 1.0]",
        ["token_id"],
        registry=_registry,
    )

    _self_presence = Gauge(
        "self_presence",
        "SELF presence score [0.0, 1.0]",
        ["token_id"],
        registry=_registry,
    )

    _self_stress = Gauge(
        "self_stress",
        "SELF stress metric [0.0, 1.0] (lower is better)",
        ["token_id"],
        registry=_registry,
    )

    return _registry


def update_stability_metrics(tracker, window_id: str = "global") -> None:
    """
    Update Prometheus metrics from StabilityTracker instance.

    Args:
        tracker: StabilityTracker instance (from src/orbis_fab/stability.py)
        window_id: Window identifier (e.g., "global", "stream")
    """
    if not is_enabled():
        return

    # Get comprehensive metrics
    metrics = tracker.get_metrics()

    # Update gauges
    _stability_score.labels(window_id=window_id).set(metrics["stability_score"])
    _stability_score_ema.labels(window_id=window_id).set(metrics["stability_score_ema"])
    _degradation_events_per_hour.labels(window_id=window_id).set(
        metrics["degradation_events_per_hour"]
    )

    # Convert mode string to numeric (for Grafana)
    mode_map = {"FAB0": 0, "FAB1": 1, "FAB2": 2}
    mode_numeric = mode_map.get(metrics["recommended_mode"], 0)
    _recommended_fab_mode.labels(window_id=window_id).set(mode_numeric)

    _stable_ticks.labels(window_id=window_id).set(metrics["stable_ticks"])

    # Note: Counter only increments, so we track delta
    # (In production, would need to track last_count to compute delta)


def get_metrics_text() -> str:
    """
    Get Prometheus metrics in text format (for HTTP endpoint).

    Returns:
        Metrics in Prometheus exposition format
    """
    if not is_enabled() or _registry is None:
        return "# Metrics disabled (AURIS_METRICS_EXP=off)\n"

    return generate_latest(_registry).decode("utf-8")


def update_hysteresis_metrics(metrics_dict: dict, window_id: str = "global") -> None:
    """
    Update Prometheus metrics from hysteresis results.

    Args:
        metrics_dict: Dict from maybe_hyst() containing:
            - switch_rate_per_sec: float
            - oscillation_rate_per_sec: float
            - dwell_counter: int
            - last_switch_age: int
            - effective_mode: str (FAB0/FAB1/FAB2)
            - desired_mode: str (FAB0/FAB1/FAB2)
        window_id: Window identifier (e.g., "global")
    """
    if not is_enabled():
        return

    # Mode string to numeric conversion
    mode_map = {"FAB0": 0, "FAB1": 1, "FAB2": 2}

    # Update hysteresis gauges
    _hyst_switch_rate.labels(window_id=window_id).set(metrics_dict.get("switch_rate_per_sec", 0.0))
    _hyst_oscillation_rate.labels(window_id=window_id).set(
        metrics_dict.get("oscillation_rate_per_sec", 0.0)
    )
    _hyst_dwell_counter.labels(window_id=window_id).set(metrics_dict.get("dwell_counter", 0))
    _hyst_last_switch_age.labels(window_id=window_id).set(metrics_dict.get("last_switch_age", 0))

    # Convert mode strings to numeric
    effective_mode_numeric = mode_map.get(metrics_dict.get("effective_mode", "FAB2"), 2)
    desired_mode_numeric = mode_map.get(metrics_dict.get("desired_mode", "FAB2"), 2)

    _hyst_effective_mode.labels(window_id=window_id).set(effective_mode_numeric)
    _hyst_desired_mode.labels(window_id=window_id).set(desired_mode_numeric)


def update_self_metrics(
    token_id: str,
    *,
    coherence: float,
    continuity: float,
    presence: float,
    stress: float,
) -> None:
    """
    Update SELF-related Prometheus metrics.

    Args:
        token_id: Token identifier (e.g., "global", "fab-default")
        coherence: SELF coherence score [0.0, 1.0]
        continuity: SELF continuity score [0.0, 1.0]
        presence: SELF presence score [0.0, 1.0]
        stress: SELF stress metric [0.0, 1.0] (lower is better)

    Note:
        Safe to call even if Prometheus client is stubbed/missing.
        No-op if AURIS_METRICS_EXP=off.
    """
    if not is_enabled():
        return

    # Update SELF gauges
    if _self_coherence is not None:
        _self_coherence.labels(token_id=token_id).set(coherence)
    if _self_continuity is not None:
        _self_continuity.labels(token_id=token_id).set(continuity)
    if _self_presence is not None:
        _self_presence.labels(token_id=token_id).set(presence)
    if _self_stress is not None:
        _self_stress.labels(token_id=token_id).set(stress)
