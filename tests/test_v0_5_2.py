"""
Tests for v0.5.2: Prometheus metrics + TTL/LRU policies
"""

import os

import pytest

from atlas.metrics.mensum import MensumMetrics


def test_mensum_metrics_basic():
    """Test basic MensumMetrics functionality."""
    m = MensumMetrics()

    # Counters
    m.inc_counter("test_counter", 5, backend="faiss", mode="on")
    key = ("test_counter", (("backend", "faiss"), ("mode", "on")))
    assert m.counters[key] == 5

    # Gauges
    m.set_gauge("test_gauge", 10.5, backend="inproc")
    key = ("test_gauge", (("backend", "inproc"),))
    assert m.gauges[key] == 10.5

    m.add_gauge("test_gauge", 2.5, backend="inproc")
    assert m.gauges[key] == 13.0


def test_mensum_to_json():
    """Test JSON export."""
    m = MensumMetrics()
    m.inc_counter("requests", 100, endpoint="/test")
    m.set_gauge("latency", 50.0, method="POST")

    json_data = m.to_json()
    assert "counters" in json_data
    assert "gauges" in json_data
    assert json_data["counters"]["requests{'endpoint': '/test'}"] == 100


def test_mensum_to_prom():
    """Test Prometheus export format."""
    m = MensumMetrics()
    m.inc_counter("router_requests_total", 42, ann_backend="faiss", router_mode="on")
    m.set_gauge("ann_index_size", 1000, ann_backend="faiss")

    prom_text = m.to_prom(ann_backend="faiss", router_mode="on")

    # Check format
    assert "# TYPE router_requests_total counter" in prom_text
    assert 'router_requests_total{ann_backend="faiss",router_mode="on"} 42' in prom_text
    assert "# TYPE ann_index_size gauge" in prom_text
    assert 'ann_index_size{ann_backend="faiss",router_mode="on"} 1000' in prom_text


def test_prometheus_labels_injection():
    """Test that base labels are injected into all metrics."""
    m = MensumMetrics()
    m.inc_counter("test_metric", 1)

    prom_text = m.to_prom(global_label="value", another="test")

    # Should have injected labels
    assert 'test_metric{global_label="value",another="test"} 1' in prom_text


def test_cache_ttl_eviction():
    """Test that cache evicts by TTL."""
    import time

    from atlas.router.ann_index import TTLCacheLRU

    cache = TTLCacheLRU(capacity=10, ttl=0.1)  # 100ms TTL

    cache.set("key1", "val1")
    assert cache.get("key1") == "val1"

    time.sleep(0.15)  # Wait for TTL
    assert cache.get("key1") is None
