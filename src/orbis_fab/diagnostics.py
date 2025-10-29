"""
Diagnostics Counters (Phase B.5)

Lightweight, dependency-free diagnostics for FAB stability and precision tracking.

Features:
- Counters: ticks, fills, mixes, envelope_changes, mode_transitions, rebalance_events
- Gauges: mode, global_precision, stream_precision, stable_ticks, cooldown_remaining
- Snapshot: JSON-serializable diagnostics block for mix() context
- Reset: Zero counters, preserve gauges

Usage:
    diag = Diagnostics()
    
    # Increment counters
    diag.inc_ticks()
    diag.inc_fills()
    diag.inc_envelope_changes()
    
    # Update gauges
    diag.set_gauge(mode="FAB1", global_precision="mxfp6.0")
    
    # Get snapshot
    snapshot = diag.snapshot()  # Returns dict with counters/gauges
    
    # Reset counters (gauges preserved)
    diag.reset()
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class Diagnostics:
    """Diagnostics counters and gauges for FAB operations"""
    
    # ========== Counters (monotonic) ==========
    ticks: int = 0
    """Total ticks processed (incremented in init_tick)"""
    
    fills: int = 0
    """Total fill() calls (node/edge additions)"""
    
    mixes: int = 0
    """Total mix() calls (context snapshots)"""
    
    envelope_changes: int = 0
    """Precision changes (hysteresis transitions)"""
    
    mode_transitions: int = 0
    """FAB mode transitions (FAB0→FAB1→FAB2)"""
    
    rebalance_events: int = 0
    """MMR rebalance operations (nodes penalized for coverage)"""
    
    # ========== Gauges (current state) ==========
    mode: str = "FAB0"
    """Current FAB mode"""
    
    global_precision: str = "mxfp4.12"
    """Current global window precision"""
    
    stream_precision: str = "mxfp4.12"
    """Current stream window precision"""
    
    stable_ticks: int = 0
    """Current stable ticks (from stability tracker)"""
    
    cooldown_remaining: int = 0
    """Remaining cooldown ticks (from stability tracker)"""
    
    # ========== Counter increment methods ==========
    
    def inc_ticks(self, n: int = 1) -> None:
        """Increment ticks counter"""
        self.ticks += n
    
    def inc_fills(self, n: int = 1) -> None:
        """Increment fills counter"""
        self.fills += n
    
    def inc_mixes(self, n: int = 1) -> None:
        """Increment mixes counter"""
        self.mixes += n
    
    def inc_envelope_changes(self, n: int = 1) -> None:
        """Increment envelope_changes counter"""
        self.envelope_changes += n
    
    def inc_mode_transitions(self, n: int = 1) -> None:
        """Increment mode_transitions counter"""
        self.mode_transitions += n
    
    def add_rebalance_events(self, n: int) -> None:
        """
        Add rebalance events (MMR penalties applied).
        
        Args:
            n: Number of rebalance events (e.g., nodes_penalized from MMR stats)
        """
        if n > 0:
            self.rebalance_events += n
    
    # ========== Gauge update methods ==========
    
    def set_gauge(self, **kwargs: Any) -> None:
        """
        Update gauges with keyword arguments.
        
        Args:
            **kwargs: Gauge names and values (e.g., mode="FAB1", global_precision="mxfp6.0")
        
        Example:
            diag.set_gauge(mode="FAB1", stable_ticks=100, cooldown_remaining=0)
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    # ========== Snapshot and reset ==========
    
    def snapshot(self) -> Dict[str, Any]:
        """
        Get JSON-serializable snapshot of all diagnostics.
        
        Returns:
            Dict with keys: counters, gauges
        
        Example:
            {
                "counters": {
                    "ticks": 17, "fills": 5, "mixes": 12,
                    "envelope_changes": 3, "mode_transitions": 2,
                    "rebalance_events": 14
                },
                "gauges": {
                    "mode": "FAB1", "global_precision": "mxfp4.12",
                    "stream_precision": "mxfp6.0", "stable_ticks": 37,
                    "cooldown_remaining": 0
                }
            }
        """
        return {
            "counters": {
                "ticks": self.ticks,
                "fills": self.fills,
                "mixes": self.mixes,
                "envelope_changes": self.envelope_changes,
                "mode_transitions": self.mode_transitions,
                "rebalance_events": self.rebalance_events,
            },
            "gauges": {
                "mode": self.mode,
                "global_precision": self.global_precision,
                "stream_precision": self.stream_precision,
                "stable_ticks": self.stable_ticks,
                "cooldown_remaining": self.cooldown_remaining,
            }
        }
    
    def reset(self) -> None:
        """
        Reset all counters to 0, preserve gauges.
        
        Gauges will be updated on next mix() call.
        """
        self.ticks = 0
        self.fills = 0
        self.mixes = 0
        self.envelope_changes = 0
        self.mode_transitions = 0
        self.rebalance_events = 0
        # Gauges preserved (mode, precisions, stable_ticks, cooldown_remaining)
    
    # ========== Derived metrics (for convenience) ==========
    
    def changes_per_1k_ticks(self) -> float:
        """
        Compute envelope changes per 1000 ticks.
        
        Returns:
            Rate of envelope changes (0.0 if no ticks)
        """
        if self.ticks == 0:
            return 0.0
        return (self.envelope_changes / self.ticks) * 1000.0
    
    def rebalance_per_fill(self) -> float:
        """
        Compute average rebalance events per fill.
        
        Returns:
            Average rebalance events per fill (0.0 if no fills)
        """
        if self.fills == 0:
            return 0.0
        return self.rebalance_events / self.fills
