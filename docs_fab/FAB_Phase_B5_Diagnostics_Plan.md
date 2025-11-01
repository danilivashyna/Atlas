FAB Phase B.5 — Diagnostics Counters (Plan & Patch Notes)
Objective: Add lightweight, dependency-free diagnostics to orbis_fab that track stability and precision behavior without external telemetry.
Scope
- Counters: envelope_changes, mode_transitions, rebalance_events, fills, mixes, ticks
- Gauges: current_mode, global_precision, stream_precision, stable_ticks, cooldown_remaining
- Rates (derived via counters): changes_per_1k_ticks, rebalance_per_fill
Files to touch
1) src/orbis_fab/diagnostics.py — new module with Diagnostics dataclass
2) src/orbis_fab/core.py — integrate Diagnostics into FABCore (init_tick, fill, mix, step_stub)
3) src/orbis_fab/__init__.py — export Diagnostics
4) tests/test_diagnostics.py — unit tests for increments & snapshot shape
Data Model
Diagnostics: - counters: {ticks, fills, mixes, envelope_changes, mode_transitions, rebalance_events} - gauges: {mode, global_precision, stream_precision, stable_ticks, cooldown_remaining} - snapshot(): returns JSON-serializable dict - reset(): zeros all counters, preserves gauges until next mix() 
Patch Outline (Key Inserts)
A) diagnostics.py - from dataclasses import dataclass, field - class Diagnostics: counters (int), gauges (str/int), methods: inc_*, set_gauge, snapshot, reset 
B) core.py - in FABCore.__init__: self.diag = Diagnostics() - in init_tick(): self.diag.inc_ticks(); detect mode change -> inc_mode_transitions() - in fill(): self.diag.inc_fills(); after MMR: self.diag.add_rebalance_events(stats.nodes_penalized>0) - in precision assignment: if precision changed -> inc_envelope_changes() - in mix(): self.diag.inc_mixes(); set gauges; include diagnostics=self.diag.snapshot() in returned ctx - in step_stub(): if mode changes -> inc_mode_transitions() 
Tests (tests/test_diagnostics.py)
- test_counters_increment_on_calls (ticks/fills/mixes)
- test_envelope_changes_increment_on_precision_shift
- test_mode_transitions_increment_on_step
- test_snapshot_shape_and_values
Non-Goals
- No external logging/Prometheus in Phase B.5
- No wall-clock timers; tick-based only
Success Criteria
- All diagnostics tests passing
- No mutation of existing public API signatures
- mix() returns diagnostics block consistently
