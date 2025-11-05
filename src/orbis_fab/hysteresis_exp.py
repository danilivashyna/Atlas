"""
Hysteresis (Experimental) - Phase B.1 Anti-Drebezg (Anti-Chatter)

Prevents frequent precision mode switching and oscillations through:
- Dwell time: minimum ticks before accepting mode change
- Global rate limit: minimum ticks between any switches
- Oscillation detection: tracking rapid back-and-forth changes

Feature flag: AURIS_HYSTERESIS=on

Usage:
    from orbis_fab.hysteresis_exp import BitEnvelopeHysteresisExp, HysteresisConfig

    config = HysteresisConfig(dwell_ticks=50, rate_limit_ticks=1000)
    hyst = BitEnvelopeHysteresisExp(config)

    # Each tick
    effective_mode = hyst.update(desired_mode="FAB2", tick=current_tick)
    metrics = hyst.get_metrics()

SLO/SLI Targets:
    - switch_rate_p95 ≤ 1/sec (1000 ticks ≈ 1 sec)
    - oscillation_rate_p95 reduced by 50%+ vs baseline
"""

import os
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

# Feature flag
HYSTERESIS_ENABLED = os.getenv("AURIS_HYSTERESIS", "off").lower() in (
    "on",
    "true",
    "1",
)


def is_enabled() -> bool:
    """Check if hysteresis is enabled."""
    return HYSTERESIS_ENABLED


@dataclass
class HysteresisConfig:
    """Configuration for hysteresis anti-chatter logic.

    Attributes:
        dwell_ticks: Minimum ticks to hold desired mode before switching (default: 50)
        rate_limit_ticks: Minimum ticks between any mode switches (default: 1000 ≈ 1 sec)
        osc_window: Window size for oscillation detection (default: 300 ticks)
        max_history: Maximum switch history to retain (default: 5000)
    """

    dwell_ticks: int = 50
    rate_limit_ticks: int = 1000
    osc_window: int = 300
    max_history: int = 5000


@dataclass
class HysteresisState:
    """Runtime state for hysteresis tracking.

    Attributes:
        last_mode: Current effective mode (default: FAB2)
        last_switch_tick: Tick of last mode switch (default: -10^9 for cold start)
        dwell_counter: Consecutive ticks with same desired mode
        switch_history: Deque of switch tick timestamps
        osc_count: Count of detected oscillations (back-and-forth within osc_window)
    """

    last_mode: str = "FAB2"
    last_switch_tick: int = -(10**9)
    dwell_counter: int = 0
    switch_history: deque = field(default_factory=deque)  # maxlen set in __init__
    osc_count: int = 0


class BitEnvelopeHysteresisExp:
    """Experimental bit-envelope hysteresis for FAB mode anti-chatter.

    Implements:
    - Dwell time: desired mode must persist for dwell_ticks before switch
    - Global rate limit: switches must be ≥ rate_limit_ticks apart
    - Oscillation detection: counts rapid back-and-forth changes

    Example:
        config = HysteresisConfig(dwell_ticks=50, rate_limit_ticks=1000)
        hyst = BitEnvelopeHysteresisExp(config)

        for tick in range(10000):
            desired = recommend_mode()  # From B2 StabilityTracker
            effective = hyst.update(desired, tick)
            # effective is smoother than desired
    """

    def __init__(self, config: Optional[HysteresisConfig] = None):
        """Initialize hysteresis with config.

        Args:
            config: HysteresisConfig instance (uses defaults if None)
        """
        self.config = config or HysteresisConfig()
        # Create state with deque maxlen from config
        self.state = HysteresisState(switch_history=deque(maxlen=self.config.max_history))

    def update(self, desired_mode: str, tick: int) -> str:
        """Update hysteresis state and return effective mode.

        Args:
            desired_mode: Desired FAB mode (FAB0/FAB1/FAB2) from upstream
            tick: Current tick number

        Returns:
            Effective mode after hysteresis filtering

        Logic:
            1. If desired_mode != last_mode:
               - Increment dwell_counter
               - If dwell_counter >= dwell_ticks AND
                  (tick - last_switch_tick) >= rate_limit_ticks:
                  → Switch to desired_mode
               - Else: stay in last_mode
            2. If desired_mode == last_mode:
               - Reset dwell_counter to 0
            3. Detect oscillations: rapid back-and-forth in switch_history
        """
        if desired_mode != self.state.last_mode:
            # Desired mode differs → increment dwell
            self.state.dwell_counter += 1

            # Check if switch is allowed
            ticks_since_last = tick - self.state.last_switch_tick
            dwell_satisfied = self.state.dwell_counter >= self.config.dwell_ticks
            rate_limit_ok = ticks_since_last >= self.config.rate_limit_ticks

            if dwell_satisfied and rate_limit_ok:
                # Perform switch
                old_mode = self.state.last_mode
                self.state.last_mode = desired_mode
                self.state.last_switch_tick = tick
                self.state.dwell_counter = 0

                # Record in history
                self.state.switch_history.append(tick)

                # Detect oscillation (back-and-forth within osc_window)
                self._detect_oscillation(old_mode, desired_mode, tick)

            # Else: stay in last_mode (dwell or rate limit not satisfied)
        else:
            # Desired mode matches current → reset dwell
            self.state.dwell_counter = 0

        return self.state.last_mode

    def _detect_oscillation(self, old_mode: str, new_mode: str, tick: int) -> None:
        """Detect oscillation: rapid back-and-forth mode changes.

        Oscillation = switching back to a mode recently left within osc_window.

        Args:
            old_mode: Mode being left
            new_mode: Mode being entered
            tick: Current tick
        """
        # Check if we have enough history
        if len(self.state.switch_history) < 2:
            return

        # Look for recent switch from new_mode → old_mode
        # (i.e., we're switching back to new_mode within osc_window)
        recent_switches = [
            t for t in self.state.switch_history if tick - t <= self.config.osc_window
        ]

        # If we have 2+ switches in osc_window, it's an oscillation
        if len(recent_switches) >= 2:
            self.state.osc_count += 1

    def get_metrics(self) -> dict:
        """Get comprehensive hysteresis metrics.

        Returns:
            Dict with keys:
                - switch_rate_per_sec: switches per second (based on history)
                - oscillation_rate_per_sec: oscillations per second
                - last_switch_age: ticks since last switch
                - dwell_counter: current dwell accumulator
                - last_mode: current effective mode
                - osc_count: total oscillation count
        """
        # Calculate switch rate (switches per 1000 ticks ≈ 1 sec)
        if len(self.state.switch_history) < 2:
            switch_rate = 0.0
        else:
            # Get time span of history
            oldest = self.state.switch_history[0]
            newest = self.state.switch_history[-1]
            span_ticks = newest - oldest
            if span_ticks > 0:
                # switches per 1000 ticks
                switch_rate = (len(self.state.switch_history) / span_ticks) * 1000.0
            else:
                switch_rate = 0.0

        # Calculate oscillation rate
        # Use last osc_window as denominator
        if self.state.osc_count > 0 and len(self.state.switch_history) > 0:
            # Oscillations per 1000 ticks
            osc_rate = (self.state.osc_count / len(self.state.switch_history)) * 1000.0
        else:
            osc_rate = 0.0

        # Age of last switch
        if self.state.last_switch_tick > -(10**9):
            # Approximate current tick from history
            current_tick_approx = (
                self.state.switch_history[-1]
                if self.state.switch_history
                else self.state.last_switch_tick
            )
            last_switch_age = current_tick_approx - self.state.last_switch_tick
        else:
            last_switch_age = 0

        return {
            "switch_rate_per_sec": switch_rate,
            "oscillation_rate_per_sec": osc_rate,
            "last_switch_age": last_switch_age,
            "dwell_counter": self.state.dwell_counter,
            "last_mode": self.state.last_mode,
            "osc_count": self.state.osc_count,
        }
