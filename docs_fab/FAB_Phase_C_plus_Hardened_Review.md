FAB — Phase C+ Hardened: Review & Next Steps
Date: 2025-10-30 21:57:19

Strengths (tests: 78/78):
- Envelope mode switch (legacy/hysteresis) with safe rollout.
- Deterministic seeding: session_id + combine_seeds(z, session, tick).
- MMR diversity effective (cluster tests pass).
- Hysteresis guard via min_stream_for_upgrade.
- changes_per_1k as float for sensitivity.
- Diagnostics counters/gauges + derived metrics in mix().

Critical fixes:
1) Precision level mapper — numeric compare avoids lexicographic risk.
2) Seeding by session_id — reproducibility across runs.
3) Hysteresis guard — configurable threshold; A/B without code changes.

Risks / refinements:
- Cache session_seed = hash_to_seed(session_id) in __init__.
- Diagnostics: add selected_diversity (share of unique score-bins in stream).
- Edge-cases:
  * budgets.nodes < min_stream_for_upgrade for long periods: ensure downgrades remain possible (already covered).
  * Unknown precision strings -> precision_level() == -1: add unit test for safe hold.
- Configs: consider EnvelopeConfig (or extend HysteresisConfig) to include min_stream_for_upgrade.
- MMR: replace 1D score vec with real embeddings later; keep (vec, score) API.
- Debugging: golden snapshot for derived metrics (changes_per_1k).

Extra tests to add:
- Runtime envelope switch between ticks — no invariant breaks.
- Hysteresis dwell/rate_limit matrix (0/1/3 dwell × 1/10/1000 rate) — no flapping.
- Precision downgrade path: immediate downgrade under threshold with rate limit honored.
- Seeding discipline: same session_id + z.seed -> deterministic ordering with varying budgets.

Observability & SLO:
- Alert on changes_per_1k using EMA (alpha≈0.2); per-branch baselines (legacy vs hysteresis).
- Log mmr.stats.max_similarity (or equivalent) in snapshot to catch diversity regressions.

Next steps:
1) Quality micro‑patch (no API break):
   - Cache session_seed in __init__.
   - Ensure all modules import precision_level from envelope.py (single source of truth).
   - Add selected_diversity metric (score-bins pre-embeddings).
2) Add integration/unit tests from the list above.
3) Shadow rollout: enable envelope_mode='hysteresis' on 5–10% ticks; compare changes_per_1k and cluster share in stream.
4) Prep Phase 2: cache + E2 writes with window stability constraints.

Ready for controlled production rollout.
