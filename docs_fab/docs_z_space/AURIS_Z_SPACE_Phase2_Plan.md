AURIS FAB → Z-Space: Phase 1 Recap & Phase 2 Plan
 
Status Summary
Branches: fab (P0 patches merged), z-space (v0.1 skeleton + tests).
Tests: FAB Phase A/B: 59; FAB Phase C+: 31; Z-Space: 13 → Total: 103/103 passing.
What’s Done (v0.1)
• P0 patches merged to fab: config consolidation, 4 edge tests, MMR stats in diagnostics.
• Z-Space skeleton (orbis_z): contracts, shim, selector; fully decoupled from FABCore.
• Typed support for vec in orbis_fab.types.ZNode (backward compatible).
• Determinism confirmed with SeededRNG discipline and tests.
Phase 2 Goals (Integration & Vectors)
• Integrate ZSpaceShim into FABCore.fill() behind a feature flag (selector='fab'|'z-space'), default='fab'.
• Enable vec-based diversity via ZSelector when node.vec exists; fallback to score-only otherwise.
• Preserve determinism: combined_seed = combine_seeds(z_seed, session_seed, tick_seed).
• Expose observability: z_selector_used, z_diversity_gain, z_latency_ms in diagnostics.
Proposed Config & API
• FABCore(selector='fab'|'z-space', envelope_mode='legacy'|'hysteresis').
• Shadow Mode routes reuse: /api/v1/fab/context/* (no external I/O).
• Optional: /api/v1/z/selector?mode=mmr|score for A/B.
Test Plan (Add ~20 tests)
• Determinism parity: FABCore(fill using ZSpaceShim) vs previous order on equal inputs.
• Mixed vec presence: ensure graceful fallback and stable selection.
• Budget/quotas respect with large n (nodes>>caps); no overlap stream/global.
• Envelope compatibility: legacy/hysteresis upgrade/downgrade with z-space enabled.
• Seeding discipline across budgets: budget changes don’t alter selection when cap unchanged.
• Stress tests: cluster imbalance (90/10), verify diversity improvement and latency < 5ms.
• Edge cases: empty slice, tiny stream (< min_stream_for_upgrade), unknown precision, runtime mode switch.
Metrics & SLOs
• z_selector_used (bool), z_diversity_gain (float: selected_diversity_after − before).
• z_latency_ms (per tick), mmr_nodes_penalized/avg_penalty/max_similarity passthrough.
• Alert: changes_per_1k > threshold and z_latency_ms p95 > 5ms.
Rollout Plan
• Stage 0: selector='fab' (baseline).
• Stage 1: selector='z-space' in Shadow Mode only; record metrics.
• Stage 2: A/B 10% traffic with vec-enabled nodes; compare diversity & latency.
• Stage 3: Gradual ramp to 50–100% if SLOs hold.
Key Risks & Mitigations
• Performance regressions from MMR: keep vectors small (2–64 dims), early exit at top_k, cache norms.
• Precision oscillations under new selection: keep hysteresis guard and min_stream_for_upgrade.
• Determinism drift: single RNG per tick; avoid re-seeding mid-fill.
Next Actions (Proposed PR sequence)
• PR#1: Add selector flag to FABCore; wire ZSpaceShim under 'z-space' (no behavior change by default).
• PR#2: Hook diagnostics (z_selector_used, z_diversity_gain, z_latency_ms) + tests.
• PR#3: Enable ZSelector (vec) path with fallback; add mixed-vec tests.
• PR#4: Shadow Mode soak + A/B harness; add SLO dashboards.
