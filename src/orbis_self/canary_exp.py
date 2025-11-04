"""
AURIS Phase C — Canary Gate (Experimental Feature)

Provides controlled sampling for SELF activation to minimize production risk.
Allows gradual rollout (5% → 25% → 100%) with feature flag protection.

Environment Variables:
    AURIS_SELF: on/off (master switch for SELF activation)
    AURIS_SELF_CANARY: 0.0-1.0 (percentage of ticks to activate SELF)
                       Default: 0.05 (5%)
                       Examples:
                         0.05 → 5% canary (1 in 20 ticks)
                         0.25 → 25% partial rollout
                         1.00 → 100% full activation

Usage:
    from orbis_self.canary_exp import should_activate_self

    if should_activate_self():
        # Execute SELF tick (token update, heartbeat, bridge sync)
        pass
    else:
        # Skip SELF logic (zero impact on core)
        pass

SLO Targets (for canary validation):
    - coherence ≥ 0.80
    - continuity ≥ 0.90
    - stress ≤ 0.30

Auto-Rollback Conditions:
    If 2+ metrics fail for ≥5 minutes:
    - stability_score_ema < 0.5
    - atlas_hysteresis_oscillation_rate > 1.0
    - self_stress > 0.4 (if exported)
    → export AURIS_SELF=off; restart service

Phase: C (experimental)
Status: Ready for staging smoke (2025-11-04)
"""

import os
import random
from typing import Optional


class CanaryConfig:
    """Configuration for SELF canary deployment."""

    def __init__(self) -> None:
        self.enabled: bool = os.getenv("AURIS_SELF", "off").lower() == "on"
        self.percentage: float = self._parse_percentage()

    def _parse_percentage(self) -> float:
        """Parse AURIS_SELF_CANARY env var with validation."""
        try:
            raw = os.getenv("AURIS_SELF_CANARY", "0.05")
            value = float(raw)
            # Clamp to [0.0, 1.0]
            if value < 0.0:
                return 0.0
            if value > 1.0:
                return 1.0
            return value
        except (ValueError, TypeError):
            # Default to 5% on parse error
            return 0.05

    def __repr__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        return f"CanaryConfig({status}, {self.percentage:.1%})"


# Global config instance (initialized once at module load)
_config: Optional[CanaryConfig] = None


def get_config() -> CanaryConfig:
    """Get or create global canary configuration."""
    global _config
    if _config is None:
        _config = CanaryConfig()
    return _config


def should_activate_self() -> bool:
    """
    Canary gate: determines if SELF should activate for this tick.

    Returns:
        True if SELF should activate (master switch ON + passed sampling)
        False otherwise (zero impact on core)

    Examples:
        >>> os.environ["AURIS_SELF"] = "on"
        >>> os.environ["AURIS_SELF_CANARY"] = "0.05"
        >>> # ~5% of calls return True
        >>> sum(should_activate_self() for _ in range(1000)) / 10
        5.2  # approximately 5%

        >>> os.environ["AURIS_SELF"] = "off"
        >>> should_activate_self()
        False  # always False when master switch off
    """
    config = get_config()

    # Master switch OFF → always skip
    if not config.enabled:
        return False

    # Master switch ON but 0% canary → skip
    if config.percentage <= 0.0:
        return False

    # 100% canary → always activate
    if config.percentage >= 1.0:
        return True

    # Probabilistic sampling (thread-safe via random module)
    try:
        return random.random() < config.percentage
    except Exception:
        # Fail closed: on error, skip SELF activation
        return False


def get_canary_percentage() -> float:
    """Get current canary percentage (for metrics/logging)."""
    return get_config().percentage


def is_canary_enabled() -> bool:
    """Check if SELF canary is enabled (AURIS_SELF=on)."""
    return get_config().enabled


# Metrics helpers (for Prometheus export if needed)
def canary_sampling_rate() -> float:
    """Current canary sampling rate [0.0, 1.0]."""
    config = get_config()
    return config.percentage if config.enabled else 0.0


def canary_status() -> str:
    """Human-readable canary status."""
    config = get_config()
    if not config.enabled:
        return "disabled (AURIS_SELF=off)"
    if config.percentage >= 1.0:
        return "full activation (100%)"
    if config.percentage <= 0.0:
        return "enabled but 0% (effectively off)"
    return f"canary {config.percentage:.1%}"
