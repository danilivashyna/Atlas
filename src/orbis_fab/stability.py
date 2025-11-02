"""
Window Stability Counter (Phase B.2)

Tracks stability metrics for FAB windows to prevent mode oscillations:
- Stable ticks counter (consecutive ticks without degradation)
- Exponential cool-down after degradation events
- Stability score computation

Usage:
    config = StabilityConfig(
        min_stable_ticks=100,      # Ticks needed for "stable" status
        cooldown_base=2.0,          # Exponential base for cool-down
        cooldown_max_ticks=10000    # Max cool-down duration
    )

    tracker = StabilityTracker(config=config)

    # Each tick: update stability
    tracker.tick(degraded=False)  # Increment stable counter
    tracker.tick(degraded=True)   # Reset counter, enter cool-down

    # Check stability status
    if tracker.is_stable():
        # Allow mode transitions
        pass
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StabilityConfig:
    """Configuration for window stability tracking"""

    min_stable_ticks: int = 100
    """Minimum consecutive stable ticks to achieve 'stable' status"""

    cooldown_base: float = 2.0
    """Exponential base for cool-down period calculation (2.0 = doubles each time)"""

    cooldown_max_ticks: int = 10000
    """Maximum cool-down duration in ticks (~10 seconds at 1000 ticks/sec)"""

    degradation_threshold: float = 0.1
    """Score drop threshold to trigger degradation event (10% drop)"""


@dataclass
class StabilityState:
    """Current stability state for a window"""

    stable_ticks: int = 0
    """Consecutive ticks without degradation"""

    degradation_count: int = 0
    """Total number of degradation events (for exponential cool-down)"""

    cooldown_remaining: int = 0
    """Ticks remaining in current cool-down period"""

    last_score: Optional[float] = None
    """Last observed score (for degradation detection)"""

    is_in_cooldown: bool = False
    """Whether currently in cool-down period"""


@dataclass
class StabilityTracker:
    """Tracks stability metrics for a single window"""

    config: StabilityConfig = field(default_factory=StabilityConfig)
    state: StabilityState = field(default_factory=StabilityState)

    def tick(self, current_score: float, degraded: bool = False) -> None:
        """
        Update stability state for one tick.

        Args:
            current_score: Current window score (e.g., coherence, relevance)
            degraded: Explicit degradation signal (optional, auto-detected from score drop)

        Effects:
            - Increments stable_ticks if no degradation
            - Resets stable_ticks and enters cool-down on degradation
            - Decrements cooldown_remaining if in cool-down
        """
        # Auto-detect degradation from score drop
        if self.state.last_score is not None and not degraded:
            score_drop = self.state.last_score - current_score
            if score_drop >= self.config.degradation_threshold:
                degraded = True

        self.state.last_score = current_score

        # Handle cool-down countdown
        if self.state.is_in_cooldown:
            self.state.cooldown_remaining -= 1
            if self.state.cooldown_remaining <= 0:
                self.state.is_in_cooldown = False
                self.state.cooldown_remaining = 0

        # Handle degradation event
        if degraded:
            # Reset stable ticks
            self.state.stable_ticks = 0

            # Increment degradation count
            self.state.degradation_count += 1

            # Calculate exponential cool-down duration
            cooldown_ticks = min(
                int(self.config.cooldown_base**self.state.degradation_count),
                self.config.cooldown_max_ticks,
            )

            # Enter cool-down
            self.state.cooldown_remaining = cooldown_ticks
            self.state.is_in_cooldown = True
        else:
            # No degradation: increment stable ticks (if not in cool-down)
            if not self.state.is_in_cooldown:
                self.state.stable_ticks += 1

    def is_stable(self) -> bool:
        """
        Check if window is currently stable.

        Returns:
            True if stable_ticks >= min_stable_ticks and not in cool-down
        """
        return (
            not self.state.is_in_cooldown
            and self.state.stable_ticks >= self.config.min_stable_ticks
        )

    def stability_score(self) -> float:
        """
        Compute stability score [0.0, 1.0].

        Returns:
            0.0 = unstable (in cool-down or low stable_ticks)
            1.0 = fully stable (stable_ticks >= min_stable_ticks)

        Formula:
            - If in cool-down: 0.0
            - Else: min(1.0, stable_ticks / min_stable_ticks)
        """
        if self.state.is_in_cooldown:
            return 0.0

        ratio = self.state.stable_ticks / max(self.config.min_stable_ticks, 1)
        return min(1.0, ratio)

    def reset(self) -> None:
        """Reset stability state (for testing or manual intervention)"""
        self.state = StabilityState()

    def get_cooldown_info(self) -> dict:
        """
        Get current cool-down status (for diagnostics).

        Returns:
            Dict with keys: is_in_cooldown, cooldown_remaining, degradation_count
        """
        return {
            "is_in_cooldown": self.state.is_in_cooldown,
            "cooldown_remaining": self.state.cooldown_remaining,
            "degradation_count": self.state.degradation_count,
            "stable_ticks": self.state.stable_ticks,
        }
