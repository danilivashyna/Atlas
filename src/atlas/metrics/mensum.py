"""
Mensum v0 metrics for Atlas v0.5+.

Tracks router, reticulum, and node statistics.
"""

import time
from collections import defaultdict
from typing import Any, Dict


class Metrics:
    """Thread-safe metrics collector for v0.5+."""

    def __init__(self):
        # Router metrics
        self.router_requests_total = 0
        self.router_batch_requests_total = 0
        self.router_latency_ms = defaultdict(list)  # endpoint -> [latencies]
        self.router_ann_backend = "off"
        self.router_hit_rate_ann = 0.0  # hit_count / total
        self.router_softmax_entropy = 0.0

        # Reticulum metrics
        self.reticulum_links_total = 0
        self.reticulum_query_latency_ms = []

        # Node metrics
        self.nodes_index_size = 0
        self.nodes_count = 0

    def inc_router_request(self, endpoint: str = "route"):
        """Increment router request counter."""
        self.router_requests_total += 1

    def inc_router_batch_request(self):
        """Increment batch router request counter."""
        self.router_batch_requests_total += 1

    def record_router_latency(self, endpoint: str, latency_ms: float):
        """Record router endpoint latency."""
        self.router_latency_ms[endpoint].append(latency_ms)

    def set_ann_backend(self, backend: str):
        """Set active ANN backend."""
        self.router_ann_backend = backend

    def set_ann_hit_rate(self, hit_count: int, total: int):
        """Set ANN hit rate (fraction of top-1 matches)."""
        if total > 0:
            self.router_hit_rate_ann = float(hit_count) / float(total)

    def set_softmax_entropy(self, entropy: float):
        """Set average softmax entropy from child activation."""
        self.router_softmax_entropy = entropy

    def inc_link_created(self):
        """Increment link counter."""
        self.reticulum_links_total += 1

    def record_link_query_latency(self, latency_ms: float):
        """Record link query latency."""
        self.reticulum_query_latency_ms.append(latency_ms)

    def set_nodes_index_size(self, size: int):
        """Set ANN index size."""
        self.nodes_index_size = size

    def set_nodes_count(self, count: int):
        """Set total node count."""
        self.nodes_count = count

    def to_dict(self) -> Dict[str, Any]:
        """Export metrics as dict."""
        # Calculate averages
        avg_router_latency = {}
        for endpoint, latencies in self.router_latency_ms.items():
            if latencies:
                avg_router_latency[endpoint] = float(sum(latencies)) / len(latencies)

        avg_link_query_latency = 0.0
        if self.reticulum_query_latency_ms:
            avg_link_query_latency = float(sum(self.reticulum_query_latency_ms)) / len(
                self.reticulum_query_latency_ms
            )

        return {
            "router": {
                "requests_total": self.router_requests_total,
                "batch_requests_total": self.router_batch_requests_total,
                "avg_latency_ms": avg_router_latency,
                "ann_backend": self.router_ann_backend,
                "ann_hit_rate": self.router_hit_rate_ann,
                "softmax_entropy": self.router_softmax_entropy,
            },
            "reticulum": {
                "links_total": self.reticulum_links_total,
                "avg_query_latency_ms": avg_link_query_latency,
            },
            "nodes": {
                "index_size": self.nodes_index_size,
                "count": self.nodes_count,
            },
        }


# Global metrics instance
_metrics_instance = None


def get_metrics() -> Metrics:
    """Get global metrics instance."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = Metrics()
    return _metrics_instance
