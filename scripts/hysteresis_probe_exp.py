#!/usr/bin/env python3
"""
Hysteresis E2E Probe (Phase B.1)

Simulates FABCore runtime with oscillating desired modes,
validates hysteresis anti-chatter behavior, and verifies
Prometheus metrics output.

Usage:
    export AURIS_HYSTERESIS=on AURIS_METRICS_EXP=on
    python scripts/hysteresis_probe_exp.py

Expected:
    - Effective mode smoother than desired mode
    - Switch rate ≤ 1/sec (SLO)
    - Oscillation count reduced vs baseline
    - Prometheus metrics contain hyst_* gauges
"""

import os
import sys

# Feature flags
os.environ["AURIS_HYSTERESIS"] = "on"
os.environ["AURIS_METRICS_EXP"] = "on"
os.environ["AURIS_STABILITY"] = "off"  # Disable B2 to isolate B1

from orbis_fab.hysteresis_exp import BitEnvelopeHysteresisExp, HysteresisConfig
from atlas.metrics.exp_prom_exporter import (
    setup_prometheus_metrics,
    update_hysteresis_metrics,
    get_metrics_text,
)


def main():
    """Run hysteresis E2E probe."""
    print("🔧 Hysteresis E2E Probe (Phase B.1)")
    print("=" * 60)

    # Setup Prometheus
    print("\n1️⃣  Setting up Prometheus registry...")
    registry = setup_prometheus_metrics()
    if registry is None:
        print("❌ Failed to setup Prometheus (check AURIS_METRICS_EXP=on)")
        sys.exit(1)
    print("✓ Registry created")

    # Create hysteresis instance
    print("\n2️⃣  Creating hysteresis instance...")
    config = HysteresisConfig(
        dwell_ticks=50,
        rate_limit_ticks=1000,
        osc_window=300,
        max_history=5000,
    )
    hyst = BitEnvelopeHysteresisExp(config)
    print(f"✓ Config: dwell={config.dwell_ticks}, rate_limit={config.rate_limit_ticks}")

    # Simulate oscillating desired modes
    print("\n3️⃣  Simulating oscillating desired modes (200 ticks)...")
    # Pattern: FAB2 (stable) → FAB1 oscillating → FAB2 (stable)
    desired_sequence = (
        ["FAB2"] * 50  # Stable start
        + ["FAB1", "FAB2"] * 25  # 50 oscillations (rapid back-and-forth)
        + ["FAB1"] * 50  # Stable end
    )

    effective_modes = []
    metrics_history = []

    for tick, desired in enumerate(desired_sequence):
        effective = hyst.update(desired_mode=desired, tick=tick)
        effective_modes.append(effective)

        # Get metrics
        metrics = hyst.get_metrics()
        metrics["desired_mode"] = desired
        metrics["effective_mode"] = effective
        metrics_history.append(metrics)

        # Update Prometheus every 10 ticks
        if tick % 10 == 0:
            update_hysteresis_metrics(metrics, window_id="global")

    print(f"✓ Processed {len(desired_sequence)} ticks")

    # Analyze results
    print("\n4️⃣  Analyzing results...")

    def count_switches(modes):
        return sum(1 for i in range(1, len(modes)) if modes[i] != modes[i - 1])

    desired_switches = count_switches(desired_sequence)
    effective_switches = count_switches(effective_modes)

    print(f"   Desired switches:   {desired_switches}")
    print(f"   Effective switches: {effective_switches}")
    print(f"   Reduction:          {desired_switches - effective_switches} ({100 * (1 - effective_switches / desired_switches):.1f}%)")

    # Get final metrics
    final_metrics = metrics_history[-1]
    print(f"\n   Switch rate:        {final_metrics['switch_rate_per_sec']:.4f} /sec")
    print(f"   Oscillation rate:   {final_metrics['oscillation_rate_per_sec']:.4f} /sec")
    print(f"   Oscillation count:  {final_metrics['osc_count']}")
    print(f"   Last switch age:    {final_metrics['last_switch_age']} ticks")

    # Verify Prometheus output
    print("\n5️⃣  Verifying Prometheus metrics...")
    metrics_text = get_metrics_text()

    required_metrics = [
        "atlas_hyst_switch_rate_per_sec",
        "atlas_hyst_oscillation_rate_per_sec",
        "atlas_hyst_dwell_counter",
        "atlas_hyst_last_switch_age",
        "atlas_hyst_effective_mode",
        "atlas_hyst_desired_mode",
    ]

    missing = []
    for metric in required_metrics:
        if metric in metrics_text:
            print(f"   ✓ {metric}")
        else:
            print(f"   ✗ {metric} (MISSING)")
            missing.append(metric)

    # Verification
    print("\n6️⃣  Verification:")
    checks_passed = 0
    checks_total = 0

    # Check 1: Effective smoother than desired
    checks_total += 1
    if effective_switches < desired_switches:
        print(f"   ✓ Effective smoother: {effective_switches} < {desired_switches}")
        checks_passed += 1
    else:
        print(f"   ✗ Effective NOT smoother: {effective_switches} >= {desired_switches}")

    # Check 2: Switch rate SLO (≤ 1/sec)
    checks_total += 1
    switch_rate_slo = 1.0
    if final_metrics["switch_rate_per_sec"] <= switch_rate_slo:
        print(f"   ✓ Switch rate SLO met: {final_metrics['switch_rate_per_sec']:.4f} ≤ {switch_rate_slo}")
        checks_passed += 1
    else:
        print(f"   ✗ Switch rate SLO VIOLATED: {final_metrics['switch_rate_per_sec']:.4f} > {switch_rate_slo}")

    # Check 3: All Prometheus metrics present
    checks_total += 1
    if not missing:
        print(f"   ✓ All Prometheus metrics present ({len(required_metrics)}/{len(required_metrics)})")
        checks_passed += 1
    else:
        print(f"   ✗ Missing Prometheus metrics: {missing}")

    # Check 4: Oscillation reduction (at least 50%)
    checks_total += 1
    reduction_pct = 100 * (1 - effective_switches / desired_switches)
    if reduction_pct >= 50:
        print(f"   ✓ Oscillation reduction ≥ 50%: {reduction_pct:.1f}%")
        checks_passed += 1
    else:
        print(f"   ✗ Oscillation reduction < 50%: {reduction_pct:.1f}%")

    # Final status
    print("\n" + "=" * 60)
    if checks_passed == checks_total:
        print(f"✅ Hysteresis probe passed ({checks_passed}/{checks_total} checks)")
        return 0
    else:
        print(f"❌ Hysteresis probe failed ({checks_passed}/{checks_total} checks)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
