"""
Stability Hook (Experimental) - Phase B.2 Runtime Integration

Фасад для подключения StabilityTracker к FABCore без изменения core.py.
Lazy initialization, минимальный контракт с FAB.

Feature flag: AURIS_STABILITY_HOOK=on

Usage:
    from orbis_fab.stability_hook_exp import attach, maybe_tick

    # Attach to FABCore
    tracker, tick_fn = attach(fab_core, decay=0.95)

    # Each FAB cycle
    maybe_tick(fab_core, tracker, window_id="global")

    # Get metrics
    metrics = tracker.get_metrics()
    print(f"EMA: {metrics['stability_score_ema']:.3f}")
    print(f"Mode: {metrics['recommended_mode']}")
"""

import os
import logging
from typing import Tuple, Optional, Any

logger = logging.getLogger(__name__)

# Feature flag
HOOK_ENABLED = os.getenv("AURIS_STABILITY_HOOK", "off").lower() in (
    "on",
    "true",
    "1",
)


def is_enabled() -> bool:
    """Check if stability hook is enabled."""
    return HOOK_ENABLED


def attach_to_fab(fab_core: Any) -> Optional[Any]:
    """
    Attach StabilityTracker to FABCore (single entry point for production).

    Args:
        fab_core: FABCore instance

    Returns:
        StabilityTracker instance if enabled, None otherwise

    Example:
        tracker = attach_to_fab(fab_core)
        if tracker:
            metrics = maybe_tick(fab_core, tracker)
    """
    if not is_enabled():
        return None

    # Lazy import to avoid circular dependencies
    from orbis_fab.stability import StabilityTracker, StabilityConfig

    # Production config: higher min_stable_ticks, moderate decay
    config = StabilityConfig(
        min_stable_ticks=100,  # Longer stabilization period
        ema_decay=0.95,  # Moderate EMA smoothing
        cooldown_base=2.0,
        cooldown_max_ticks=10000,
        degradation_threshold=0.1,
    )

    # Create tracker
    tracker = StabilityTracker(config=config)

    logger.info("StabilityTracker attached to FABCore (production config)")

    return tracker


def attach(
    fab_core: Any, *, decay: float = 0.95, min_stable_ticks: int = 100
) -> Optional[Tuple[Any, Any]]:
    """
    Attach StabilityTracker to FABCore instance (legacy API for tests).

    Args:
        fab_core: FABCore instance (любой объект, не используется пока)
        decay: EMA decay factor (default 0.95)
        min_stable_ticks: Minimum ticks for stable status (default 100)

    Returns:
        (tracker, tick_fn) tuple if enabled, None otherwise

    Example:
        tracker, tick_fn = attach(fab_core)
        if tracker:
            tick_fn()  # Update tracker each cycle
    """
    if not is_enabled():
        return None

    # Lazy import to avoid circular dependencies
    from orbis_fab.stability import StabilityTracker, StabilityConfig

    # Create config
    config = StabilityConfig(
        min_stable_ticks=min_stable_ticks,
        ema_decay=decay,
        cooldown_base=2.0,
        cooldown_max_ticks=10000,
        degradation_threshold=0.1,
    )

    # Create tracker
    tracker = StabilityTracker(config=config)

    # Create tick function (closure over fab_core)
    def tick_fn(window_id: str = "global"):
        """Tick tracker based on FAB state"""
        # Extract state from FABCore (minimal contract)
        current_score = extract_fab_score(fab_core)
        degraded = detect_degradation(fab_core)

        # Tick tracker
        tracker.tick(current_score=current_score, degraded=degraded)

        return tracker.get_metrics()

    logger.info("StabilityTracker attached to FABCore (decay=%s)", decay)

    return tracker, tick_fn


def maybe_tick(
    fab_core: Any,
    tracker: Any,
    window_id: str = "global",
    *,
    tick_interval: int = 1,
) -> Optional[dict]:
    """
    Conditionally tick StabilityTracker based on FABCore state.

    Args:
        fab_core: FABCore instance
        tracker: StabilityTracker instance (from attach_to_fab())
        window_id: Window identifier (e.g., "global", "stream")
        tick_interval: Tick every N calls (default 1 = every call)

    Returns:
        Metrics dict if enabled and ticked, None otherwise

    Example:
        # In FABCore.step_stub():
        if self._stability is not None:
            metrics = maybe_tick(self, self._stability)
            self._last_stability = metrics
    """
    if not is_enabled() or tracker is None:
        return None

    # Extract FAB tick counter (if available)
    fab_tick = getattr(fab_core, "current_tick", 0)

    # Check tick interval
    if fab_tick % tick_interval != 0:
        return None

    # Extract state from FABCore (enriched for production)
    current_score = extract_fab_score(fab_core)
    degraded = detect_degradation(fab_core)

    # Tick tracker
    tracker.tick(current_score=current_score, degraded=degraded)

    # Update Prometheus metrics if available
    try:
        from atlas.metrics.exp_prom_exporter import (
            update_stability_metrics,
            is_enabled as metrics_enabled,
        )

        if metrics_enabled():
            update_stability_metrics(tracker, window_id=window_id)
    except Exception:  # pylint: disable=broad-exception-caught
        pass  # Metrics optional, don't fail

    # Return metrics
    return tracker.get_metrics()


def extract_fab_score(fab_core: Any) -> float:
    """
    Extract current score from FABCore (minimal contract).

    Args:
        fab_core: FABCore instance

    Returns:
        Current score [0.0, 1.0] (default 0.8 if not available)

    Implementation:
        Tries to extract:
        1. fab_core.st.metrics["stress"] → convert to score (1.0 - stress)
        2. fab_core.coherence_score
        3. fab_core.quality_score
        4. Default: 0.8
    """
    # Try FABCore metrics (1.0 - stress as score proxy)
    try:
        metrics = getattr(fab_core, "st", None)
        if metrics is not None:
            st_metrics = getattr(metrics, "metrics", {})
            stress = st_metrics.get("stress", None)
            if stress is not None:
                return float(1.0 - stress)
    except Exception:  # pylint: disable=broad-exception-caught
        pass

    # Try coherence_score
    coherence = getattr(fab_core, "coherence_score", None)
    if coherence is not None:
        return float(coherence)

    # Try quality_score
    quality = getattr(fab_core, "quality_score", None)
    if quality is not None:
        return float(quality)

    # Default: assume reasonable quality
    return 0.8


def detect_degradation(fab_core: Any) -> bool:
    """
    Detect degradation event from FABCore state.

    Args:
        fab_core: FABCore instance

    Returns:
        True if degradation detected, False otherwise

    Implementation:
        Checks for:
        1. fab_core.degraded flag
        2. fab_core.mode change to lower precision
        3. Default: False (no degradation)
    """
    # Explicit degraded flag
    degraded = getattr(fab_core, "degraded", None)
    if degraded is not None:
        return bool(degraded)

    # Mode degradation (FAB2 → FAB1 → FAB0)
    mode = getattr(fab_core, "mode", None)
    prev_mode = getattr(fab_core, "_prev_mode", None)

    if mode is not None and prev_mode is not None:
        mode_order = {"FAB2": 2, "FAB1": 1, "FAB0": 0}
        current_level = mode_order.get(mode, 1)
        prev_level = mode_order.get(prev_mode, 1)

        # Degradation = mode level decreased
        if current_level < prev_level:
            return True

    # Default: no degradation
    return False
