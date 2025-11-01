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
        selector: str = "fab",
        ab_shadow_enabled: bool = False,
        ab_ratio: float = 0.5,
        shadow_selector: str = "z-space",
        z_time_limit_ms: float = 5.0,
        z_cb_cooldown_ticks: int = 50,
        z_adapt_enabled: bool = True,
        z_target_latency_ms: float = 2.0,
        z_limit_min_ms: float = 1.0,
        z_limit_max_ms: float = 10.0,
        z_ai_step_ms: float = 0.25,
        z_md_factor: float = 0.5,
        # PR#5.5: Meta-adaptation (self-tuning target latency)
        z_meta_enabled: bool = True,
        z_meta_min_window: int = 20,
        z_meta_vol_threshold: float = 0.35,
        z_meta_target_bounds: tuple[float, float] = (1.0, 8.0),
        z_meta_adjust_step_ms: float = 0.25,
        # PR#5.6: Policy-Gating (Intention through Stability)
        policy_enabled: bool = True,
        policy_dwell_ticks: int = 5,
        # Thresholds for policy decisions (volatility / errors)
        policy_aggr_vol_max: float = 0.20,
        policy_cons_vol_min: float = 0.60,
        policy_error_cons_min: float = 0.05,
        # Multipliers applied per policy (aggressive / balanced / conservative)
        policy_aggr_ai_mult: float = 1.5,
        policy_aggr_md_mult: float = 0.9,
        policy_aggr_cb_mult: float = 0.5,
        policy_aggr_ab_mult: float = 1.2,
        policy_cons_ai_mult: float = 0.5,
        policy_cons_md_mult: float = 0.5,
        policy_cons_cb_mult: float = 1.5,
        policy_cons_ab_mult: float = 0.6
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
        
        # Phase 2.5: Shadow A/B selector (PR#5)
        if shadow_selector not in ("fab", "z-space"):
            raise ValueError(f"shadow_selector must be 'fab' or 'z-space', got {shadow_selector}")
        if not (0.0 <= ab_ratio <= 1.0):
            raise ValueError(f"ab_ratio must be in [0.0, 1.0], got {ab_ratio}")
        self.ab_shadow_enabled = ab_shadow_enabled
        self.ab_ratio = float(ab_ratio)
        self.shadow_selector = shadow_selector
        self.ab_last_used: bool = False
        self.ab_last_arm: str = self.selector  # effective selector used in last fill
        
        # PR#5.1: A/B per-arm counters and accumulators
        self.ab_arm_counts: dict[str, int] = {"fab": 0, "z-space": 0}
        self.ab_latency_sum: dict[str, float] = {"fab": 0.0, "z-space": 0.0}
        self.ab_diversity_gain_sum: dict[str, float] = {"fab": 0.0, "z-space": 0.0}
        self._ab_stats_last_tick: int = -1  # guard to avoid double-count per tick
        
        # PR#5.2: EMA and sliding window for z-space metrics
        self.z_ema_alpha: float = 0.1  # EMA smoothing factor (faster reaction)
        self.z_latency_ema: float = 0.0  # Exponential moving average of z_latency_ms
        self.z_gain_ema: float = 0.0  # Exponential moving average of z_diversity_gain
        self.z_window_size: int = 100  # Sliding window size for percentiles
        from collections import deque
        self.z_latency_window: deque = deque(maxlen=self.z_window_size)  # Last N latencies
        self.z_gain_window: deque = deque(maxlen=self.z_window_size)  # Last N gains

        # PR#5.3: Z-Space circuit breaker & hard time budget
        self.z_time_limit_ms: float = float(z_time_limit_ms)
        self.z_cb_cooldown_ticks: int = int(z_cb_cooldown_ticks)
        self.z_cb_remaining: int = 0  # ticks to force fallback to 'fab'

        # PR#5.3.1: Circuit breaker observability (reasons + counters)
        self.z_cb_reason: str = ""  # Last CB trigger reason ('timeout'/'exception'/'unavailable')
        self.z_cb_open_count: int = 0  # Total CB opens across session
        self.z_cb_reason_counts: dict[str, int] = {"timeout": 0, "exception": 0, "unavailable": 0}

        # PR#5.4: Adaptive time limit (AIMD)
        self.z_adapt_enabled: bool = bool(z_adapt_enabled)
        self.z_target_latency_ms: float = float(z_target_latency_ms)
        self.z_limit_min_ms: float = float(z_limit_min_ms)
        self.z_limit_max_ms: float = float(z_limit_max_ms)
        self.z_ai_step_ms: float = float(z_ai_step_ms)
        self.z_md_factor: float = float(z_md_factor)
        # Текущее адаптивное значение (зажимаем между min/max и hard cap)
        self.z_limit_current_ms: float = max(self.z_limit_min_ms, min(self.z_time_limit_ms, self.z_limit_max_ms))
        from collections import deque as _deque
        self.z_limit_history = _deque(maxlen=50)
        self.z_limit_last_adjust: str = ""

        # PR#5.5: Meta-adaptation (self-tuning target latency)
        self.z_meta_enabled: bool = bool(z_meta_enabled)
        self.z_meta_min_window: int = int(z_meta_min_window)
        self.z_meta_vol_threshold: float = float(z_meta_vol_threshold)
        self.z_meta_target_bounds: tuple[float, float] = (float(z_meta_target_bounds[0]), float(z_meta_target_bounds[1]))
        self.z_meta_adjust_step_ms: float = float(z_meta_adjust_step_ms)
        self.z_meta_last_decision: str = ""  # 'tighten'/'loosen'/'hold'/'none'
        self.z_meta_volatility: float = 0.0  # Normalized std of limit history
        self.z_meta_trend: float = 0.0  # EMA of latency delta
        self.z_latency_ema: float = 0.0  # Exponential moving average of latency

        # PR#5.6: Policy-Gating state
        self.policy_enabled: bool = bool(policy_enabled)
        self.policy_mode: str = "balanced"  # 'aggressive' | 'balanced' | 'conservative'
        self.policy_dwell_ticks: int = int(policy_dwell_ticks)
        self._policy_last_switch_tick: int = 0
        self._policy_dwell_remaining: int = 0
        # Thresholds
        self.policy_aggr_vol_max: float = float(policy_aggr_vol_max)
        self.policy_cons_vol_min: float = float(policy_cons_vol_min)
        self.policy_error_cons_min: float = float(policy_error_cons_min)
        # Multipliers
        self.policy_aggr_ai_mult: float = float(policy_aggr_ai_mult)
        self.policy_aggr_md_mult: float = float(policy_aggr_md_mult)
        self.policy_aggr_cb_mult: float = float(policy_aggr_cb_mult)
        self.policy_aggr_ab_mult: float = float(policy_aggr_ab_mult)
        self.policy_cons_ai_mult: float = float(policy_cons_ai_mult)
        self.policy_cons_md_mult: float = float(policy_cons_md_mult)
        self.policy_cons_cb_mult: float = float(policy_cons_cb_mult)
        self.policy_cons_ab_mult: float = float(policy_cons_ab_mult)
        
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
        
        # Phase 2: Z-Space diagnostics (PR#2)
        self.z_last_latency_ms: float = 0.0
        self.z_last_diversity_gain: float = 0.0
        self.z_last_baseline_div: float = 0.0  # PR#3: FAB baseline diversity for gain calc
    
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
        
        # PR#5.6: Update policy once per tick (before fills/mix)
        try:
            self._policy_update()
        except Exception:
            pass
        
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
        
        # Route to selector-specific implementation (with Shadow A/B if enabled)
        chosen_selector = self.selector
        self.ab_last_used = False
        self.ab_last_arm = chosen_selector

        if self.ab_shadow_enabled:
            # Deterministic A/B choice per tick using combined seeds (z.seed, session_seed, current_tick)
            z_seed = hash_to_seed(str(z.get("seed", "fab")))
            tick_seed = self.current_tick
            ab_seed = combine_seeds(z_seed, self.session_seed, tick_seed)
            # Use Python's Random via SeededRNG to draw a stable float in [0,1)
            ab_rng = SeededRNG(seed=ab_seed)
            roll = ab_rng.random()
            # Policy-adjusted A/B probability
            ab_ratio = self._policy_ab_ratio()
            if roll < ab_ratio:
                chosen_selector = self.shadow_selector
                self.ab_last_used = True
                self.ab_last_arm = chosen_selector
            else:
                self.ab_last_used = False
                self.ab_last_arm = self.selector

        # PR#5.3: If circuit breaker is open, force 'fab' for this tick
        if getattr(self, "z_cb_remaining", 0) > 0:
            chosen_selector = "fab"
            self.ab_last_used = False
            self.ab_last_arm = "fab"
            self.z_cb_remaining -= 1

        if chosen_selector == "z-space":
            return self._fill_with_z_space(z)
        else:
            # Default: original FAB selection (Phase A/B/C+)
            return self._fill_with_fab_selector(z)
    
    def _fill_with_fab_selector(self, z: ZSliceLite) -> None:
        """Original FAB node selection (score-based sort + MMR).
        
        This preserves Phase A/B/C+ behavior for backward compatibility.
        Used when selector='fab' (default).
        
        Phase 2 PR#2: Resets Z-Space diagnostics (not used in FAB mode)
        """
        # PR#2/PR#3: Reset Z-Space metrics (FAB selector doesn't use them)
        self.z_last_latency_ms = 0.0
        self.z_last_diversity_gain = 0.0
        self.z_last_baseline_div = 0.0
        
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
    
    def _simulate_fab_stream_diversity(self, z: ZSliceLite, *, combined_seed: int, stream_cap: int) -> float:
        """
        PR#3 helper: локальная симуляция FAB-селектора для оценки baseline diversity
        (дисперсия скорингов в отобранном stream), без мутаций self.st/diagnostics.
        """
        from .seeding import deterministic_sort
        local_rng = SeededRNG(seed=combined_seed)

        nodes = list(z.get("nodes", []))
        if not nodes or stream_cap <= 0:
            return 0.0

        # Тот же детерминированный sort, что и в FAB-пути
        items_with_scores = [(n, n.get("score", 0.0)) for n in nodes]
        sorted_tuples = deterministic_sort(
            items=items_with_scores,
            rng=local_rng,
            key_index=1,
            reverse=True
        )
        nodes_sorted = [item for item, score in sorted_tuples]

        candidates_for_stream = nodes_sorted[:min(len(nodes_sorted), stream_cap * 2)]

        # Та же MMR-логика (1D-вектора по score), что и в FAB
        if len(candidates_for_stream) > stream_cap:
            candidates_mmr = [([float(node.get("score", 0.0))], node.get("score", 0.0)) for node in candidates_for_stream]
            local_rebalancer = MMRRebalancer(self.mmr_cfg)
            rebalanced_results = local_rebalancer.rebalance_batch(
                candidates=candidates_mmr,
                existing_nodes=[],
                top_k=stream_cap
            )
            rebalanced_stream = []
            selected_scores = {result[1] for result in rebalanced_results}
            for node in candidates_for_stream:
                if node.get("score", 0.0) in selected_scores:
                    rebalanced_stream.append(node)
                    selected_scores.remove(node.get("score", 0.0))
                if len(rebalanced_stream) >= stream_cap:
                    break
        else:
            rebalanced_stream = candidates_for_stream

        scores = [n.get("score", 0.0) for n in rebalanced_stream]
        if len(scores) <= 1:
            return 0.0

        mean_score = sum(scores) / len(scores)
        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
        return variance
    
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
        
        Phase 2 PR#2: Tracks latency and diversity gain for diagnostics
        Phase 2 PR#5.3: Circuit breaker + hard time budget
        Phase 2 PR#5.4: Adaptive time limit (AIMD)
        """
        import time
        
        # PR#5.4: Combine adaptive limit, hard cap, and external quota
        z_quotas = z.get("quotas", {}) or {}
        quota_ms = float(z_quotas.get("time_ms", float("inf")) or float("inf"))
        base_limit = self.z_limit_current_ms if getattr(self, "z_adapt_enabled", False) else self.z_time_limit_ms
        hard_cap = self.z_time_limit_ms if self.z_time_limit_ms > 0.0 else float("inf")
        effective_limit_ms = min(base_limit, hard_cap, quota_ms)

        try:
            # Immediate timeout if budget is 0
            if effective_limit_ms <= 0.0:
                raise TimeoutError("z-space time budget is zero")
            
            # Check ZSpaceShim availability
            if not HAS_ZSPACE:
                raise RuntimeError("ZSpaceShim unavailable")
            
            # Start latency tracking (PR#2)
            t_start = time.perf_counter()
            
            # Initialize deterministic RNG from combined seeds
            z_seed = hash_to_seed(str(z.get("seed", "fab")))
            tick_seed = self.current_tick
            combined_seed = combine_seeds(z_seed, self.session_seed, tick_seed)
            self.rng = SeededRNG(seed=combined_seed)
            
            # PR#3: baseline FAB diversity
            stream_cap = self.st.stream_win.cap_nodes
            baseline_div = self._simulate_fab_stream_diversity(
                z, combined_seed=combined_seed, stream_cap=stream_cap
            )
            self.z_last_baseline_div = baseline_div

            # Early timeout check before heavy work
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            if elapsed_ms > effective_limit_ms:
                raise TimeoutError(f"z-space selection time budget exceeded pre-select ({elapsed_ms:.3f}ms > {effective_limit_ms:.3f}ms)")
            
            nodes = list(z.get("nodes", []))
            if not nodes:
                self.st.stream_win.nodes = []
                self.st.global_win.nodes = []
                self.z_last_diversity_gain = 0.0
                self.z_last_baseline_div = 0.0
                self.z_last_latency_ms = (time.perf_counter() - t_start) * 1000.0
                return
            
            # Use ZSpaceShim for deterministic selection
            global_cap = self.st.global_win.cap_nodes
            z_compat = {
                "nodes": list(z.get("nodes", [])),
                "edges": list(z.get("edges", [])),
                "quotas": z.get("quotas", {}),
                "seed": z.get("seed", "fab"),
                "zv": z.get("zv", "v0.1.0"),
            }
            stream_ids = ZSpaceShim.select_topk_for_stream(z_compat, k=stream_cap, rng=self.rng._rng)

            # Timeout check after stream selection
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            if elapsed_ms > effective_limit_ms:
                raise TimeoutError(f"z-space selection time budget exceeded after stream ({elapsed_ms:.3f}ms > {effective_limit_ms:.3f}ms)")

            global_ids = ZSpaceShim.select_topk_for_global(
                z_compat, k=global_cap, exclude_ids=set(stream_ids), rng=self.rng._rng
            )
            
            # Map IDs back to nodes
            node_map = {n["id"]: n for n in nodes}
            stream_nodes = [node_map[i] for i in stream_ids if i in node_map]
            global_nodes = [node_map[i] for i in global_ids if i in node_map]
            self.st.stream_win.nodes = stream_nodes
            self.st.global_win.nodes = global_nodes
            
            # Precision assignment for stream (same logic as FAB selector)
            if self.st.stream_win.nodes:
                stream_size = len(self.st.stream_win.nodes)
                avg_score = sum(n["score"] for n in self.st.stream_win.nodes) / stream_size
                old_precision = self.st.stream_win.precision
                if self.envelope_mode == "legacy":
                    new_precision = assign_precision(avg_score)
                else:
                    target_precision = assign_precision(avg_score)
                    if stream_size < self.hys_cfg.min_stream_for_upgrade:
                        if precision_level(target_precision) > precision_level(old_precision):
                            new_precision = old_precision
                        else:
                            new_precision, self.hys_state_stream = assign_precision_hysteresis(
                                score=avg_score,
                                state=self.hys_state_stream,
                                config=self.hys_cfg,
                                current_tick=self.current_tick
                            )
                    else:
                        new_precision, self.hys_state_stream = assign_precision_hysteresis(
                            score=avg_score,
                            state=self.hys_state_stream,
                            config=self.hys_cfg,
                            current_tick=self.current_tick
                        )
                self.st.stream_win.precision = new_precision
                if old_precision != new_precision:
                    self.diag.inc_envelope_changes()
            self.st.global_win.precision = "mxfp4.12"

            # PR#3: diversity gain
            if self.st.stream_win.nodes and len(self.st.stream_win.nodes) > 1:
                stream_scores = [n["score"] for n in self.st.stream_win.nodes]
                mean_score = sum(stream_scores) / len(stream_scores)
                z_variance = sum((s - mean_score) ** 2 for s in stream_scores) / len(stream_scores)
            else:
                z_variance = 0.0
            self.z_last_diversity_gain = max(0.0, z_variance - self.z_last_baseline_div)
            self.z_last_latency_ms = (time.perf_counter() - t_start) * 1000.0

            # PR#5.4: Adaptive update on success
            try:
                self._z_adapt("success", self.z_last_latency_ms)
            except Exception:
                pass

        except Exception as e:
            # PR#5.3.1: Determine CB reason from exception type
            if isinstance(e, TimeoutError):
                reason = "timeout"
            elif isinstance(e, RuntimeError) and "unavailable" in str(e).lower():
                reason = "unavailable"
            else:
                reason = "exception"
            
            # Open circuit breaker with reason tracking
            self._z_open_circuit_breaker(reason)
            
            # PR#5.4: Adaptive decrease on failure
            try:
                self._z_adapt(reason if reason in ("timeout", "exception", "unavailable") else "cb_open", None)
            except Exception:
                pass
            
            try:
                self.z_last_latency_ms = (time.perf_counter() - locals().get("t_start", time.perf_counter())) * 1000.0
            except Exception:
                self.z_last_latency_ms = 0.0
            self.z_last_diversity_gain = 0.0
            self.z_last_baseline_div = 0.0
            return self._fill_with_fab_selector(z)
    
    def _z_adapt(self, outcome: str, observed_latency_ms: float | None = None) -> None:
        """PR#5.4: Adaptive time limit (AIMD-like).
        
        Args:
            outcome: "success", "timeout", "exception", "unavailable", "cb_open"
            observed_latency_ms: Actual latency for success case
        """
        if not getattr(self, "z_adapt_enabled", False):
            self.z_limit_last_adjust = "none"
            return
        
        cur = float(getattr(self, "z_limit_current_ms", self.z_time_limit_ms))
        new_val = cur
        
        if outcome == "success" and observed_latency_ms is not None:
            # Additive Increase: if latency <= target, increase limit
            if observed_latency_ms <= self.z_target_latency_ms:
                new_val = cur + self._policy_ai_step_ms()
                self.z_limit_last_adjust = "increase"
            else:
                # Latency above target, don't adjust
                self.z_limit_last_adjust = "none"
        else:
            # Multiplicative Decrease: on timeout/exception/unavailable
            new_val = cur * self._policy_md_factor()
            self.z_limit_last_adjust = "decrease"
        
        # Clamp to [min, max] and hard cap
        hard_cap = self.z_time_limit_ms if self.z_time_limit_ms > 0.0 else float("inf")
        cap_upper = min(self.z_limit_max_ms, hard_cap)
        cap_lower = max(0.0, self.z_limit_min_ms)
        new_val = max(cap_lower, min(cap_upper, new_val))
        
        if new_val != cur:
            self.z_limit_current_ms = new_val
        
        # PR#5.5: Meta-learn before tracking history
        try:
            self._z_meta_learn(observed_latency_ms)
        except Exception:
            pass
        
        # Track history for observability
        try:
            self.z_limit_history.append(float(self.z_limit_current_ms))
        except Exception:
            pass
    
    def _z_meta_learn(self, observed_latency_ms: float | None = None) -> None:
        """PR#5.5: Meta-adaptation (self-tuning target latency).
        
        Observes limit volatility and latency trends to adjust z_target_latency_ms:
        - tighten: Reduce target when stable and fast (low volatility, non-positive trend)
        - loosen: Increase target when unstable or slowing (high volatility or positive trend)
        - hold: No change
        
        Args:
            observed_latency_ms: Current latency measurement (for EMA tracking)
        """
        if not getattr(self, "z_meta_enabled", False):
            self.z_meta_last_decision = "none"
            return
        
        # Update latency EMA (α=0.2 for responsiveness)
        if observed_latency_ms is not None:
            if self.z_latency_ema == 0.0:
                self.z_latency_ema = observed_latency_ms
            else:
                alpha = 0.2
                delta = observed_latency_ms - self.z_latency_ema
                self.z_latency_ema = self.z_latency_ema + alpha * delta
                # Update trend (EMA of delta)
                self.z_meta_trend = self.z_meta_trend + alpha * (delta - self.z_meta_trend)
        
        # Need minimum window for volatility calculation
        if len(self.z_limit_history) < self.z_meta_min_window:
            self.z_meta_last_decision = "none"
            return
        
        # Calculate volatility (coefficient of variation)
        window = list(self.z_limit_history)[-self.z_meta_min_window:]
        try:
            mean_limit = sum(window) / len(window)
            if mean_limit > 0.0:
                variance = sum((x - mean_limit) ** 2 for x in window) / len(window)
                std_limit = variance ** 0.5
                self.z_meta_volatility = std_limit / mean_limit  # Normalized
            else:
                self.z_meta_volatility = 0.0
        except Exception:
            self.z_meta_volatility = 0.0
            self.z_meta_last_decision = "none"
            return
        
        # Decision logic
        current_target = self.z_target_latency_ms
        new_target = current_target
        
        # tighten: stable (low volatility) and fast/steady (trend <= 0)
        if self.z_meta_volatility < self.z_meta_vol_threshold and self.z_meta_trend <= 0.0:
            new_target = current_target - self.z_meta_adjust_step_ms
            self.z_meta_last_decision = "tighten"
        # loosen: unstable (high volatility) or slowing (trend > 0)
        elif self.z_meta_volatility >= self.z_meta_vol_threshold or self.z_meta_trend > 0.0:
            new_target = current_target + self.z_meta_adjust_step_ms
            self.z_meta_last_decision = "loosen"
        else:
            self.z_meta_last_decision = "hold"
        
        # Clamp to meta target bounds
        min_target, max_target = self.z_meta_target_bounds
        new_target = max(min_target, min(max_target, new_target))
        
        if new_target != current_target:
            self.z_target_latency_ms = new_target
    
    def _policy_update(self) -> None:
        """PR#5.6: Evaluate and (optionally) switch behavioral policy.

        Policies:
          - aggressive: low volatility, stable, no CB → faster exploration/adaptation
          - balanced: default
          - conservative: high volatility, errors/CB → safety first

        Hysteresis via dwell: require policy_dwell_ticks before switching again.
        """
        if not getattr(self, "policy_enabled", False):
            return

        # Respect dwell to avoid flapping
        if self._policy_dwell_remaining > 0:
            self._policy_dwell_remaining -= 1
            return

        vol = float(getattr(self, "z_meta_volatility", 0.0) or 0.0)
        cb_open = bool(getattr(self, "z_cb_remaining", 0) > 0)
        err_rate = float(self.st.metrics.get("error_rate", 0.0) if getattr(self, "st", None) and getattr(self, "st").metrics is not None else 0.0)

        target_mode = "balanced"
        # Conservative if volatility high OR CB open OR error rate above threshold
        # (safety-first tie-break: prefer conservative when conditions overlap)
        if vol >= self.policy_cons_vol_min or cb_open or err_rate >= self.policy_error_cons_min:
            target_mode = "conservative"
        # Aggressive if volatility low, no CB, and low error rate
        elif vol <= self.policy_aggr_vol_max and not cb_open and err_rate < self.policy_error_cons_min * 0.5:
            target_mode = "aggressive"

        if target_mode != self.policy_mode:
            self.policy_mode = target_mode
            self._policy_last_switch_tick = int(getattr(self, "current_tick", 0))
            self._policy_dwell_remaining = max(int(self.policy_dwell_ticks), 0)

    # Effective parameter helpers
    def _policy_ai_step_ms(self) -> float:
        base = float(getattr(self, "z_ai_step_ms", 0.25))
        if not getattr(self, "policy_enabled", False):
            return base
        if self.policy_mode == "aggressive":
            val = base * self.policy_aggr_ai_mult
        elif self.policy_mode == "conservative":
            val = base * self.policy_cons_ai_mult
        else:
            val = base
        # Clamp to reasonable bounds (min=0.01ms, max=10.0ms)
        return max(0.01, min(10.0, val))

    def _policy_md_factor(self) -> float:
        base = float(getattr(self, "z_md_factor", 0.5))
        if not getattr(self, "policy_enabled", False):
            return base
        if self.policy_mode == "aggressive":
            return max(0.05, min(0.99, base * self.policy_aggr_md_mult))
        if self.policy_mode == "conservative":
            return max(0.05, min(0.99, base * self.policy_cons_md_mult))
        return base

    def _policy_cb_cooldown_ticks(self) -> int:
        base = int(getattr(self, "z_cb_cooldown_ticks", 50))
        if not getattr(self, "policy_enabled", False):
            return base
        if self.policy_mode == "aggressive":
            return max(1, int(round(base * self.policy_aggr_cb_mult)))
        if self.policy_mode == "conservative":
            return max(1, int(round(base * self.policy_cons_cb_mult)))
        return base

    def _policy_ab_ratio(self) -> float:
        base = float(getattr(self, "ab_ratio", 0.5))
        if not getattr(self, "policy_enabled", False):
            return base
        if self.policy_mode == "aggressive":
            return max(0.0, min(1.0, base * self.policy_aggr_ab_mult))
        if self.policy_mode == "conservative":
            return max(0.0, min(1.0, base * self.policy_cons_ab_mult))
        return base
    
    def _z_open_circuit_breaker(self, reason: str) -> None:
        """PR#5.3.1: Open circuit breaker with tracking.
        
        Args:
            reason: CB trigger reason ('timeout', 'exception', 'unavailable')
        """
        # Apply policy-adjusted cooldown
        self.z_cb_remaining = max(self._policy_cb_cooldown_ticks(), 1)
        self.z_cb_reason = reason
        self.z_cb_open_count += 1
        self.z_cb_reason_counts[reason] = self.z_cb_reason_counts.get(reason, 0) + 1
        self.ab_last_arm = "fab"  # Mark fallback in diagnostics
    
    def _z_percentile(self, values: list[float], p: float) -> float:
        """PR#5.2: Calculate percentile from sorted values.
        
        Args:
            values: List of numeric values
            p: Percentile (0.0-1.0, e.g., 0.95 for p95)
        
        Returns:
            Percentile value, or 0.0 if empty
        """
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        k = (len(sorted_vals) - 1) * p
        f = int(k)
        c = f + 1
        if c >= len(sorted_vals):
            return sorted_vals[-1]
        # Linear interpolation between floor and ceil
        return sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f])
    
    def _ab_safe_avg(self, s: float, n: int) -> float:
        """PR#5.1: Safe division for averages (avoid division by zero)"""
        return s / n if n > 0 else 0.0

    def _ab_record_metrics_for_current_tick(self) -> None:
        """PR#5.1/5.2: Update per-arm counters and z-metrics exactly once per tick.
        
        Updates:
        - PR#5.1: A/B arm counters/sums (only if ab_shadow_enabled)
        - PR#5.2: Z-Space EMA/window (always for z-space selector)
        
        Guard (_ab_stats_last_tick) prevents double-counting on multiple mix() calls.
        """
        if self._ab_stats_last_tick == self.current_tick:
            return
        
        arm = self.ab_last_arm
        if arm not in ("fab", "z-space"):
            return
        
        # PR#5.2: Always update EMA/window for z-space (regardless of A/B)
        if arm == "z-space":
            latency = float(getattr(self, "z_last_latency_ms", 0.0) or 0.0)
            gain = float(getattr(self, "z_last_diversity_gain", 0.0) or 0.0)
            
            # Update EMA (exponential moving average)
            z_count = self.ab_arm_counts.get("z-space", 0)
            if z_count == 0:
                # First value: initialize EMA
                self.z_latency_ema = latency
                self.z_gain_ema = gain
            else:
                # EMA update: new_ema = alpha * new_value + (1 - alpha) * old_ema
                self.z_latency_ema = self.z_ema_alpha * latency + (1 - self.z_ema_alpha) * self.z_latency_ema
                self.z_gain_ema = self.z_ema_alpha * gain + (1 - self.z_ema_alpha) * self.z_gain_ema
            
            # Update sliding window (deque auto-evicts oldest when full)
            self.z_latency_window.append(latency)
            self.z_gain_window.append(gain)
        
        # PR#5.1: Update A/B counters/sums (only if A/B enabled)
        if not self.ab_shadow_enabled:
            self._ab_stats_last_tick = self.current_tick
            return
        
        self.ab_arm_counts[arm] += 1
        if arm == "z-space":
            latency = float(getattr(self, "z_last_latency_ms", 0.0) or 0.0)
            gain = float(getattr(self, "z_last_diversity_gain", 0.0) or 0.0)
            self.ab_latency_sum[arm] += latency
            self.ab_diversity_gain_sum[arm] += gain
        else:
            self.ab_latency_sum[arm] += 0.0
            self.ab_diversity_gain_sum[arm] += 0.0
        self._ab_stats_last_tick = self.current_tick
    
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
        
        # PR#5.1: update A/B per-arm stats once per tick
        try:
            self._ab_record_metrics_for_current_tick()
        except Exception:
            # diagnostics should not break main flow
            pass
        
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
        
        # PR#2/PR#5: Z-Space diagnostics (use ab_last_arm for A/B compatibility)
        z_selector_used = self.ab_last_arm == "z-space"
        z_diversity_gain = self.z_last_diversity_gain
        z_latency_ms = self.z_last_latency_ms
        
        diag_snapshot["derived"] = {
            "changes_per_1k": changes_per_1k,
            "selected_diversity": selected_diversity,
            "mmr_nodes_penalized": mmr_nodes_penalized,
            "mmr_avg_penalty": mmr_avg_penalty,
            "mmr_max_similarity": mmr_max_similarity,
            "z_selector_used": z_selector_used,
            "z_baseline_diversity": self.z_last_baseline_div,  # PR#3
            "z_diversity_gain": z_diversity_gain,
            "z_latency_ms": z_latency_ms,
            "ab_shadow_enabled": self.ab_shadow_enabled,
            "ab_ratio": self.ab_ratio,
            "ab_arm": self.ab_last_arm,
            "ab_counts": {
                "fab": self.ab_arm_counts.get("fab", 0),
                "z-space": self.ab_arm_counts.get("z-space", 0),
            },
            "ab_latency_avg": {
                "fab": self._ab_safe_avg(self.ab_latency_sum.get("fab", 0.0), self.ab_arm_counts.get("fab", 0)),
                "z-space": self._ab_safe_avg(self.ab_latency_sum.get("z-space", 0.0), self.ab_arm_counts.get("z-space", 0)),
            },
            "ab_diversity_gain_avg": {
                "fab": self._ab_safe_avg(self.ab_diversity_gain_sum.get("fab", 0.0), self.ab_arm_counts.get("fab", 0)),
                "z-space": self._ab_safe_avg(self.ab_diversity_gain_sum.get("z-space", 0.0), self.ab_arm_counts.get("z-space", 0)),
            },
            "z_latency_ema": self.z_latency_ema,
            "z_gain_ema": self.z_gain_ema,
            "z_latency_p50": self._z_percentile(list(self.z_latency_window), 0.50),
            "z_latency_p95": self._z_percentile(list(self.z_latency_window), 0.95),
            "z_latency_p99": self._z_percentile(list(self.z_latency_window), 0.99),
            "z_gain_p50": self._z_percentile(list(self.z_gain_window), 0.50),
            "z_gain_p95": self._z_percentile(list(self.z_gain_window), 0.95),
            "z_gain_p99": self._z_percentile(list(self.z_gain_window), 0.99),
            "z_window_size": len(self.z_latency_window),
            "zspace_cb_open": self.z_cb_remaining > 0,
            "zspace_cb_cooldown_remaining": int(self.z_cb_remaining),
            "zspace_cb_reason": self.z_cb_reason,
            "zspace_cb_open_count": self.z_cb_open_count,
            "zspace_cb_reason_counts": dict(self.z_cb_reason_counts),
            "z_adapt_enabled": self.z_adapt_enabled,
            "z_limit_current_ms": self.z_limit_current_ms,
            "z_target_latency_ms": self.z_target_latency_ms,
            "z_limit_min_ms": self.z_limit_min_ms,
            "z_limit_max_ms": self.z_limit_max_ms,
            "z_limit_last_adjust": self.z_limit_last_adjust,
            "z_meta_enabled": self.z_meta_enabled,
            "z_meta_last_decision": self.z_meta_last_decision,
            "z_meta_volatility": self.z_meta_volatility,
            "z_meta_trend": self.z_meta_trend,
            "z_meta_target_bounds": self.z_meta_target_bounds,
            "policy_enabled": self.policy_enabled,
            "policy_mode": self.policy_mode,
            "policy_dwell_remaining": int(getattr(self, "_policy_dwell_remaining", 0)),
            "policy_last_switch_tick": int(getattr(self, "_policy_last_switch_tick", 0)),
            "policy_effective_ai_step_ms": self._policy_ai_step_ms(),
            "policy_effective_md_factor": self._policy_md_factor(),
            "policy_effective_cb_cooldown": self._policy_cb_cooldown_ticks(),
            "policy_effective_ab_ratio": self._policy_ab_ratio()
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
