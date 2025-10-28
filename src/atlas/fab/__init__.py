"""
Atlas × FAB Integration (v0.1)

Fractal Associative Bus (FAB) — global + stream context windows
over Atlas E1-E4 stack (API, indices, metrics, homeostasis).

Architecture:
    FABᴳ (Global Window)  → System-wide z-space, immutable per step
    FABˢ (Stream Window)  → Per-flow localized context, refresh on step change

Integration Points:
    - E2 Index Builders: HNSW/FAISS indexing for FAB vectors
    - E3 Metrics: h_coherence, h_stability monitoring
    - E4 Homeostasis: Policy triggers, decision engine, actions
    - E4.4 Snapshots: FAB cache rotation + manifest
    - E4.6 Sleep: Nightly consolidation + FAB cache cleanup

Lifecycle Hooks:
    - before_step: Freeze FABˢ, export to E3 metrics
    - after_step: Publish drift/coherence deltas, trigger E4 if needed
    - sleep_cycle: Call E4.6 consolidation, rotate FAB caches, snapshot

Contracts (v0.1):
    - JSON Schema: window{type,id,ts} + tokens + vectors + links + meta
    - Backpressure: Token bucket per-actor/per-window
    - QoS: X-FAB-Backpressure headers (slow|reject), Retry-After

Phased Rollout:
    1. Shadow (read-only): /fab/context/push dry_run, collect metrics
    2. Mirroring: Write-through to FAB cache + E2 indices
    3. Cutover: Enable actions with rate limits, SLO monitors

See: docs/AURIS_FAB_Integration_Plan_v0.1.txt for full specification
"""

__version__ = "0.1.0"
__author__ = "Danil Ivashyna"

# FAB will be implemented in phases:
# - Phase 1 (v0.1): Shadow mode routes + schemas + backpressure
# - Phase 2 (v0.2): Mirroring to E2 indices + E3 metrics
# - Phase 3 (v0.3): Cutover with E4 actions + SLO monitoring

__all__ = []
