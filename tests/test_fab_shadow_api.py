"""Tests for FAB Shadow Mode API routes

Validates HTTP endpoints for FAB observability without external I/O.
All tests use in-memory FABCore instance (no OneBlock/Atlas).
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from orbis_fab import create_fab_router, FABCore


@pytest.fixture
def fab_app():
    """Create FastAPI app with FAB router"""
    app = FastAPI()

    # Create FAB router with fresh core
    fab_core = FABCore(envelope_mode="legacy")
    fab_router = create_fab_router(fab_core=fab_core)

    app.include_router(fab_router, prefix="/api/v1/fab", tags=["FAB"])

    return app


@pytest.fixture
def client(fab_app):
    """Create test client"""
    return TestClient(fab_app)


def test_push_context_basic(client):
    """POST /context/push accepts Z-slice and returns diagnostics"""
    response = client.post(
        "/api/v1/fab/context/push",
        json={
            "mode": "FAB0",
            "budgets": {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30},
            "z_slice": {
                "nodes": [
                    {"id": "n1", "score": 0.95},
                    {"id": "n2", "score": 0.85},
                    {"id": "n3", "score": 0.75},
                ],
                "edges": [],
                "quotas": {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30},
                "seed": "test-42",
                "zv": "0.1",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert data["status"] == "ok"
    assert data["tick"] == 1  # First tick
    assert "diagnostics" in data

    # Validate diagnostics
    diag = data["diagnostics"]
    assert "counters" in diag
    assert "gauges" in diag

    # Check counters
    assert diag["counters"]["ticks"] == 1
    assert diag["counters"]["fills"] == 1
    assert diag["counters"]["mixes"] == 1

    # Check gauges
    assert diag["gauges"]["mode"] == "FAB0"


def test_pull_context(client):
    """GET /context/pull returns current FAB state"""
    # First push some context
    client.post(
        "/api/v1/fab/context/push",
        json={
            "mode": "FAB1",
            "budgets": {"tokens": 4096, "nodes": 200, "edges": 0, "time_ms": 30},
            "z_slice": {
                "nodes": [{"id": f"n{i}", "score": 0.90 - i * 0.01} for i in range(50)],
                "edges": [],
                "quotas": {"tokens": 4096, "nodes": 200},
                "seed": "test-pull",
                "zv": "0.1",
            },
        },
    )

    # Now pull
    response = client.get("/api/v1/fab/context/pull")

    assert response.status_code == 200
    data = response.json()

    # Validate state
    assert data["mode"] == "FAB1"
    assert data["stream_size"] > 0
    assert data["global_size"] >= 0
    assert data["stream_precision"] in ["mxfp8.0", "mxfp6.0", "mxfp5.25", "mxfp4.12"]
    assert data["global_precision"] == "mxfp4.12"  # Always cold

    # Diagnostics included
    assert "diagnostics" in data


def test_decide_fab0_to_fab1(client):
    """POST /decide triggers FAB0 → FAB1 transition"""
    # Initialize in FAB0
    client.post(
        "/api/v1/fab/context/push",
        json={
            "mode": "FAB0",
            "budgets": {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30},
            "z_slice": {
                "nodes": [{"id": "n1", "score": 0.90}],
                "edges": [],
                "quotas": {"tokens": 4096, "nodes": 256},
                "seed": "test-decide",
            },
        },
    )

    # Trigger transition with high self_presence + low stress
    response = client.post(
        "/api/v1/fab/decide", json={"stress": 0.3, "self_presence": 0.85, "error_rate": 0.0}
    )

    assert response.status_code == 200
    data = response.json()

    # Validate transition
    assert data["mode"] == "FAB1"  # Upgraded from FAB0
    assert data["stable"] is False  # Not yet stable
    assert data["stable_ticks"] == 0  # Reset on FAB0→FAB1

    # Diagnostics included
    assert "diagnostics" in data
    assert data["diagnostics"]["counters"]["mode_transitions"] == 1


def test_decide_fab1_to_fab2_stability(client):
    """POST /decide triggers FAB1 → FAB2 after stability"""
    # Initialize in FAB1
    client.post(
        "/api/v1/fab/context/push",
        json={
            "mode": "FAB1",
            "budgets": {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30},
            "z_slice": {
                "nodes": [{"id": "n1", "score": 0.90}],
                "edges": [],
                "quotas": {"tokens": 4096, "nodes": 256},
                "seed": "test-stability",
            },
        },
    )

    # Accumulate 3 stable ticks
    for i in range(3):
        response = client.post(
            "/api/v1/fab/decide", json={"stress": 0.3, "self_presence": 0.9, "error_rate": 0.0}
        )
        data = response.json()

        if i < 2:
            # Still FAB1
            assert data["mode"] == "FAB1"
            assert data["stable_ticks"] == i + 1
        else:
            # Transition to FAB2
            assert data["mode"] == "FAB2"
            assert data["stable"] is True
            assert data["stable_ticks"] == 3  # Shows count that triggered transition


def test_decide_degrade_fab2_to_fab1(client):
    """POST /decide triggers FAB2 → FAB1 on stress spike"""
    # Initialize in FAB2 (manually set)
    push_resp = client.post(
        "/api/v1/fab/context/push",
        json={
            "mode": "FAB2",
            "budgets": {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30},
            "z_slice": {
                "nodes": [{"id": "n1", "score": 0.90}],
                "edges": [],
                "quotas": {"tokens": 4096, "nodes": 256},
                "seed": "test-degrade",
            },
        },
    )

    # Trigger degradation with high stress
    response = client.post(
        "/api/v1/fab/decide",
        json={"stress": 0.8, "self_presence": 0.9, "error_rate": 0.0},  # > 0.7 threshold
    )

    assert response.status_code == 200
    data = response.json()

    # Validate degradation
    assert data["mode"] == "FAB1"  # Degraded from FAB2
    assert "diagnostics" in data


def test_act_shadow_mode_noop(client):
    """POST /act returns shadow mode message (no I/O)"""
    response = client.post("/api/v1/fab/act")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "shadow_mode"
    assert "No external I/O" in data["message"]


def test_push_multiple_ticks(client):
    """Multiple push calls increment tick counter"""
    # Push 3 times
    for i in range(3):
        response = client.post(
            "/api/v1/fab/context/push",
            json={
                "mode": "FAB0",
                "budgets": {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30},
                "z_slice": {
                    "nodes": [{"id": f"n{i}", "score": 0.9}],
                    "edges": [],
                    "quotas": {"tokens": 4096, "nodes": 256},
                    "seed": f"test-{i}",
                },
            },
        )

        data = response.json()
        assert data["tick"] == i + 1
        assert data["diagnostics"]["counters"]["ticks"] == i + 1
        assert data["diagnostics"]["counters"]["fills"] == i + 1


def test_push_diagnostics_envelope_changes(client):
    """Diagnostics track envelope changes on precision shift"""
    # First push: low scores → mxfp4.12
    client.post(
        "/api/v1/fab/context/push",
        json={
            "mode": "FAB0",
            "budgets": {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30},
            "z_slice": {
                "nodes": [{"id": "n1", "score": 0.3}],
                "edges": [],
                "quotas": {"tokens": 4096, "nodes": 256},
                "seed": "test-low",
            },
        },
    )

    # Second push: high scores → mxfp8.0 (should trigger envelope change)
    response = client.post(
        "/api/v1/fab/context/push",
        json={
            "mode": "FAB0",
            "budgets": {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30},
            "z_slice": {
                "nodes": [{"id": "n2", "score": 0.95}],
                "edges": [],
                "quotas": {"tokens": 4096, "nodes": 256},
                "seed": "test-high",
            },
        },
    )

    data = response.json()

    # Envelope change detected
    assert data["diagnostics"]["counters"]["envelope_changes"] >= 1
