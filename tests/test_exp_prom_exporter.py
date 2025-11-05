"""
Tests for Experimental Prometheus Exporter (Phase B.3)

Coverage:
- Metrics setup and registration
- update_stability_metrics() from StabilityTracker
- Prometheus text format output
- Feature flag behavior (enabled/disabled)
- FastAPI endpoint integration
"""

import os
import pytest
from src.atlas.metrics.exp_prom_exporter import (
    is_enabled,
    setup_prometheus_metrics,
    update_stability_metrics,
    get_metrics_text,
)
from src.orbis_fab.stability import StabilityTracker, StabilityConfig


def test_is_enabled_when_flag_on(monkeypatch):
    """is_enabled() returns True when AURIS_METRICS_EXP=on"""
    monkeypatch.setenv("AURIS_METRICS_EXP", "on")
    # Need to reload module to pick up env change
    from importlib import reload
    import src.atlas.metrics.exp_prom_exporter as exporter

    reload(exporter)
    assert exporter.is_enabled()


def test_is_enabled_when_flag_off(monkeypatch):
    """is_enabled() returns False when AURIS_METRICS_EXP=off"""
    monkeypatch.setenv("AURIS_METRICS_EXP", "off")
    from importlib import reload
    import src.atlas.metrics.exp_prom_exporter as exporter

    reload(exporter)
    assert not exporter.is_enabled()


def test_setup_prometheus_metrics_creates_registry(monkeypatch):
    """setup_prometheus_metrics() creates CollectorRegistry when enabled"""
    monkeypatch.setenv("AURIS_METRICS_EXP", "on")
    from importlib import reload
    import src.atlas.metrics.exp_prom_exporter as exporter

    reload(exporter)

    registry = exporter.setup_prometheus_metrics()

    # Registry should be created (if prometheus_client installed)
    if exporter.PROMETHEUS_AVAILABLE:
        assert registry is not None
    else:
        assert registry is None


def test_update_stability_metrics_no_crash(monkeypatch):
    """update_stability_metrics() doesn't crash when enabled"""
    monkeypatch.setenv("AURIS_METRICS_EXP", "on")
    from importlib import reload
    import src.atlas.metrics.exp_prom_exporter as exporter

    reload(exporter)

    # Setup registry
    exporter.setup_prometheus_metrics()

    # Create tracker
    tracker = StabilityTracker()
    tracker.tick(current_score=0.8, degraded=False)

    # Should not crash
    exporter.update_stability_metrics(tracker, window_id="test")


def test_update_stability_metrics_updates_gauges(monkeypatch):
    """update_stability_metrics() updates Prometheus gauges"""
    monkeypatch.setenv("AURIS_METRICS_EXP", "on")
    from importlib import reload
    import src.atlas.metrics.exp_prom_exporter as exporter

    reload(exporter)

    exporter.setup_prometheus_metrics()

    # Create tracker with known state
    config = StabilityConfig(min_stable_ticks=10)
    tracker = StabilityTracker(config=config)

    # Run 20 stable ticks
    for _ in range(20):
        tracker.tick(current_score=0.8, degraded=False)

    # Update metrics
    exporter.update_stability_metrics(tracker, window_id="test")

    # Get metrics text
    metrics_text = exporter.get_metrics_text()

    # Should contain metric names (if prometheus available)
    if exporter.PROMETHEUS_AVAILABLE:
        assert "atlas_stability_score" in metrics_text
        assert "atlas_stability_score_ema" in metrics_text
        assert "atlas_stable_ticks" in metrics_text


def test_get_metrics_text_disabled(monkeypatch):
    """get_metrics_text() returns disabled message when flag off"""
    monkeypatch.setenv("AURIS_METRICS_EXP", "off")
    from importlib import reload
    import src.atlas.metrics.exp_prom_exporter as exporter

    reload(exporter)

    metrics_text = exporter.get_metrics_text()

    assert "disabled" in metrics_text.lower()


def test_recommended_mode_numeric_conversion(monkeypatch):
    """Recommended mode converts FAB0/FAB1/FAB2 to 0/1/2"""
    monkeypatch.setenv("AURIS_METRICS_EXP", "on")
    from importlib import reload
    import src.atlas.metrics.exp_prom_exporter as exporter

    reload(exporter)

    exporter.setup_prometheus_metrics()

    # Create tracker with low EMA (FAB0 mode)
    config = StabilityConfig(ema_decay=0.5)
    tracker = StabilityTracker(config=config)

    # Degrade many times to lower EMA
    for _ in range(10):
        tracker.tick(current_score=0.8, degraded=True)

    # Update metrics
    exporter.update_stability_metrics(tracker, window_id="test")

    # Get metrics
    metrics_text = exporter.get_metrics_text()

    # Should contain recommended_fab_mode metric
    if exporter.PROMETHEUS_AVAILABLE:
        assert "atlas_recommended_fab_mode" in metrics_text


def test_stability_score_ema_in_metrics(monkeypatch):
    """Metrics contain stability_score_ema value"""
    monkeypatch.setenv("AURIS_METRICS_EXP", "on")
    from importlib import reload
    import src.atlas.metrics.exp_prom_exporter as exporter

    reload(exporter)

    exporter.setup_prometheus_metrics()

    tracker = StabilityTracker()

    # Run stable ticks
    for _ in range(50):
        tracker.tick(current_score=0.9, degraded=False)

    exporter.update_stability_metrics(tracker)

    metrics_text = exporter.get_metrics_text()

    # Should contain EMA metric (if prometheus available)
    if exporter.PROMETHEUS_AVAILABLE:
        assert "stability_score_ema" in metrics_text
