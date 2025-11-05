"""
Hysteresis Hook (Experimental) - Phase B.1 FABCore Integration

Connects B2 StabilityTracker recommend_mode() → B1 Hysteresis → effective_mode.

Feature flag: AURIS_HYSTERESIS=on

Usage:
    from orbis_fab.hysteresis_hook_exp import attach_to_fab, maybe_hyst

    # In FABCore.__init__:
    self._hyst = attach_to_fab(self)

    # In FABCore.step_stub():
    if self._hyst:
        metrics = maybe_hyst(self)
        # metrics = {desired_mode, effective_mode, switch_rate, ...}
"""

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Feature flag
HYSTERESIS_ENABLED = os.getenv("AURIS_HYSTERESIS", "off").lower() in (
    "on",
    "true",
    "1",
)


def is_enabled() -> bool:
    """Check if hysteresis hook is enabled."""
    return HYSTERESIS_ENABLED


def attach_to_fab(fab_core: Any) -> Optional[Any]:
    """
    Attach BitEnvelopeHysteresisExp to FABCore.

    Args:
        fab_core: FABCore instance

    Returns:
        BitEnvelopeHysteresisExp instance if enabled, None otherwise

    Example:
        hyst = attach_to_fab(fab_core)
        if hyst:
            metrics = maybe_hyst(fab_core)
    """
    if not is_enabled():
        return None

    # Lazy import to avoid circular dependencies
    from orbis_fab.hysteresis_exp import BitEnvelopeHysteresisExp, HysteresisConfig

    # Production config: moderate dwell, strict rate limit
    config = HysteresisConfig(
        dwell_ticks=50,  # Hold desired mode for 50 ticks before switch
        rate_limit_ticks=1000,  # Min 1000 ticks (≈1 sec) between switches
        osc_window=300,  # Detect oscillations within 300 ticks
        max_history=5000,  # Keep up to 5000 switch events
    )

    # Create hysteresis instance
    hyst = BitEnvelopeHysteresisExp(config)

    logger.info("BitEnvelopeHysteresisExp attached to FABCore (production config)")

    return hyst


def maybe_hyst(fab_core: Any) -> Optional[dict]:
    """
    Apply hysteresis filtering to FABCore mode recommendation.

    Args:
        fab_core: FABCore instance

    Returns:
        Metrics dict if enabled, None otherwise
        Keys:
            - desired_mode: from B2 StabilityTracker (or FAB internal)
            - effective_mode: after hysteresis filtering
            - switch_rate_per_sec: hysteresis switch rate
            - oscillation_rate_per_sec: oscillation rate
            - dwell_counter: current dwell accumulator
            - last_switch_age: ticks since last switch
            - osc_count: total oscillation count

    Example:
        # In FABCore.step_stub():
        if self._hyst is not None:
            metrics = maybe_hyst(self)
            self._last_hyst = metrics
            # Now have desired vs effective mode for observability
    """
    if not is_enabled():
        return None

    # Extract hysteresis instance
    hyst = getattr(fab_core, "_hyst", None)
    if hyst is None:
        return None

    # Extract desired mode from B2 StabilityTracker (if available)
    desired_mode = extract_desired_mode(fab_core)

    # Extract current tick
    current_tick = getattr(fab_core, "current_tick", 0)

    # Apply hysteresis
    effective_mode = hyst.update(desired_mode=desired_mode, tick=current_tick)

    # Get hysteresis metrics
    hyst_metrics = hyst.get_metrics()

    # Combine with desired/effective
    result = {
        "desired_mode": desired_mode,
        "effective_mode": effective_mode,
        **hyst_metrics,
    }

    # Update Prometheus metrics if available
    try:
        from atlas.metrics.exp_prom_exporter import (
            update_hysteresis_metrics,
            is_enabled as metrics_enabled,
        )

        if metrics_enabled():
            update_hysteresis_metrics(result, window_id="global")
    except Exception:  # pylint: disable=broad-exception-caught
        pass  # Metrics optional, don't fail

    return result


def extract_desired_mode(fab_core: Any) -> str:
    """
    Extract desired mode from FABCore.

    Priority:
    1. B2 StabilityTracker recommend_mode() (if available)
    2. FABCore.st.mode (current mode)
    3. Default: "FAB2"

    Args:
        fab_core: FABCore instance

    Returns:
        Desired mode string (FAB0/FAB1/FAB2)
    """
    # Try B2 StabilityTracker recommendation
    try:
        stability_metrics = getattr(fab_core, "_last_stability", None)
        if stability_metrics and "recommended_mode" in stability_metrics:
            return stability_metrics["recommended_mode"]
    except Exception:  # pylint: disable=broad-exception-caught
        pass

    # Try FABCore current mode
    try:
        st = getattr(fab_core, "st", None)
        if st is not None:
            mode = getattr(st, "mode", None)
            if mode:
                return mode
    except Exception:  # pylint: disable=broad-exception-caught
        pass

    # Default: assume FAB2
    return "FAB2"
