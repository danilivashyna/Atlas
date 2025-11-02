# SPDX-License-Identifier: AGPL-3.0-or-later
# Atlas Metrics package exports

from .h_coherence import (
    HCoherenceMetric,
    compute_h_coherence,
)
from .h_stability import (
    HStabilityMetric,
    compute_h_stability,
)

# Optional E4.8 homeostasis metrics registry (graceful if module absent)
try:
    from .homeostasis import HomeostasisMetrics, get_homeostasis_metrics  # type: ignore
except Exception:  # pylint: disable=broad-exception-caught  # pragma: no cover
    HomeostasisMetrics = None  # type: ignore

    def get_homeostasis_metrics():  # type: ignore
        return None

__all__ = [
    "HCoherenceMetric",
    "compute_h_coherence",
    "HStabilityMetric",
    "compute_h_stability",
    "HomeostasisMetrics",
    "get_homeostasis_metrics",
]
