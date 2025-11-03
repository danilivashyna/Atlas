"""
Window Stability Counter (Phase B.2)

Tracks stability metrics for FAB windows to prevent mode oscillations:
- Stable ticks counter (consecutive ticks without degradation)
- Exponential cool-down after degradation events
- Stability score computation
- EMA (exponential moving average) for stability_score
- Degradation events tracking with hourly rate

Usage:
    config = StabilityConfig(
        min_stable_ticks=100,      # Ticks needed for "stable" status
        cooldown_base=2.0,          # Exponential base for cool-down
        cooldown_max_ticks=10000,   # Max cool-down duration
        ema_decay=0.95              # EMA decay factor
    )

    tracker = StabilityTracker(config=config)

    # Each tick: update stability
    tracker.tick(degraded=False)  # Increment stable counter
    tracker.tick(degraded=True)   # Reset counter, enter cool-down

    # Check stability status
    if tracker.is_stable():
        # Allow mode transitions
        pass

    # Get EMA stability score
    ema_score = tracker.stability_score_ema()  # Smoothed [0.0, 1.0]

    # Get degradation rate
    events_per_hour = tracker.degradation_events_per_hour()  # events/h
"""

import time
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

    ema_decay: float = 0.95
    """EMA decay factor for stability_score_ema (0.95 = slow adaptation)"""


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

    stability_score_ema: float = 1.0
    """Exponential moving average of stability_score [0.0, 1.0]"""

    degradation_timestamps: list[float] = field(default_factory=list)
    """Timestamps of degradation events (for hourly rate calculation)"""


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
            - Updates stability_score_ema
            - Records degradation timestamps for hourly rate
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
            # Record timestamp for hourly rate calculation
            self.state.degradation_timestamps.append(time.time())

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

        # Update stability_score_ema
        current_stability = self.stability_score()
        self.state.stability_score_ema = (
            self.config.ema_decay * self.state.stability_score_ema
            + (1 - self.config.ema_decay) * current_stability
        )

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

    def get_stability_score_ema(self) -> float:
        """
        Get exponential moving average of stability_score.

        Returns:
            Smoothed stability score [0.0, 1.0]
        """
        return self.state.stability_score_ema

    def degradation_events_per_hour(self) -> float:
        """
        Calculate degradation events per hour (sliding 1h window).

        Returns:
            Number of degradation events in the last hour
        """
        now = time.time()
        one_hour_ago = now - 3600  # 1 hour = 3600 seconds

        # Filter timestamps within last hour
        recent_events = [ts for ts in self.state.degradation_timestamps if ts >= one_hour_ago]

        # Update state (cleanup old timestamps)
        self.state.degradation_timestamps = recent_events

        return float(len(recent_events))

    def should_degrade(self, threshold: float = 0.5) -> bool:
        """
        Check if FAB mode should degrade based on stability_score_ema.

        Args:
            threshold: EMA threshold for degradation (default 0.5)

        Returns:
            True if stability_score_ema < threshold
        """
        return self.state.stability_score_ema < threshold

    def recommend_mode(self) -> str:
        """
        Recommend FAB mode based on stability_score_ema.

        Returns:
            "FAB2" (ema >= 0.8) - full precision
            "FAB1" (0.5 <= ema < 0.8) - degraded precision
            "FAB0" (ema < 0.5) - safe mode
        """
        ema = self.state.stability_score_ema

        if ema >= 0.8:
            return "FAB2"
        if ema >= 0.5:
            return "FAB1"
        return "FAB0"

    def reset(self) -> None:
        """Reset stability state (for testing or manual intervention)"""
        self.state = StabilityState()

    def get_metrics(self) -> dict:
        """
        Get comprehensive stability metrics (for diagnostics and Prometheus).

        Returns:
            Dict with keys:
                - stability_score: current instantaneous score [0.0, 1.0]
                - stability_score_ema: EMA smoothed score [0.0, 1.0]
                - degradation_events_per_hour: events/h in last hour
                - is_in_cooldown: bool
                - cooldown_remaining: ticks
                - degradation_count: total events
                - stable_ticks: consecutive stable ticks
                - recommended_mode: "FAB0" | "FAB1" | "FAB2"
        """
        return {
            "stability_score": self.stability_score(),
            "stability_score_ema": self.state.stability_score_ema,
            "degradation_events_per_hour": self.degradation_events_per_hour(),
            "is_in_cooldown": self.state.is_in_cooldown,
            "cooldown_remaining": self.state.cooldown_remaining,
            "degradation_count": self.state.degradation_count,
            "stable_ticks": self.state.stable_ticks,
            "recommended_mode": self.recommend_mode(),
        }

    def get_cooldown_info(self) -> dict:
        """
        Get current cool-down status (for diagnostics).

        Returns:
            Dict with keys: is_in_cooldown, cooldown_remaining, degradation_count

        Deprecated: Use get_metrics() instead for comprehensive diagnostics
        """
        return {
            "is_in_cooldown": self.state.is_in_cooldown,
            "cooldown_remaining": self.state.cooldown_remaining,
            "degradation_count": self.state.degradation_count,
            "stable_ticks": self.state.stable_ticks,
        }
