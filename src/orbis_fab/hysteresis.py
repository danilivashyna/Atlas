"""FAB Bit-Envelope Hysteresis - Phase B

Hysteresis policy to prevent precision oscillation.

Zones with dead bands:
- up_threshold > down_threshold (e.g., 0.85 vs 0.75 for hot band)
- dwell_time: minimum ticks before precision change
- rate limit: ≤1 precision change/sec/window

Algorithm:
1. Track current precision and dwell counter per window
2. Score crosses up_threshold → increment dwell
3. After dwell_time ticks → upgrade precision
4. Score crosses down_threshold → downgrade (immediate, but rate-limited)
5. Score in dead band [down, up] → hold current precision

Example (hot band):
- Current: mxfp6.0, score jumps to 0.88
- up_threshold: 0.85, dwell_time: 3 ticks
- Tick 1-2: score ≥0.85, dwell=2 (still mxfp6.0)
- Tick 3: score ≥0.85, dwell=3 → upgrade to mxfp8.0

Invariants:
- Precision never changes mid-tick
- Rate limit: ≤1 change/sec (enforced by last_change_tick)
- Downgrade immediate on drop below down_threshold (prevents stale high precision)
- Dead band prevents dithering
"""

from typing import Tuple
from dataclasses import dataclass


@dataclass
class HysteresisConfig:
    """Hysteresis configuration for precision bands
    
    Each band has up/down thresholds with dead zone between them.
    dwell_time enforces stability before upgrading precision.
    rate_limit_ticks enforces ≤1 change/sec.
    """
    # Hot band (mxfp8.0)
    hot_up: float = 0.85        # Must cross to upgrade to hot
    hot_down: float = 0.75      # Must drop below to downgrade from hot
    
    # Warm-high band (mxfp6.0)
    warm_high_up: float = 0.65
    warm_high_down: float = 0.55
    
    # Warm-low band (mxfp5.25)
    warm_low_up: float = 0.45
    warm_low_down: float = 0.35
    
    # Cold band (mxfp4.12) - default, no thresholds needed
    
    # Dwell time (ticks to hold before upgrade)
    dwell_time: int = 3
    
    # Rate limit (ticks between changes, ~1/sec)
    rate_limit_ticks: int = 1000  # Assuming 1ms/tick → 1000 ticks ≈ 1sec


@dataclass
class HysteresisState:
    """Per-window hysteresis state
    
    Tracks current precision, dwell counter, and last change tick.
    """
    current_precision: str = "mxfp4.12"   # Current precision
    dwell_counter: int = 0                 # Ticks at current threshold
    last_change_tick: int = 0              # Last tick when precision changed
    target_precision: str = "mxfp4.12"     # Target precision (for dwell)


def assign_precision_hysteresis(
    score: float,
    state: HysteresisState,
    config: HysteresisConfig,
    current_tick: int
) -> Tuple[str, HysteresisState]:
    """Assign precision with hysteresis to prevent oscillation
    
    Args:
        score: Average node score [0.0, 1.0]
        state: Current hysteresis state
        config: Hysteresis configuration
        current_tick: Current tick number (for rate limiting)
    
    Returns:
        (new_precision, updated_state)
    
    Algorithm:
        1. Determine target precision from score (with up thresholds)
        2. If target > current: increment dwell, upgrade after dwell_time
        3. If score < down_threshold: immediate downgrade (rate-limited)
        4. If in dead band: hold current precision
    
    Example:
        # Initial state: mxfp4.12
        score=0.50 → target=mxfp5.25, dwell=1 (hold mxfp4.12)
        score=0.51 → target=mxfp5.25, dwell=2 (hold mxfp4.12)
        score=0.52 → target=mxfp5.25, dwell=3 → upgrade to mxfp5.25
        
        # Score drops
        score=0.30 → below down_threshold(0.35) → immediate downgrade to mxfp4.12
    """
    # Current precision determines dead band boundaries
    current = state.current_precision
    
    # Check if score is in dead band for current precision
    in_dead_band = False
    if current == "mxfp8.0" and config.hot_down <= score < config.hot_up:
        in_dead_band = True
    elif current == "mxfp6.0" and config.warm_high_down <= score < config.warm_high_up:
        in_dead_band = True
    elif current == "mxfp5.25" and config.warm_low_down <= score < config.warm_low_up:
        in_dead_band = True
    
    # If in dead band, hold current precision (no change)
    if in_dead_band:
        return current, state
    
    # Determine target precision from score (using up thresholds)
    if score >= config.hot_up:
        target = "mxfp8.0"
    elif score >= config.warm_high_up:
        target = "mxfp6.0"
    elif score >= config.warm_low_up:
        target = "mxfp5.25"
    else:
        target = "mxfp4.12"
    
    # Check for downgrade conditions (immediate, but rate-limited)
    should_downgrade = False
    if current == "mxfp8.0" and score < config.hot_down:
        should_downgrade = True
    elif current == "mxfp6.0" and score < config.warm_high_down:
        should_downgrade = True
    elif current == "mxfp5.25" and score < config.warm_low_down:
        should_downgrade = True
    
    # Rate limit check
    ticks_since_last_change = current_tick - state.last_change_tick
    # Allow change if: never changed before OR enough time passed
    can_change = (state.last_change_tick == 0) or (ticks_since_last_change >= config.rate_limit_ticks)
    
    # Downgrade path (immediate if rate limit allows)
    if should_downgrade and can_change:
        # Find appropriate lower precision based on score
        if score >= config.warm_high_up:
            new_precision = "mxfp6.0"
        elif score >= config.warm_low_up:
            new_precision = "mxfp5.25"
        else:
            new_precision = "mxfp4.12"
        
        # Only downgrade if new precision is actually lower than current
        # This prevents downgrade when score is in dead band
        precision_levels = {"mxfp4.12": 0, "mxfp5.25": 1, "mxfp6.0": 2, "mxfp8.0": 3}
        if precision_levels.get(new_precision, 0) < precision_levels.get(current, 0):
            return new_precision, HysteresisState(
                current_precision=new_precision,
                dwell_counter=0,
                last_change_tick=current_tick,
                target_precision=new_precision
            )
    
    # Upgrade/target change path (requires dwell time)
    if target != current:
        # Determine if this is upgrade or downgrade via target
        precision_levels = {"mxfp4.12": 0, "mxfp5.25": 1, "mxfp6.0": 2, "mxfp8.0": 3}
        is_upgrade = precision_levels.get(target, 0) > precision_levels.get(current, 0)
        
        # Downgrades via target require rate limit (same as immediate downgrades)
        if not is_upgrade and not can_change:
            return current, state  # Rate limit blocks downgrade
        
        # Check if we're pursuing same target
        if target == state.target_precision:
            # Continue dwelling
            new_dwell = state.dwell_counter + 1
            
            # Change if dwell time reached and (upgrade OR rate limit allows)
            if new_dwell >= config.dwell_time and (is_upgrade or can_change):
                return target, HysteresisState(
                    current_precision=target,
                    dwell_counter=0,
                    last_change_tick=current_tick,
                    target_precision=target
                )
            else:
                # Still dwelling
                return current, HysteresisState(
                    current_precision=current,
                    dwell_counter=new_dwell,
                    last_change_tick=state.last_change_tick,
                    target_precision=target
                )
        else:
            # New target, reset dwell
            return current, HysteresisState(
                current_precision=current,
                dwell_counter=1,
                last_change_tick=state.last_change_tick,
                target_precision=target
            )
    
    # Target == current, reset dwell
    return current, HysteresisState(
        current_precision=current,
        dwell_counter=0,
        last_change_tick=state.last_change_tick,
        target_precision=current
    )
