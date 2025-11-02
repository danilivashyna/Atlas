"""FAB State Machine - Phase A MVP

Core state representation for FAB windows and mode transitions.

Windows:
- Global: Background context (self/ethics/history), precision ≤mxfp4.12
- Stream: Current thought, precision mxfp6-8, fast updates

State Machine:
- FAB0: No SELF, validation-only, no Atlas writes
- FAB1: SELF present, navigation/mix, anti-oscillation
- FAB2: SELF + Ego, I/O permitted (future)

Transitions:
- FAB0→FAB1: self_presence ≥0.8 ∧ stress <0.7 ∧ ok
- FAB1→FAB2: stable 3 ticks ∧ stress <0.5 ∧ ok
- Degrade→FAB1: stress >0.7 ∨ error_rate >0.05

Invariants:
- One SELF per window (slot reserved, not implemented in Phase A)
- Global + Stream ≤ budgets.nodes
- No mode changes during tick execution
"""

from dataclasses import dataclass, field
from typing import List
from .types import FabMode, ZNode, Metrics


@dataclass
class Window:
    """FAB window (Global or Stream)

    Holds active nodes with assigned precision.
    Reserves slot for SELF token (not implemented in Phase A).
    """
    name: str                           # "global" | "stream"
    nodes: List[ZNode] = field(default_factory=list)
    cap_nodes: int = 0                  # Max nodes (set by budgets)
    precision: str = "mxfp4.12"         # Bit-envelope precision
    self_slot_reserved: bool = True     # Reserve space for [SELF] token

    def __repr__(self) -> str:
        return f"Window(name={self.name}, nodes={len(self.nodes)}/{self.cap_nodes}, precision={self.precision})"


@dataclass
class FabState:
    """FAB state machine state

    Manages mode transitions and dual windows (global/stream).
    Tracks stability for FAB1→FAB2 transition.
    """
    mode: FabMode = "FAB0"
    global_win: Window = field(default_factory=lambda: Window("global"))
    stream_win: Window = field(default_factory=lambda: Window("stream"))
    hold_ms: int = 1500                 # Mode transition hold time
    stable_ticks: int = 0               # Consecutive stable ticks (for FAB1→FAB2)
    metrics: Metrics = field(default_factory=lambda: {
        "stress": 0.0,
        "self_presence": 0.0,
        "error_rate": 0.0
    })

    def __repr__(self) -> str:
        return (f"FabState(mode={self.mode}, stable_ticks={self.stable_ticks}, "
                f"global={len(self.global_win.nodes)}, stream={len(self.stream_win.nodes)}, "
                f"stress={self.metrics['stress']:.2f})")
