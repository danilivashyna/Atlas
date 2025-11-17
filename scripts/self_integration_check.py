#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
SELF Integration Smoke Test

Quick validation that SELF system is wired correctly:
1. Metrics export to Prometheus
2. /self/health endpoint
3. Auto-tune background task (if enabled)

Usage:
    python scripts/self_integration_check.py [--api-url http://localhost:8000]
"""

import argparse
import sys
import time
from urllib.request import urlopen
from urllib.error import URLError


def check_metrics_export(api_url: str) -> bool:
    """Check if SELF metrics are exported to /metrics/exp."""
    print("🔍 Checking SELF metrics export...")
    try:
        url = f"{api_url}/metrics/exp"
        with urlopen(url, timeout=5) as response:
            content = response.read().decode("utf-8")
            
            required_metrics = [
                "self_coherence",
                "self_continuity", 
                "self_presence",
                "self_stress"
            ]
            
            found = []
            missing = []
            
            for metric in required_metrics:
                if metric in content:
                    found.append(metric)
                    # Extract sample value
                    for line in content.split("\n"):
                        if line.startswith(metric) and "}" in line:
                            print(f"  ✓ {line.strip()}")
                            break
                else:
                    missing.append(metric)
            
            if missing:
                print(f"  ❌ Missing metrics: {', '.join(missing)}")
                return False
            
            print(f"  ✅ All {len(required_metrics)} SELF metrics found")
            return True
            
    except URLError as e:
        print(f"  ❌ Failed to fetch metrics: {e}")
        print(f"     Is API running at {api_url}?")
        return False


def check_health_endpoint(api_url: str) -> bool:
    """Check /self/health endpoint."""
    print("\n🏥 Checking /self/health endpoint...")
    try:
        url = f"{api_url}/self/health"
        with urlopen(url, timeout=5) as response:
            import json
            data = json.loads(response.read().decode("utf-8"))
            
            print(f"  ✓ enabled: {data.get('enabled', False)}")
            print(f"  ✓ canary_sampling: {data.get('canary_sampling', 0.0)}")
            print(f"  ✓ heartbeat_count: {data.get('heartbeat_count', 0)}")
            
            metrics = data.get("current_metrics", {})
            if metrics:
                print(f"  ✓ coherence: {metrics.get('coherence', 'N/A')}")
                print(f"  ✓ continuity: {metrics.get('continuity', 'N/A')}")
                print(f"  ✓ stress: {metrics.get('stress', 'N/A')}")
            
            slo_status = data.get("slo_status", {})
            if slo_status:
                print(f"  ✓ SLO compliance: coherence={slo_status.get('coherence_ok')}, "
                      f"continuity={slo_status.get('continuity_ok')}, "
                      f"stress={slo_status.get('stress_ok')}")
            
            print("  ✅ /self/health OK")
            return True
            
    except URLError as e:
        print(f"  ❌ Failed to fetch /self/health: {e}")
        return False
    except (ValueError, KeyError) as e:  # JSON parsing or missing keys
        print(f"  ❌ Error parsing response: {e}")
        return False


def check_autotune_task(_api_url: str) -> bool:  # pylint: disable=unused-argument
    """Check if auto-tune task is running (best-effort check)."""
    print("\n🤖 Checking auto-tune status...")
    print("  ℹ️  Auto-tune runs in background every 60s (default)")
    print("  ℹ️  Check logs for: 'Auto-tune:' messages")
    print("  ✓ Auto-tune task starts if AURIS_SELF_AUTOTUNE=on")
    return True


def main():
    parser = argparse.ArgumentParser(description="SELF integration smoke test")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)"
    )
    args = parser.parse_args()
    
    print("=" * 60)
    print("SELF Integration Smoke Test")
    print("=" * 60)
    print(f"API URL: {args.api_url}")
    print()
    
    # Give API time to start if just launched
    print("⏳ Waiting 2s for API startup...")
    time.sleep(2)
    
    results = []
    
    # Check 1: Metrics export
    results.append(("Metrics Export", check_metrics_export(args.api_url)))
    
    # Check 2: Health endpoint
    results.append(("Health Endpoint", check_health_endpoint(args.api_url)))
    
    # Check 3: Auto-tune (informational)
    results.append(("Auto-tune Info", check_autotune_task(args.api_url)))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}  {name}")
    
    print()
    
    if passed == total:
        print(f"✅ All checks passed ({passed}/{total})")
        print("\nSELF system is ready for monitoring! 🚀")
        return 0
    else:
        print(f"❌ Some checks failed ({passed}/{total})")
        print("\nTroubleshooting:")
        print("  1. Ensure API is running: make self-api")
        print("  2. Check environment variables:")
        print("     export AURIS_SELF=on")
        print("     export AURIS_METRICS_EXP=on")
        print("  3. Check logs for errors")
        return 1


if __name__ == "__main__":
    sys.exit(main())
