"""
AURIS Phase C — SELF Integration Hook with Canary Gate.

Provides safe SELF activation in FABCore with controlled rollout:
- Canary sampling (5% → 25% → 100%)
- Zero impact when AURIS_SELF=off (default)
- Metrics export for monitoring

Usage in FABCore.step_stub():
    from orbis_self.phase_c_hook_exp import maybe_self_tick

    # Inside step_stub() after FAB logic:
    maybe_self_tick(fab_core=self)

Environment Variables:
    AURIS_SELF: on/off (master switch, default: off)
    AURIS_SELF_CANARY: 0.0-1.0 (rollout percentage, default: 0.05)

Phase: C (experimental)
Status: Ready for staging smoke (2025-11-04)
"""

import logging
import os
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from orbis_fab.core import FABCore

logger = logging.getLogger(__name__)


def maybe_self_tick(fab_core: "FABCore") -> bool:
    """
    Execute SELF tick with canary gate protection.

    Args:
        fab_core: FABCore instance (provides st.metrics["stress"] for scoring)

    Returns:
        True if SELF tick was executed
        False if skipped (master switch off or canary gate blocked)

    Side Effects:
        - Updates SelfManager token (if activated)
        - Writes heartbeat to identity.jsonl (every 50 ticks)
        - Increments resonance metrics (if AURIS_METRICS_EXP=on)

    Thread Safety:
        Safe for single-threaded FABCore execution.
        Not tested for concurrent calls.
    """
    # Import guard: only import when master switch ON
    if os.getenv("AURIS_SELF", "off").lower() != "on":
        return False

    # Import inside guard to avoid circular deps + minimize footprint
    from orbis_self.canary_exp import should_activate_self
    from orbis_self.manager import SelfManager

    # Canary gate: probabilistic sampling
    if not should_activate_self():
        return False

    # Lazy initialization of SelfManager (singleton pattern)
    manager = _get_or_create_manager()

    # Extract SELF token (create if not exists)
    token_id = _get_or_create_token(manager)

    # Update token metrics from FABCore
    try:
        stress = fab_core.st.metrics.get("stress", 0.5)
        # Convert stress to coherence (inverse relationship)
        coherence = 1.0 - stress
        # Placeholder continuity (will be computed from token history later)
        continuity = 0.95

        manager.update(
            token_id=token_id,
            coherence=coherence,
            continuity=continuity,
            presence=1.0,  # Active in current tick
        )

        # Export SELF metrics to Prometheus (best-effort, fail-safe)
        try:
            # Import inside to avoid circular dependencies
            from atlas.metrics.exp_prom_exporter import update_self_metrics

            update_self_metrics(
                token_id=token_id,
                coherence=coherence,
                continuity=continuity,
                presence=1.0,
                stress=stress,
            )
        except Exception:
            # Best-effort: do not fail tick if metrics exporter unavailable
            pass

        # Heartbeat every 50 ticks
        manager.heartbeat(token_id=token_id, every_n=50)

        return True

    except Exception as e:
        logger.warning("SELF tick failed: %s", e, exc_info=True)
        return False


# ════════════════════════════════════════════════════════════════════════
# Internal Helpers (not part of public API)
# ════════════════════════════════════════════════════════════════════════

_manager_singleton: Optional["SelfManager"] = None
_token_singleton: Optional[str] = None


def _get_or_create_manager():
    """Get or create global SelfManager instance."""
    global _manager_singleton
    if _manager_singleton is None:
        from orbis_self.manager import SelfManager

        _manager_singleton = SelfManager()
        logger.info("SELF manager initialized (Phase C canary)")
    return _manager_singleton


def _get_or_create_token(manager: "SelfManager") -> str:
    """Get or create SELF token for this session."""
    global _token_singleton
    if _token_singleton is None:
        # Mint new token with initial scores
        _token_singleton = manager.mint(
            coherence=0.8,
            continuity=0.9,
            presence=1.0,
        )
        logger.info("SELF token minted: %s (Phase C canary)", _token_singleton)
    return _token_singleton


def reset_singletons() -> None:
    """
    Reset global state (for testing only).

    WARNING: This should NEVER be called in production.
    Only use in test teardown.
    """
    global _manager_singleton, _token_singleton
    _manager_singleton = None
    _token_singleton = None
