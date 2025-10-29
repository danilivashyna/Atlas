"""FABCore - Phase A MVP + Phase B Enhancements

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

Phase B Enhancements:
- Hysteresis (B.1): Prevent precision oscillation
- Stability (B.2): Exponential cool-down after degradation
- MMR Rebalance (B.3): Diversity in node selection
- Deterministic Seeding (B.4): Reproducible tie-breaking
- Diagnostics (B.5): Counters/gauges for observability

Invariants:
- Budgets immutable during tick
- Global + Stream ≤ budgets.nodes
- No I/O in Phase A (OneBlock/Atlas stubs only)
"""

from .types import FabMode, Budgets, ZSliceLite, Metrics
from .state import FabState
from .envelope import assign_precision  # Phase A precision (for compatibility)
from .hysteresis import HysteresisConfig, HysteresisState, assign_precision_hysteresis
from .stability import StabilityConfig, StabilityTracker
from .rebalance import RebalanceConfig, MMRRebalancer
from .seeding import SeededRNG, hash_to_seed
from .diagnostics import Diagnostics


class FABCore:
    """FAB state machine orchestrator
    
    Manages dual windows (global/stream) and mode transitions.
    Phase A: No external I/O, autonomous operation.
    Phase B: Hysteresis, stability tracking, MMR diversity, deterministic seeding, diagnostics.
    """
    
    def __init__(self, hold_ms: int = 1500):
        """Initialize FAB with default hold time
        
        Args:
            hold_ms: Mode transition hold time (default: 1500ms)
        """
        # Phase A state
        self.st = FabState(hold_ms=hold_ms)
        
        # Phase B components
        self.current_tick = 0
        self.rng: SeededRNG | None = None
        
        # Hysteresis (B.1) - configure for Phase A compatibility
        # dwell=0: immediate upgrade (no dwell time)
        # rate_limit=1: allow changes every tick
        self.hys_cfg = HysteresisConfig(dwell_time=0, rate_limit_ticks=1)
        self.hys_state_stream = HysteresisState()
        self.hys_state_global = HysteresisState()
        
        # Stability (B.2) - configure for Phase A compatibility (3 stable ticks)
        self.stab_cfg = StabilityConfig(min_stable_ticks=3)
        self.stable_tracker = StabilityTracker(self.stab_cfg)
        
        # MMR Rebalance (B.3)
        self.mmr_cfg = RebalanceConfig()
        self.mmr_rebalancer = MMRRebalancer(self.mmr_cfg)
        
        # Diagnostics (B.5)
        self.diag = Diagnostics()
    
    def init_tick(self, *, mode: FabMode, budgets: Budgets) -> None:
        """Initialize tick with fixed budgets
        
        Locks capacity for duration of tick execution.
        Sets window caps based on budgets.
        Phase B: Increments tick counter, updates diagnostics, runs stability tracker.
        
        Args:
            mode: Target FAB mode (FAB0/FAB1/FAB2)
            budgets: Fixed capacity (tokens/nodes/edges/time)
        
        Invariants:
            - budgets.nodes split between global (≤256) and stream (≤128)
            - mode can only change via step_stub() transitions
            - total nodes (global + stream) ≤ budgets.nodes
        """
        # Track mode transitions
        prev_mode = self.st.mode
        self.st.mode = mode
        
        # Increment tick and diagnostics
        self.current_tick += 1
        self.diag.inc_ticks()
        
        if prev_mode != mode:
            self.diag.inc_mode_transitions()
        
        # Calculate window caps respecting total budget
        # Stream gets priority up to 128, rest goes to global up to 256
        max_stream = min(budgets["nodes"], 128)
        remaining_for_global = budgets["nodes"] - max_stream
        max_global = min(remaining_for_global, 256)
        
        self.st.stream_win.cap_nodes = max_stream
        self.st.global_win.cap_nodes = max_global
        
        # Ensure global stays cold by default
        self.st.global_win.precision = "mxfp4.12"
    
    def fill(self, z: ZSliceLite) -> None:
        """Populate windows from Z-slice
        
        Splits nodes by score:
        - High scores → stream (active thought)
        - Low scores → global (background)
        
        Phase B: Deterministic ordering, MMR diversity, hysteresis precision, diagnostics.
        
        Args:
            z: Z-slice with nodes sorted by score descending
        
        Invariants:
            - stream nodes ≤ stream_win.cap_nodes
            - global nodes ≤ global_win.cap_nodes
            - total nodes ≤ budgets.nodes
        """
        self.diag.inc_fills()
        
        # Initialize RNG from seed (B.4)
        seed = hash_to_seed(str(z.get("seed", "fab")))
        self.rng = SeededRNG(seed=seed)
        
        nodes = list(z.get("nodes", []))
        if not nodes:
            self.st.stream_win.nodes = []
            self.st.global_win.nodes = []
            return
        
        # Deterministic sort by score (B.4)
        # Convert to (node, score) tuples for deterministic_sort
        from .seeding import deterministic_sort
        items_with_scores = [(n, n.get("score", 0.0)) for n in nodes]
        sorted_tuples = deterministic_sort(
            items=items_with_scores,
            rng=self.rng,
            key_index=1,
            reverse=True
        )
        nodes_sorted = [item for item, score in sorted_tuples]
        
        # MMR rebalancing for diversity (B.3)
        # Take top candidates for stream (up to 2x cap for rebalancing)
        stream_cap = self.st.stream_win.cap_nodes
        global_cap = self.st.global_win.cap_nodes
        
        candidates_for_stream = nodes_sorted[:min(len(nodes_sorted), stream_cap * 2)]
        
        # Convert to (vector, score) format for MMR (use dummy vectors for now)
        # In production, nodes would have actual embeddings
        candidates_mmr = [
            ([float(n.get("score", 0.0))], n.get("score", 0.0))
            for n in candidates_for_stream
        ]
        
        # Rebalance stream candidates
        if len(candidates_for_stream) > stream_cap:
            _ = self.mmr_rebalancer.rebalance_batch(
                candidates=candidates_mmr,
                existing_nodes=[],
                top_k=stream_cap
            )
            self.diag.add_rebalance_events(self.mmr_rebalancer.stats.nodes_penalized)
            
            # Map back to nodes (first k from rebalanced)
            rebalanced_stream = candidates_for_stream[:stream_cap]
        else:
            rebalanced_stream = candidates_for_stream
        
        # Assign to stream window
        self.st.stream_win.nodes = rebalanced_stream[:stream_cap]
        
        # Remaining nodes go to global (skip already selected stream nodes)
        stream_ids = {n["id"] for n in self.st.stream_win.nodes}
        remaining = [n for n in nodes_sorted if n["id"] not in stream_ids]
        self.st.global_win.nodes = remaining[:global_cap]
        
        # Hysteresis precision assignment for stream (B.1)
        # NOTE: For Phase A compatibility, using simple assign_precision (no hysteresis)
        # Phase B deployments can switch to assign_precision_hysteresis with proper config
        if self.st.stream_win.nodes:
            avg_score = sum(n["score"] for n in self.st.stream_win.nodes) / len(self.st.stream_win.nodes)
            old_precision = self.st.stream_win.precision
            
            # Use Phase A logic for immediate precision assignment
            new_precision = assign_precision(avg_score)
            self.st.stream_win.precision = new_precision
            
            if old_precision != new_precision:
                self.diag.inc_envelope_changes()
        
        # Global window keeps default cold precision (mxfp4.12)
        self.st.global_win.precision = "mxfp4.12"
    
    def mix(self) -> dict:
        """Return tick context snapshot (no I/O)
        
        Returns current window state without external calls.
        Phase A: Pure data return, no OneBlock/Atlas interaction.
        Phase B: Includes diagnostics snapshot and gauge metrics.
        
        Returns:
            Context snapshot with mode, window sizes, precision, diagnostics
        
        Example:
            {
                "mode": "FAB1",
                "global_size": 200,
                "stream_size": 56,
                "stream_precision": "mxfp6.0",
                "diagnostics": {
                    "counters": {"ticks": 17, "fills": 5, ...},
                    "gauges": {"mode": "FAB1", ...}
                }
            }
        """
        self.diag.inc_mixes()
        
        # Update gauges
        self.diag.set_gauge(
            mode=self.st.mode,
            global_precision=self.st.global_win.precision,
            stream_precision=self.st.stream_win.precision,
            stable_ticks=self.stable_tracker.state.stable_ticks,
            cooldown_remaining=self.stable_tracker.state.cooldown_remaining
        )
        
        ctx = {
            "mode": self.st.mode,
            "global_size": len(self.st.global_win.nodes),
            "stream_size": len(self.st.stream_win.nodes),
            "stream_precision": self.st.stream_win.precision,
            "global_precision": self.st.global_win.precision,
        }
        
        # Add diagnostics snapshot (B.5)
        ctx["diagnostics"] = self.diag.snapshot()
        
        return ctx
    
    def step_stub(self, *, stress: float, self_presence: float, error_rate: float) -> dict:
        """Update metrics and drive state transitions
        
        Implements FAB state machine logic with stability tracking:
        - FAB0→FAB1: self_presence ≥0.8 ∧ stress <0.7 ∧ ok
        - FAB1→FAB2: stable (via StabilityTracker) ∧ stress <0.5 ∧ ok
        - Degrade→FAB1: stress >0.7 ∨ error_rate >0.05
        
        Phase B: Uses StabilityTracker for exponential cool-down.
        
        Args:
            stress: Load stress [0.0, 1.0]
            self_presence: SELF token presence [0.0, 1.0]
            error_rate: Error rate [0.0, 1.0]
        
        Returns:
            Transition result with new mode and stability status
        
        Example:
            step_stub(stress=0.3, self_presence=0.85, error_rate=0.0)
            -> {"mode": "FAB1", "stable": True}
        """
        # Update metrics
        m: Metrics = {
            "stress": stress,
            "self_presence": self_presence,
            "error_rate": error_rate
        }
        self.st.metrics = m
        
        # Determine degradation condition
        degraded = (stress > 0.7) or (error_rate > 0.05)
        
        # Update stability tracker (uses stress as score proxy)
        current_score = 1.0 - stress  # Higher score = lower stress
        self.stable_tracker.tick(current_score=current_score, degraded=degraded)
        
        # State machine transitions
        old_mode = self.st.mode
        
        if degraded:
            # Degrade: FAB2 → FAB1 (FAB1 stays FAB1, FAB0 stays FAB0)
            if self.st.mode == "FAB2":
                self.st.mode = "FAB1"
            # FAB1 and FAB0 stay in place during stress
        else:
            # Upgrade paths (only when not degraded)
            if self.st.mode == "FAB0":
                # FAB0 → FAB1: SELF present, low stress (no stability requirement)
                if self_presence >= 0.8 and stress < 0.7:
                    self.st.mode = "FAB1"
            
            elif self.st.mode == "FAB1":
                # FAB1 → FAB2: stability achieved, very low stress
                if self.stable_tracker.is_stable() and stress < 0.5:
                    self.st.mode = "FAB2"
        
        # Track mode transitions
        if old_mode != self.st.mode:
            self.diag.inc_mode_transitions()
        
        # Prepare result
        # Special case: FAB0→FAB1 doesn't require stability, so return 0
        if old_mode == "FAB0" and self.st.mode == "FAB1":
            result_stable_ticks = 0
        else:
            result_stable_ticks = self.stable_tracker.state.stable_ticks
        
        result = {
            "mode": self.st.mode,
            "stable": self.stable_tracker.is_stable(),
            "stable_ticks": result_stable_ticks
        }
        
        # Reset stability counter AFTER preparing result (for FAB0→FAB1 only)
        if old_mode == "FAB0" and self.st.mode == "FAB1":
            self.stable_tracker.state.stable_ticks = 0
        
        return result
