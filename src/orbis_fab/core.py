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
from .envelope import assign_precision, precision_level  # Phase A precision + level mapper
from .hysteresis import HysteresisConfig, HysteresisState, assign_precision_hysteresis
from .stability import StabilityConfig, StabilityTracker
from .rebalance import RebalanceConfig, MMRRebalancer
from .seeding import SeededRNG, hash_to_seed, combine_seeds
from .diagnostics import Diagnostics
import secrets

# Phase 2: Z-Space integration
try:
    from orbis_z import ZSpaceShim
    HAS_ZSPACE = True
except ImportError:
    HAS_ZSPACE = False


class FABCore:
    """FAB state machine orchestrator
    
    Manages dual windows (global/stream) and mode transitions.
    Phase A: No external I/O, autonomous operation.
    Phase B: Hysteresis, stability tracking, MMR diversity, deterministic seeding, diagnostics.
    Phase C+: Configurable envelope mode (legacy vs hysteresis rollout).
    """
    
    def __init__(
        self,
        hold_ms: int = 1500,
        envelope_mode: str = "legacy",
        hysteresis_dwell: int = 3,
        hysteresis_rate_limit: int = 1000,
        min_stream_for_upgrade: int = 8,
        session_id: str | None = None,
        selector: str = "fab"
    ):
        """Initialize FAB with configurable envelope behavior and node selection
        
        Args:
            hold_ms: Mode transition hold time (default: 1500ms)
            envelope_mode: Precision assignment mode ('legacy' or 'hysteresis')
                - 'legacy': immediate precision assignment (Phase A behavior)
                - 'hysteresis': dead-band + dwell time to prevent oscillation
            hysteresis_dwell: Dwell time for hysteresis mode (default: 3 ticks)
            hysteresis_rate_limit: Rate limit for hysteresis mode (default: 1000 ticks ≈ 1s)
            min_stream_for_upgrade: Minimum stream size for precision upgrades (default: 8)
                - Prevents false upgrades on tiny samples in hysteresis mode
            session_id: Optional deterministic session ID for reproducible RNG
                - If None, generates random session ID
                - Use fixed value for deterministic testing/debugging
            selector: Node selection strategy ('fab' or 'z-space', default: 'fab')
                - 'fab': Original FAB selection (score-based sort + MMR)
                - 'z-space': Use ZSpaceShim for deterministic top-k selection
                - Phase 2: Enables vec-based MMR when node.vec present
        
        Example:
            # Phase A compatibility (default)
            fab = FABCore()
            
            # Enable hysteresis for production
            fab = FABCore(envelope_mode='hysteresis', hysteresis_dwell=3)
            
            # Deterministic session for testing
            fab = FABCore(session_id='test-session-42')
            
            # Enable Z-Space selector (Phase 2)
            fab = FABCore(selector='z-space', session_id='test-z-space')
        """
        # Phase A state
        self.st = FabState(hold_ms=hold_ms)
        
        # Phase C+ configuration
        if envelope_mode not in ("legacy", "hysteresis"):
            raise ValueError(f"envelope_mode must be 'legacy' or 'hysteresis', got {envelope_mode}")
        self.envelope_mode = envelope_mode
        
        # Phase 2: Node selection strategy
        if selector not in ("fab", "z-space"):
            raise ValueError(f"selector must be 'fab' or 'z-space', got {selector}")
        self.selector = selector
        
        # Session ID for deterministic seeding (C+.5 enhancement)
        self.session_id = session_id if session_id is not None else f"fab-{secrets.token_hex(4)}"
        self.session_seed = hash_to_seed(self.session_id)  # Cache to avoid rehashing on every fill()
        
        # Phase B components
        self.current_tick = 0
        self.rng: SeededRNG | None = None
        
        # Hysteresis (B.1) - configure based on envelope_mode
        if self.envelope_mode == "legacy":
            # Phase A compatibility: immediate assignment (dwell=0, rate_limit=1)
            self.hys_cfg = HysteresisConfig(
                dwell_time=0,
                rate_limit_ticks=1,
                min_stream_for_upgrade=min_stream_for_upgrade
            )
        else:
            # Production hysteresis: dead band + dwell + rate limit + tiny stream guard
            self.hys_cfg = HysteresisConfig(
                dwell_time=hysteresis_dwell,
                rate_limit_ticks=hysteresis_rate_limit,
                min_stream_for_upgrade=min_stream_for_upgrade
            )
        
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
        Phase 2: Selector strategy ('fab' or 'z-space' for node selection).
        
        Args:
            z: Z-slice with nodes sorted by score descending
        
        Invariants:
            - stream nodes ≤ stream_win.cap_nodes
            - global nodes ≤ global_win.cap_nodes
            - total nodes ≤ budgets.nodes
        """
        self.diag.inc_fills()
        
        # Route to selector-specific implementation
        if self.selector == "z-space":
            return self._fill_with_z_space(z)
        else:
            # Default: original FAB selection (Phase A/B/C+)
            return self._fill_with_fab_selector(z)
    
    def _fill_with_fab_selector(self, z: ZSliceLite) -> None:
        """Original FAB node selection (score-based sort + MMR).
        
        This preserves Phase A/B/C+ behavior for backward compatibility.
        Used when selector='fab' (default).
        """
        
        # Initialize deterministic RNG from combined seeds (B.4 + C+.5)
        # Combine: z_slice seed + session_id + current_tick
        z_seed = hash_to_seed(str(z.get("seed", "fab")))
        tick_seed = self.current_tick
        
        # Combine all seeds for single deterministic RNG per tick (session_seed cached in __init__)
        combined_seed = combine_seeds(z_seed, self.session_seed, tick_seed)
        self.rng = SeededRNG(seed=combined_seed)
        
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
        
        # Rebalance stream candidates using MMR
        if len(candidates_for_stream) > stream_cap:
            # Convert to (vector, score) for MMR (dummy 1D vectors based on score)
            candidates_mmr = [
                ([float(node.get("score", 0.0))], node.get("score", 0.0))
                for node in candidates_for_stream
            ]
            
            # Run MMR rebalancing (returns top-k by rebalanced score)
            rebalanced_results = self.mmr_rebalancer.rebalance_batch(
                candidates=candidates_mmr,
                existing_nodes=[],
                top_k=stream_cap
            )
            
            # Track real MMR penalty stats
            self.diag.add_rebalance_events(self.mmr_rebalancer.stats.nodes_penalized)
            
            # Map rebalanced results back to original nodes
            # Match by position in greedy selection (rebalancer picks incrementally)
            # Since we use dummy 1D vectors [score], match by score value
            rebalanced_stream = []
            selected_scores = {result[1] for result in rebalanced_results}  # base_score from result
            
            for node in candidates_for_stream:
                if node.get("score", 0.0) in selected_scores:
                    rebalanced_stream.append(node)
                    selected_scores.remove(node.get("score", 0.0))  # Avoid duplicates
                if len(rebalanced_stream) >= stream_cap:
                    break
        else:
            rebalanced_stream = candidates_for_stream
        
        # Assign to stream window
        self.st.stream_win.nodes = rebalanced_stream[:stream_cap]
        
        # Remaining nodes go to global (skip already selected stream nodes)
        stream_ids = {n["id"] for n in self.st.stream_win.nodes}
        remaining = [n for n in nodes_sorted if n["id"] not in stream_ids]
        self.st.global_win.nodes = remaining[:global_cap]
        
        # Precision assignment for stream (B.1 / Phase C+)
        if self.st.stream_win.nodes:
            stream_size = len(self.st.stream_win.nodes)
            avg_score = sum(n["score"] for n in self.st.stream_win.nodes) / stream_size
            old_precision = self.st.stream_win.precision
            
            if self.envelope_mode == "legacy":
                # Phase A: immediate precision assignment
                new_precision = assign_precision(avg_score)
            else:
                # Phase C+: hysteresis with dead band + dwell + rate limit
                # Safety guard: if stream too small, prevent upgrades
                target_precision = assign_precision(avg_score)
                
                if stream_size < self.hys_cfg.min_stream_for_upgrade:
                    # Too few samples for confident upgrade
                    # Use precision_level for safe comparison (not lexicographic)
                    if precision_level(target_precision) > precision_level(old_precision):
                        # Would be upgrade, but stream too small → keep current
                        new_precision = old_precision
                    else:
                        # Downgrade or same level → allow hysteresis logic
                        new_precision, self.hys_state_stream = assign_precision_hysteresis(
                            score=avg_score,
                            state=self.hys_state_stream,
                            config=self.hys_cfg,
                            current_tick=self.current_tick
                        )
                else:
                    # Normal hysteresis path (sufficient samples)
                    new_precision, self.hys_state_stream = assign_precision_hysteresis(
                        score=avg_score,
                        state=self.hys_state_stream,
                        config=self.hys_cfg,
                        current_tick=self.current_tick
                    )
            
            self.st.stream_win.precision = new_precision
            
            if old_precision != new_precision:
                self.diag.inc_envelope_changes()
        
        # Global window keeps default cold precision (mxfp4.12)
        self.st.global_win.precision = "mxfp4.12"
    
    def _fill_with_z_space(self, z: ZSliceLite) -> None:
        """Z-Space node selection (using ZSpaceShim for deterministic top-k).
        
        Phase 2: Uses orbis_z.ZSpaceShim for:
        - Deterministic top-k selection
        - Stream/global pool separation
        - Future: vec-based MMR diversity (when node.vec present)
        
        Args:
            z: Z-slice with nodes (optionally with vec embeddings)
        
        Behavior:
            - selector='z-space': Use ZSpaceShim.select_topk_for_stream()
            - Fallback to score-based if ZSpaceShim unavailable
            - Determinism preserved via combined RNG seed
        """
        # Check ZSpaceShim availability
        if not HAS_ZSPACE:
            # Graceful fallback to FAB selector
            return self._fill_with_fab_selector(z)
        
        # Initialize deterministic RNG from combined seeds
        z_seed = hash_to_seed(str(z.get("seed", "fab")))
        tick_seed = self.current_tick
        combined_seed = combine_seeds(z_seed, self.session_seed, tick_seed)
        self.rng = SeededRNG(seed=combined_seed)
        
        nodes = list(z.get("nodes", []))
        if not nodes:
            self.st.stream_win.nodes = []
            self.st.global_win.nodes = []
            return
        
        # Use ZSpaceShim for deterministic selection
        stream_cap = self.st.stream_win.cap_nodes
        global_cap = self.st.global_win.cap_nodes
        
        # Convert FAB ZSliceLite to orbis_z ZSliceLite format
        # Note: FAB uses Sequence, orbis_z uses list - cast for compatibility
        z_compat = {
            "nodes": list(z.get("nodes", [])),
            "edges": list(z.get("edges", [])),
            "quotas": z.get("quotas", {}),
            "seed": z.get("seed", "fab"),
            "zv": z.get("zv", "v0.1.0")
        }
        
        # Select top-k for stream using shim (pass RNG's internal Random object)
        stream_ids = ZSpaceShim.select_topk_for_stream(z_compat, k=stream_cap, rng=self.rng._rng)
        
        # Select top-k for global (excluding stream)
        global_ids = ZSpaceShim.select_topk_for_global(
            z_compat, k=global_cap, exclude_ids=set(stream_ids), rng=self.rng._rng
        )
        
        # Map IDs back to nodes (preserve full node data)
        node_map = {n["id"]: n for n in nodes}
        stream_nodes = [node_map[id] for id in stream_ids if id in node_map]
        global_nodes = [node_map[id] for id in global_ids if id in node_map]
        
        # Populate windows
        self.st.stream_win.nodes = stream_nodes
        self.st.global_win.nodes = global_nodes
        
        # Note: MMR stats will be integrated in Phase 2.1 (vec-based diversity)
        # For now, Z-Space uses score-based top-k (no MMR penalty)
        
        # Precision assignment for stream (same logic as FAB selector)
        if self.st.stream_win.nodes:
            stream_size = len(self.st.stream_win.nodes)
            avg_score = sum(n["score"] for n in self.st.stream_win.nodes) / stream_size
            old_precision = self.st.stream_win.precision
            
            if self.envelope_mode == "legacy":
                # Phase A: immediate precision assignment
                new_precision = assign_precision(avg_score)
            else:
                # Phase C+: hysteresis with dead band + dwell + rate limit
                target_precision = assign_precision(avg_score)
                
                if stream_size < self.hys_cfg.min_stream_for_upgrade:
                    # Tiny stream guard (same as FAB selector)
                    if precision_level(target_precision) > precision_level(old_precision):
                        new_precision = old_precision  # Prevent upgrade
                    else:
                        new_precision, self.hys_state_stream = assign_precision_hysteresis(
                            score=avg_score,
                            state=self.hys_state_stream,
                            config=self.hys_cfg,
                            current_tick=self.current_tick
                        )
                else:
                    # Normal hysteresis path
                    new_precision, self.hys_state_stream = assign_precision_hysteresis(
                        score=avg_score,
                        state=self.hys_state_stream,
                        config=self.hys_cfg,
                        current_tick=self.current_tick
                    )
            
            self.st.stream_win.precision = new_precision
            
            if old_precision != new_precision:
                self.diag.inc_envelope_changes()
        
        # Global window keeps default cold precision
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
        diag_snapshot = self.diag.snapshot()
        
        # Add derived metrics (C+.6)
        ticks = diag_snapshot["counters"]["ticks"]
        envelope_changes = diag_snapshot["counters"]["envelope_changes"]
        
        # changes_per_1k: envelope changes normalized per 1000 ticks (float for precision)
        if ticks > 0:
            changes_per_1k = (envelope_changes / ticks) * 1000.0
        else:
            changes_per_1k = 0.0
        
        # selected_diversity: variance of scores in stream window (observability metric)
        selected_diversity = 0.0
        if len(self.st.stream_win.nodes) > 1:
            scores = [n["score"] for n in self.st.stream_win.nodes]
            mean_score = sum(scores) / len(scores)
            variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
            selected_diversity = variance
        
        # MMR rebalance stats (P0.3: diversity observability)
        mmr_nodes_penalized = self.mmr_rebalancer.stats.nodes_penalized
        mmr_avg_penalty = self.mmr_rebalancer.stats.avg_penalty
        mmr_max_similarity = self.mmr_rebalancer.stats.max_similarity
        
        diag_snapshot["derived"] = {
            "changes_per_1k": changes_per_1k,
            "selected_diversity": selected_diversity,
            "mmr_nodes_penalized": mmr_nodes_penalized,
            "mmr_avg_penalty": mmr_avg_penalty,
            "mmr_max_similarity": mmr_max_similarity
        }
        
        ctx["diagnostics"] = diag_snapshot
        
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
