"""
Test SELF metrics export to Prometheus (Phase C).

Smoke test to ensure SELF metrics (coherence, continuity, presence, stress)
are correctly exported to Prometheus when AURIS_METRICS_EXP=on.

Phase: C (experimental)
Status: Ready for CI (2025-11-05)
"""

import os
import importlib
import pytest


def test_self_metrics_export_smoke(monkeypatch):
    """
    Smoke test: SELF metrics appear in Prometheus registry.

    Verifies:
    - update_self_metrics() is callable
    - Metrics are registered in Prometheus
    - Metric names are correct
    - No crashes with valid inputs
    """
    # Enable experimental metrics
    monkeypatch.setenv("AURIS_METRICS_EXP", "on")

    # Reload exporter to pick up env var
    import atlas.metrics.exp_prom_exporter as exp

    importlib.reload(exp)

    # Setup Prometheus registry
    registry = exp.setup_prometheus_metrics()
    assert registry is not None, "Registry should be initialized when AURIS_METRICS_EXP=on"

    # Call update function with test values
    token_id = "test-token-001"
    exp.update_self_metrics(
        token_id=token_id,
        coherence=0.91,
        continuity=0.95,
        presence=1.0,
        stress=0.12,
    )

    # Render metrics text
    try:
        from prometheus_client import generate_latest

        text = generate_latest(registry).decode("utf-8")
    except ImportError:
        pytest.skip("prometheus_client not installed")

    # Verify metric names present
    assert "self_coherence" in text, "self_coherence metric missing"
    assert "self_continuity" in text, "self_continuity metric missing"
    assert "self_presence" in text, "self_presence metric missing"
    assert "self_stress" in text, "self_stress metric missing"

    # Verify token_id label
    assert f'token_id="{token_id}"' in text, f"token_id label missing for {token_id}"

    # Verify values (approximate, Prometheus may add metadata)
    assert "0.91" in text or "9.1e-01" in text, "coherence value missing"
    assert "0.95" in text or "9.5e-01" in text, "continuity value missing"
    assert "1.0" in text or "1e+00" in text, "presence value missing"
    assert "0.12" in text or "1.2e-01" in text, "stress value missing"


def test_self_metrics_disabled_gracefully(monkeypatch):
    """
    Test that update_self_metrics() is safe when metrics disabled.

    Verifies:
    - No crashes when AURIS_METRICS_EXP=off
    - No-op behavior (no side effects)
    """
    # Disable experimental metrics
    monkeypatch.setenv("AURIS_METRICS_EXP", "off")

    # Reload exporter
    import atlas.metrics.exp_prom_exporter as exp

    importlib.reload(exp)

    # Should not crash
    exp.update_self_metrics(
        token_id="test-token-002",
        coherence=0.8,
        continuity=0.9,
        presence=1.0,
        stress=0.2,
    )

    # Verify registry is None
    assert exp._registry is None, "Registry should be None when metrics disabled"


def test_self_metrics_multiple_tokens(monkeypatch):
    """
    Test that multiple token_id labels work correctly.

    Verifies:
    - Multiple tokens can be tracked simultaneously
    - Labels are distinct
    - Values are isolated per token
    """
    monkeypatch.setenv("AURIS_METRICS_EXP", "on")

    import atlas.metrics.exp_prom_exporter as exp

    importlib.reload(exp)
    registry = exp.setup_prometheus_metrics()

    # Update metrics for multiple tokens
    exp.update_self_metrics(
        token_id="token-A",
        coherence=0.85,
        continuity=0.90,
        presence=1.0,
        stress=0.15,
    )

    exp.update_self_metrics(
        token_id="token-B",
        coherence=0.92,
        continuity=0.95,
        presence=1.0,
        stress=0.08,
    )

    try:
        from prometheus_client import generate_latest

        text = generate_latest(registry).decode("utf-8")
    except ImportError:
        pytest.skip("prometheus_client not installed")

    # Verify both tokens present
    assert 'token_id="token-A"' in text, "token-A label missing"
    assert 'token_id="token-B"' in text, "token-B label missing"

    # Verify distinct values (simplified check)
    assert "0.85" in text or "8.5e-01" in text, "token-A coherence missing"
    assert "0.92" in text or "9.2e-01" in text, "token-B coherence missing"


def test_self_metrics_edge_values(monkeypatch):
    """
    Test edge values (0.0, 1.0) are handled correctly.

    Verifies:
    - Boundary values don't crash
    - Values are exported correctly
    """
    monkeypatch.setenv("AURIS_METRICS_EXP", "on")

    import atlas.metrics.exp_prom_exporter as exp

    importlib.reload(exp)
    registry = exp.setup_prometheus_metrics()

    # Edge case: all zeros
    exp.update_self_metrics(
        token_id="edge-zero",
        coherence=0.0,
        continuity=0.0,
        presence=0.0,
        stress=0.0,
    )

    # Edge case: all ones
    exp.update_self_metrics(
        token_id="edge-one",
        coherence=1.0,
        continuity=1.0,
        presence=1.0,
        stress=1.0,
    )

    try:
        from prometheus_client import generate_latest

        text = generate_latest(registry).decode("utf-8")
    except ImportError:
        pytest.skip("prometheus_client not installed")

    # Verify both edge tokens present
    assert 'token_id="edge-zero"' in text
    assert 'token_id="edge-one"' in text

    # Verify values (Prometheus may format as 0.0 or 0e+00)
    assert "0.0" in text or "0e+00" in text
    assert "1.0" in text or "1e+00" in text
