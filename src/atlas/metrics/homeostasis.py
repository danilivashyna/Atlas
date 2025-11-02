# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Atlas Homeostasis Metrics (E4.8)

Prometheus metrics for homeostasis loop monitoring.

Metrics:
- atlas_decision_count{policy, action_type, status}
- atlas_action_duration_seconds{action_type} (histogram P50/P95/P99)
- atlas_repair_success_ratio
- atlas_snapshot_age_seconds

Архитектурная роль:
- E4.8 (Metrics): Observability for homeostasis loop
- E3 (Self-awareness): Extends metrics with homeostasis stats
"""

from typing import Optional

# Try importing prometheus_client (optional dependency)
try:
    from prometheus_client import Counter, Gauge, Histogram, generate_latest  # type: ignore
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = None  # type: ignore
    Gauge = None  # type: ignore
    Histogram = None  # type: ignore
    generate_latest = None  # type: ignore


class HomeostasisMetrics:
    """
    Homeostasis metrics collector.

    Exports Prometheus metrics for:
    - Decision count (by policy, action_type, status)
    - Action duration (histogram)
    - Repair success ratio
    - Snapshot age

    Beta constraint: Stub if prometheus_client not installed.
    """

    def __init__(self):
        """Initialize metrics collectors."""
        if not PROMETHEUS_AVAILABLE:
            # Stub mode
            self.decision_count_total = None
            self.action_duration_seconds = None
            self.repair_success_ratio = None
            self.snapshot_age_seconds = None
            return

        # Decision counter
        if Counter is not None:
            self.decision_count_total = Counter(
                "atlas_decision_count_total",
                "Total number of decisions made",
                ["policy", "action_type", "status"],
            )
        else:
            self.decision_count_total = None

        # Action duration histogram
        if Histogram is not None:
            self.action_duration_seconds = Histogram(
                "atlas_action_duration_seconds",
                "Duration of homeostasis actions",
                ["action_type"],
                buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0],
            )
        else:
            self.action_duration_seconds = None

        # Repair success ratio gauge
        if Gauge is not None:
            self.repair_success_ratio = Gauge(
                "atlas_repair_success_ratio",
                "Ratio of successful repairs (0.0-1.0)",
            )
        else:
            self.repair_success_ratio = None

        # Snapshot age gauge
        if Gauge is not None:
            self.snapshot_age_seconds = Gauge(
                "atlas_snapshot_age_seconds",
                "Age of latest snapshot in seconds",
            )
        else:
            self.snapshot_age_seconds = None

    def record_decision(
        self,
        policy: str,
        action_type: str,
        status: str = "approved",
    ) -> None:
        """
        Record a decision.

        Args:
            policy: Policy name
            action_type: Action type (rebuild_shard, etc.)
            status: Decision status (approved, rejected, etc.)
        """
        if not PROMETHEUS_AVAILABLE or self.decision_count_total is None:
            return

        self.decision_count_total.labels(
            policy=policy,
            action_type=action_type,
            status=status,
        ).inc()

    def record_action_duration(
        self,
        action_type: str,
        duration_seconds: float,
    ) -> None:
        """
        Record action duration.

        Args:
            action_type: Action type
            duration_seconds: Duration in seconds
        """
        if not PROMETHEUS_AVAILABLE or self.action_duration_seconds is None:
            return

        self.action_duration_seconds.labels(action_type=action_type).observe(
            duration_seconds
        )

    def update_repair_success_ratio(self, ratio: float) -> None:
        """
        Update repair success ratio.

        Args:
            ratio: Success ratio (0.0-1.0)
        """
        if not PROMETHEUS_AVAILABLE or self.repair_success_ratio is None:
            return

        self.repair_success_ratio.set(ratio)

    def update_snapshot_age(self, age_seconds: float) -> None:
        """
        Update snapshot age.

        Args:
            age_seconds: Age of latest snapshot in seconds
        """
        if not PROMETHEUS_AVAILABLE or self.snapshot_age_seconds is None:
            return

        self.snapshot_age_seconds.set(age_seconds)

    def get_metrics_text(self) -> str:
        """
        Get Prometheus metrics in text format.

        Returns:
            str: Prometheus metrics text
        """
        if not PROMETHEUS_AVAILABLE or generate_latest is None:
            return "# Prometheus client not installed\n"

        return generate_latest().decode("utf-8")


# Global instance
_homeostasis_metrics: Optional[HomeostasisMetrics] = None


def get_homeostasis_metrics() -> HomeostasisMetrics:
    """
    Get global homeostasis metrics instance.

    Returns:
        HomeostasisMetrics: Global instance
    """
    global _homeostasis_metrics  # noqa: PLW0603

    if _homeostasis_metrics is None:
        _homeostasis_metrics = HomeostasisMetrics()

    return _homeostasis_metrics
