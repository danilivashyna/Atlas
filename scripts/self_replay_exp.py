#!/usr/bin/env python3
"""
SELF Replay & Analysis Script (Phase C.1)

Анализирует последние N heartbeats из data/identity.jsonl:
- Вычисляет средние значения coherence, continuity, presence, stress
- Показывает перцентили (p50, p95, p99)
- Валидирует SLO targets
- Опционально сохраняет snapshot в data/self_state.json

Usage:
    python scripts/self_replay_exp.py                  # Last 50 heartbeats
    python scripts/self_replay_exp.py --count 100      # Last 100 heartbeats
    python scripts/self_replay_exp.py --save-snapshot  # Save state to JSON

Phase: C.1 (Snapshot & Replay)
Status: Ready for use (2025-11-05)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
import statistics


def parse_heartbeats(identity_file: Path) -> List[Dict[str, Any]]:
    """
    Parse all heartbeats from identity.jsonl.

    Args:
        identity_file: Path to identity.jsonl

    Returns:
        List of heartbeat records (newest first)
    """
    if not identity_file.exists():
        print(f"❌ File not found: {identity_file}", file=sys.stderr)
        return []

    heartbeats = []
    with open(identity_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if record.get("kind") == "heartbeat":
                    heartbeats.append(record)
            except json.JSONDecodeError as e:
                print(f"⚠️  Skipping invalid JSON line: {e}", file=sys.stderr)
                continue

    # Return newest first
    return list(reversed(heartbeats))


def analyze_heartbeats(heartbeats: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute statistics from heartbeat records.

    Args:
        heartbeats: List of heartbeat records

    Returns:
        Dict with averages, percentiles, SLO status
    """
    if not heartbeats:
        return {
            "count": 0,
            "avg": {},
            "p50": {},
            "p95": {},
            "p99": {},
            "slo_status": {},
        }

    # Extract metrics
    coherence_values = [h.get("coherence", 0.0) for h in heartbeats]
    continuity_values = [h.get("continuity", 0.0) for h in heartbeats]
    presence_values = [h.get("presence", 0.0) for h in heartbeats]
    stress_values = [h.get("stress", 0.0) for h in heartbeats]

    def percentile(values, p):
        """Compute percentile (0-100)."""
        if not values:
            return 0.0
        return statistics.quantiles(values, n=100)[p - 1] if len(values) > 1 else values[0]

    return {
        "count": len(heartbeats),
        "avg": {
            "coherence": statistics.mean(coherence_values),
            "continuity": statistics.mean(continuity_values),
            "presence": statistics.mean(presence_values),
            "stress": statistics.mean(stress_values),
        },
        "p50": {
            "coherence": percentile(coherence_values, 50),
            "continuity": percentile(continuity_values, 50),
            "presence": percentile(presence_values, 50),
            "stress": percentile(stress_values, 50),
        },
        "p95": {
            "coherence": percentile(coherence_values, 95),
            "continuity": percentile(continuity_values, 95),
            "presence": percentile(presence_values, 95),
            "stress": percentile(stress_values, 95),
        },
        "p99": {
            "coherence": percentile(coherence_values, 99),
            "continuity": percentile(continuity_values, 99),
            "presence": percentile(presence_values, 99),
            "stress": percentile(stress_values, 99),
        },
        "slo_status": {
            "coherence_slo": statistics.mean(coherence_values) >= 0.80,
            "continuity_slo": statistics.mean(continuity_values) >= 0.90,
            "stress_slo": statistics.mean(stress_values) <= 0.30,
        },
    }


def save_snapshot(snapshot_file: Path, stats: Dict[str, Any]) -> None:
    """
    Save snapshot to data/self_state.json.

    Args:
        snapshot_file: Path to snapshot JSON
        stats: Statistics dict from analyze_heartbeats()
    """
    snapshot = {
        "version": "0.2.0-alpha1",
        "phase": "C.1",
        "timestamp": None,  # Will be set by caller if needed
        "heartbeats_analyzed": stats["count"],
        "averages": stats["avg"],
        "percentiles": {
            "p50": stats["p50"],
            "p95": stats["p95"],
            "p99": stats["p99"],
        },
        "slo_status": stats["slo_status"],
    }

    snapshot_file.parent.mkdir(parents=True, exist_ok=True)
    with open(snapshot_file, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    print(f"✅ Snapshot saved to {snapshot_file}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Analyze SELF heartbeats from identity.jsonl")
    parser.add_argument(
        "--count",
        type=int,
        default=50,
        help="Number of recent heartbeats to analyze (default: 50)",
    )
    parser.add_argument(
        "--identity",
        type=Path,
        default=Path("data/identity.jsonl"),
        help="Path to identity.jsonl (default: data/identity.jsonl)",
    )
    parser.add_argument(
        "--save-snapshot",
        action="store_true",
        help="Save snapshot to data/self_state.json",
    )
    parser.add_argument(
        "--snapshot-file",
        type=Path,
        default=Path("data/self_state.json"),
        help="Snapshot output path (default: data/self_state.json)",
    )

    args = parser.parse_args()

    # Parse heartbeats
    print(f"📖 Reading heartbeats from {args.identity}")
    all_heartbeats = parse_heartbeats(args.identity)

    if not all_heartbeats:
        print("❌ No heartbeats found", file=sys.stderr)
        sys.exit(1)

    # Take last N
    heartbeats = all_heartbeats[: args.count]
    print(f"📊 Analyzing last {len(heartbeats)} heartbeats (of {len(all_heartbeats)} total)")

    # Compute statistics
    stats = analyze_heartbeats(heartbeats)

    # Print report
    print("\n" + "=" * 70)
    print("🧠 SELF Replay & Analysis Report")
    print("=" * 70)

    print(f"\nHeartbeats Analyzed: {stats['count']}")

    print("\n📈 Averages:")
    for metric, value in stats["avg"].items():
        print(f"   {metric:12s} = {value:.3f}")

    print("\n📊 Percentiles (p50 / p95 / p99):")
    for metric in ["coherence", "continuity", "presence", "stress"]:
        p50 = stats["p50"].get(metric, 0.0)
        p95 = stats["p95"].get(metric, 0.0)
        p99 = stats["p99"].get(metric, 0.0)
        print(f"   {metric:12s} = {p50:.3f} / {p95:.3f} / {p99:.3f}")

    print("\n🎯 SLO Status (Phase C):")
    slo_checks = [
        (
            "coherence >= 0.80",
            stats["slo_status"]["coherence_slo"],
            stats["avg"]["coherence"],
        ),
        (
            "continuity >= 0.90",
            stats["slo_status"]["continuity_slo"],
            stats["avg"]["continuity"],
        ),
        (
            "stress <= 0.30",
            stats["slo_status"]["stress_slo"],
            stats["avg"]["stress"],
        ),
    ]

    all_passed = True
    for check_name, passed, actual_value in slo_checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   [{status}] {check_name:20s} (actual: {actual_value:.3f})")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🟢 ALL SLO TARGETS PASSED")
    else:
        print("\n🔴 SOME SLO TARGETS FAILED")

    # Save snapshot if requested
    if args.save_snapshot:
        print()
        save_snapshot(args.snapshot_file, stats)

    print("=" * 70)


if __name__ == "__main__":
    main()
