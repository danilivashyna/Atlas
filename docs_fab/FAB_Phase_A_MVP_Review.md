FAB Phase A MVP — Review & Next Steps
Status: Completed (branch: fab). All 40/40 tests passing. Autonomous core without external deps.
Quick Verification Checklist (Pass)
• Budgets fixed per tick; no mid-tick changes
• Global+Stream ≤ budgets.nodes; caps enforced (Stream≤128, Global≤256)
• High-score → Stream, lower-score → Global; no duplication
• Bit-envelope: Stream precision from avg score; Global fixed mxfp4.12
• State machine: FAB0→FAB1 (self_presence≥0.8 & stress<0.7); FAB1→FAB2 after 3 stable ticks; degrade on stress/error
• Backpressure bands: ok/slow/reject thresholds applied (unit-tested)
• mix() snapshot matches internal state (keys & values)
Phase B — Implementation Plan (Hysteresis & Stability)
Scope: keep FAB isolated. No Atlas/OneBlock I/O.
1) Bit-envelope hysteresis: ≤1 precision change/sec/layer; up/down thresholds with dwell time
1) Window stability counter: exponential backoff on oscillations; cool-down after degradations
1) Stream/Global rebalancer: soft MMR-like coverage with score decay; guard total cost ≤ Budgets
1) Deterministic seeding: incorporate z_slice.seed into any randomized tie-breakers
1) Diagnostics: counters for envelope_changes/sec and mode_transitions (for Mensum later)
Additional Tests to Add (Phase B)
• Hysteresis: precision does NOT toggle when avg score hovers around a threshold
• Stability: require N stable ticks before FAB1→FAB2; reset on stress spike
• Backpressure edges: exactly 2000/5000 tokens go to slow/reject as defined
• Rebalance: total nodes remain within cap after repeated fill() calls with different Z-slices
• No duplication: union(Stream,Global) has unique node ids
Risk Notes & Guardrails
- Avoid implicit I/O or imports from Atlas/HSI; keep package pure.
- Keep budgets & thresholds configurable via constructor args (future metrics tuning).
- Do not introduce time-based code that depends on system clock into logic; inject clock for tests.
- Prefer pure functions for policies (envelope/backpressure) to ease property testing.
Minimal Public API (Phase A/B)
- FABCore.init_tick(mode: FabMode, budgets: Budgets)
- FABCore.fill(z: ZSliceLite)
- FABCore.mix() -> dict(snapshot)  # includes global_precision & stream_precision
- FABCore.step_stub(stress, self_presence, error_rate) -> dict(mode, stable_ticks)

Prepared by: Auris HSI • Date: 2025-10-29 (Europe/Kyiv)
