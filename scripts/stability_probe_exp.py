#!/usr/bin/env python3
"""
Stability Probe (Experimental) - Phase B.3 End-to-End Test

Симуляция FAB с деградацией → StabilityTracker → Prometheus metrics.

Usage:
    AURIS_STABILITY_HOOK=on AURIS_METRICS_EXP=on python scripts/stability_probe_exp.py

Output:
    - EMA evolution over 100 ticks
    - Mode recommendations (FAB0/FAB1/FAB2)
    - Prometheus metrics snapshot
"""

import os
import sys
from dataclasses import dataclass, field
from typing import Optional

# Enable feature flags
os.environ["AURIS_STABILITY_HOOK"] = "on"
os.environ["AURIS_METRICS_EXP"] = "on"

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@dataclass
class MockFABCore:
    """Mock FABCore for testing"""

    current_tick: int = 0
    mode: str = "FAB2"
    _prev_mode: str = "FAB2"
    coherence_score: float = 0.9
    degraded: bool = False

    # Scenario control
    degradation_schedule: list = field(default_factory=list)

    def tick(self):
        """Advance tick, check for degradation events"""
        self.current_tick += 1

        # Check degradation schedule
        if self.current_tick in self.degradation_schedule:
            print(f"[TICK {self.current_tick:3d}] ⚠️  Degradation event triggered")
            self.degraded = True
            self.coherence_score = 0.4  # Drop score

            # Downgrade mode
            self._prev_mode = self.mode
            if self.mode == "FAB2":
                self.mode = "FAB1"
            elif self.mode == "FAB1":
                self.mode = "FAB0"
        else:
            self.degraded = False
            # Gradual recovery
            if self.coherence_score < 0.9:
                self.coherence_score = min(0.9, self.coherence_score + 0.05)


def main():
    """Run stability probe simulation"""
    print("=" * 70)
    print("Stability Probe (Experimental) - FAB → Tracker → Prometheus")
    print("=" * 70)
    print()

    # Import modules (after env vars set)
    from orbis_fab.stability_hook_exp import attach
    from atlas.metrics.exp_prom_exporter import (
        setup_prometheus_metrics,
        update_stability_metrics,
        get_metrics_text,
    )

    # Create mock FAB with degradation schedule
    fab = MockFABCore(degradation_schedule=[20, 50, 80])

    # Attach StabilityTracker
    print("1️⃣  Attaching StabilityTracker to FABCore...")
    result = attach(fab, decay=0.95, min_stable_ticks=30)
    if result is None:
        print("❌ Failed to attach (feature flags disabled?)")
        return 1

    tracker, tick_fn = result
    print(f"   ✓ Tracker attached (decay=0.95, min_stable_ticks=30)")
    print()

    # Setup Prometheus
    print("2️⃣  Setting up Prometheus metrics...")
    registry = setup_prometheus_metrics()
    if registry is None:
        print("❌ Failed to setup Prometheus (AURIS_METRICS_EXP disabled?)")
        return 1
    print("   ✓ Prometheus registry created")
    print()

    # Run simulation
    print("3️⃣  Running 100-tick simulation...")
    print("   Degradation schedule: ticks 20, 50, 80")
    print()
    print("TICK | MODE | SCORE | EMA   | STABLE | DEGRAD | RECOMMENDED")
    print("-" * 70)

    for i in range(100):
        fab.tick()
        metrics = tick_fn()

        # Update Prometheus
        update_stability_metrics(tracker, window_id="global")

        # Print every 10 ticks or on degradation
        if i % 10 == 0 or fab.degraded:
            print(
                f"{fab.current_tick:4d} | {fab.mode:4s} | "
                f"{fab.coherence_score:5.2f} | {metrics['stability_score_ema']:5.3f} | "
                f"{metrics['stable_ticks']:6d} | {metrics['degradation_count']:6d} | "
                f"{metrics['recommended_mode']:4s}"
            )

    print()

    # Final metrics
    final_metrics = tracker.get_metrics()
    print("4️⃣  Final Metrics:")
    print(f"   EMA:                    {final_metrics['stability_score_ema']:.3f}")
    print(f"   Degradation count:      {final_metrics['degradation_count']}")
    print(
        f"   Degradation events/h:   {final_metrics['degradation_events_per_hour']:.1f}"
    )
    print(f"   Recommended mode:       {final_metrics['recommended_mode']}")
    print(f"   Stable ticks:           {final_metrics['stable_ticks']}")
    print()

    # Prometheus snapshot
    print("5️⃣  Prometheus Metrics Snapshot:")
    print("-" * 70)
    metrics_text = get_metrics_text()
    for line in metrics_text.split("\n"):
        if line and not line.startswith("#"):
            print(f"   {line}")
    print()

    # Verify correctness
    print("6️⃣  Verification:")

    # Check EMA range
    ema = final_metrics["stability_score_ema"]
    if 0.0 <= ema <= 1.0:
        print(f"   ✓ EMA in valid range [0.0, 1.0]: {ema:.3f}")
    else:
        print(f"   ❌ EMA out of range: {ema:.3f}")
        return 1

    # Check degradation count
    if final_metrics["degradation_count"] == 3:
        print(f"   ✓ Degradation count correct: 3 events")
    else:
        print(
            f"   ❌ Degradation count incorrect: {final_metrics['degradation_count']}"
        )
        return 1

    # Check Prometheus text format
    if "atlas_stability_score_ema" in metrics_text:
        print(f"   ✓ Prometheus metrics contain EMA gauge")
    else:
        print(f"   ❌ Prometheus metrics missing EMA gauge")
        return 1

    print()
    print("=" * 70)
    print("✅ Stability probe completed successfully!")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
