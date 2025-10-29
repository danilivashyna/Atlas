"""FABCore - Phase A MVP

Main orchestrator for FAB state machine and dual windows.

API:
- init_tick(): Lock budgets for tick, set mode
- fill(): Populate global/stream windows from Z-slice
- mix(): Return tick context snapshot (no I/O)
- step_stub(): Update metrics and drive state transitions

Flow (per tick):
1. init_tick(mode, budgets) → fix capacity
2. fill(z_slice) → split nodes to global/stream by score
3. mix() → return context snapshot
4. step_stub(stress, self_presence, error_rate) → transition FAB0→FAB1→FAB2

State Transitions:
- FAB0→FAB1: self_presence ≥0.8 ∧ stress <0.7 ∧ error_rate ≤0.05
- FAB1→FAB2: stable 3 ticks ∧ stress <0.5 ∧ error_rate ≤0.05
- Degrade→FAB1: stress >0.7 ∨ error_rate >0.05

Invariants:
- Budgets immutable during tick
- Global + Stream ≤ budgets.nodes
- No I/O in Phase A (OneBlock/Atlas stubs only)
"""

from .types import FabMode, Budgets, ZSliceLite, Metrics
from .state import FabState
from .envelope import assign_precision


class FABCore:
    """FAB state machine orchestrator
    
    Manages dual windows (global/stream) and mode transitions.
    Phase A: No external I/O, autonomous operation.
    """
    
    def __init__(self, hold_ms: int = 1500):
        """Initialize FAB with default hold time
        
        Args:
            hold_ms: Mode transition hold time (default: 1500ms)
        """
        self.st = FabState(hold_ms=hold_ms)
    
    def init_tick(self, *, mode: FabMode, budgets: Budgets) -> None:
        """Initialize tick with fixed budgets
        
        Locks capacity for duration of tick execution.
        Sets window caps based on budgets.
        
        Args:
            mode: Target FAB mode (FAB0/FAB1/FAB2)
            budgets: Fixed capacity (tokens/nodes/edges/time)
        
        Invariants:
            - budgets.nodes split between global (≤256) and stream (≤128)
            - mode can only change via step_stub() transitions
            - total nodes (global + stream) ≤ budgets.nodes
        """
        self.st.mode = mode
        
        # Calculate window caps respecting total budget
        # Stream gets priority up to 128, rest goes to global up to 256
        max_stream = min(budgets["nodes"], 128)
        remaining_for_global = budgets["nodes"] - max_stream
        max_global = min(remaining_for_global, 256)
        
        self.st.stream_win.cap_nodes = max_stream
        self.st.global_win.cap_nodes = max_global
    
    def fill(self, z: ZSliceLite) -> None:
        """Populate windows from Z-slice
        
        Splits nodes by score:
        - High scores → stream (active thought)
        - Low scores → global (background)
        
        Assigns precision based on average score per window.
        
        Args:
            z: Z-slice with nodes sorted by score descending
        
        Invariants:
            - stream nodes ≤ stream_win.cap_nodes
            - global nodes ≤ global_win.cap_nodes
            - total nodes ≤ budgets.nodes
        """
        # Sort nodes by score descending (ensure invariant)
        nodes_sorted = sorted(z["nodes"], key=lambda n: n["score"], reverse=True)
        
        # Split: high scores → stream, rest → global
        self.st.stream_win.nodes = nodes_sorted[: self.st.stream_win.cap_nodes]
        global_start = self.st.stream_win.cap_nodes
        global_end = global_start + self.st.global_win.cap_nodes
        self.st.global_win.nodes = nodes_sorted[global_start:global_end]
        
        # Assign precision based on average score
        if self.st.stream_win.nodes:
            avg_score = sum(n["score"] for n in self.st.stream_win.nodes) / len(self.st.stream_win.nodes)
            self.st.stream_win.precision = assign_precision(avg_score)
        
        # Global window keeps default cold precision (mxfp4.12)
        self.st.global_win.precision = "mxfp4.12"
    
    def mix(self) -> dict:
        """Return tick context snapshot (no I/O)
        
        Returns current window state without external calls.
        Phase A: Pure data return, no OneBlock/Atlas interaction.
        
        Returns:
            Context snapshot with mode, window sizes, precision
        
        Example:
            {
                "mode": "FAB1",
                "global_size": 200,
                "stream_size": 56,
                "stream_precision": "mxfp6.0"
            }
        """
        return {
            "mode": self.st.mode,
            "global_size": len(self.st.global_win.nodes),
            "stream_size": len(self.st.stream_win.nodes),
            "stream_precision": self.st.stream_win.precision,
            "global_precision": self.st.global_win.precision,
        }
    
    def step_stub(self, *, stress: float, self_presence: float, error_rate: float) -> dict:
        """Update metrics and drive state transitions
        
        Implements FAB state machine logic:
        - FAB0→FAB1: self_presence ≥0.8 ∧ stress <0.7 ∧ ok
        - FAB1→FAB2: stable 3 ticks ∧ stress <0.5 ∧ ok
        - Degrade→FAB1: stress >0.7 ∨ error_rate >0.05
        
        Args:
            stress: Load stress [0.0, 1.0]
            self_presence: SELF token presence [0.0, 1.0]
            error_rate: Error rate [0.0, 1.0]
        
        Returns:
            Transition result with new mode and stability counter
        
        Example:
            step_stub(stress=0.3, self_presence=0.85, error_rate=0.0)
            -> {"mode": "FAB1", "stable_ticks": 0}
        """
        # Update metrics
        m: Metrics = {
            "stress": stress,
            "self_presence": self_presence,
            "error_rate": error_rate
        }
        self.st.metrics = m
        
        # State machine transitions
        if self.st.mode == "FAB0":
            # FAB0 → FAB1: SELF present, low stress, no errors
            if self_presence >= 0.8 and stress < 0.7 and error_rate <= 0.05:
                self.st.mode = "FAB1"
                self.st.stable_ticks = 0
        
        elif self.st.mode == "FAB1":
            # Degrade to FAB1 if stress/errors high
            if stress > 0.7 or error_rate > 0.05:
                # Stay in FAB1, reset stability
                self.st.stable_ticks = 0
            else:
                # Count stable ticks
                self.st.stable_ticks += 1
                # FAB1 → FAB2: 3 stable ticks, very low stress
                if self.st.stable_ticks >= 3 and stress < 0.5:
                    self.st.mode = "FAB2"
        
        elif self.st.mode == "FAB2":
            # FAB2 → FAB1: Degrade on stress/errors
            if stress > 0.7 or error_rate > 0.05:
                self.st.mode = "FAB1"
                self.st.stable_ticks = 0
        
        return {
            "mode": self.st.mode,
            "stable_ticks": self.st.stable_ticks
        }
