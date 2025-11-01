# AURIS · FAB — Phase C Integration Complete & Next Steps (C+)

**Date:** 2025-10-29 20:40  
**Branch:** `fab`  
**Status:** 93/93 tests passing; Phase A + Phase B units ✅

---

## What’s done
- Phase C: integrated B.1–B.5 modules into FABCore with full test pass.
- Precision: Phase‑A‑compatible path (`assign_precision`) active; hysteresis wired but bypassed for legacy tests.
- Stability: `StabilityTracker` (min_stable_ticks=3 for compatibility).
- MMR Rebalance: diversity in `fill()` selection; deterministic seeding for reproducibility.
- Diagnostics: counters + gauges included in `mix()` context.

## Decisions locked for now
- Keep hysteresis configured but disabled in FABCore by default (`dwell_time=0`, `rate_limit=1`) to maintain Phase‑A semantics.
- Reset `stable_ticks` **only** on FAB0→FAB1 transition (no stability requirement), preserve on FAB1→FAB2 (evidence‑driven promotion).
- Global window fixed to `mxfp4.12`; Stream precision computed from average score (legacy behavior).

## Next steps (Phase C+)
**C+.1 — Expose FAB v0.1 Shadow Mode routes**
- `POST /api/v1/fab/context/push` — feed Z‑slice; returns diagnostics snapshot
- `GET  /api/v1/fab/context/pull` — current windows + gauges
- `POST /api/v1/fab/decide` — runs `step_stub()` with current metrics
- `POST /api/v1/fab/act` — placeholder (no external I/O yet)

**C+.2 — Diagnostic assertions in integration tests**
- Augment existing Phase A tests to assert `ctx["diagnostics"]` counters/gauges
- Golden snapshot for stable scenarios (seeded)

**C+.3 — Hysteresis rollout switch**
- `FAB_SETTINGS.envelope_mode`: `'legacy'|'hysteresis'`
- Config surface: `dwell_time=3`, `rate_limit_ticks=1000`, `bands=[hot,warm,dead]`
- A/B test flag in tests to validate non‑regression

**C+.4 — MMR tuning & caps**
- λ sweep: (0.3, 0.5, 0.7); `distance_threshold` sweep: (0.2, 0.3, 0.4)
- Hard caps: `max_penalty`, `max_nodes_penalized` per fill
- Telemetry: `avg_penalty`, `max_similarity` in diagnostics

**C+.5 — Seed discipline**
- Propagate `z_slice.seed` across tick for full determinism
- Add `combine_seeds(session_id, tick_id, z_seed)` utility

**C+.6 — Operational SLO hooks (non‑blocking)**
- Expose `changes_per_1k_ticks` & `rebalance_per_fill` via metrics endpoint
- Warn if `envelope_changes` spikes > threshold

## Risks & mitigations
- **Precision flip‑flop on rollout of hysteresis**  
  Mitigation: keep `'legacy'` default; enable via flag. Add dead‑band + rate limit validated by unit tests.
- **Transition semantics divergence with StabilityTracker**  
  Mitigation: preserve Phase‑A by special‑casing FAB0→FAB1 reset; keep FAB1→FAB2 evidence count.
- **Determinism drift between `fill()` and `rebalance()`**  
  Mitigation: enforce `SeededRNG` for both; add integration test with fixed seed & golden snapshot.

## Checklist to execute now
- [ ] Add `envelope_mode` flag in `FABCore.__init__` (`legacy|hysteresis`)
- [ ] Wire diagnostics into all `mix()` call sites (already in place)
- [ ] Create `tests/test_fab_diagnostics_integration.py` with 3 happy‑paths
- [ ] Draft API stubs for Shadow Mode routes (no network I/O)
