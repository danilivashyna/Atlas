# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Smoke test for E4.7 Homeostasis API Routes integration

Quick validation that homeostasis endpoints are accessible and
stub implementations return expected responses.
"""

from fastapi.testclient import TestClient

from atlas.api.app import app


def test_homeostasis_routes_registered():
    """Verify all 5 homeostasis routes are registered."""
    routes = [r.path for r in app.routes]
    
    expected = [
        "/api/v1/homeostasis/policies/test",
        "/api/v1/homeostasis/actions/{action_type}",
        "/api/v1/homeostasis/audit",
        "/api/v1/homeostasis/snapshots",
        "/api/v1/homeostasis/snapshots/rollback",
    ]
    
    for route in expected:
        assert route in routes, f"Route {route} not registered"


def test_policies_test_smoke():
    """Smoke test POST /policies/test."""
    client = TestClient(app)
    
    response = client.post(
        "/api/v1/homeostasis/policies/test",
        json={
            "run_id": "smoke-001",
            "metrics": {
                "h_coherence": {"sp": 0.91, "pd": 0.89},
                "h_stability": {"avg_drift": 0.03},
            },
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "decisions" in data
    assert len(data["decisions"]) >= 1
    assert data["run_id"] == "smoke-001"


def test_action_dry_run_smoke():
    """Smoke test POST /actions/{action_type} with dry_run."""
    client = TestClient(app)
    
    response = client.post(
        "/api/v1/homeostasis/actions/rebuild_shard",
        json={"run_id": "smoke-002", "dry_run": True, "params": {"shard_id": 0}},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "dry_run"
    assert data["action_type"] == "rebuild_shard"
    assert "stub" in data["details"]  # Stub implementation marker


def test_audit_query_smoke():
    """Smoke test GET /audit."""
    client = TestClient(app)
    
    # Trigger some events first
    client.post(
        "/api/v1/homeostasis/policies/test",
        json={"run_id": "smoke-003", "metrics": {}},
    )
    
    response = client.get("/api/v1/homeostasis/audit?run_id=smoke-003")
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "count" in data


def test_snapshot_create_smoke():
    """Smoke test POST /snapshots."""
    client = TestClient(app)
    
    response = client.post(
        "/api/v1/homeostasis/snapshots",
        json={"run_id": "smoke-004", "reason": "smoke test"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "snapshot_id" in data
    assert "checksums" in data
    assert len(data["checksums"]) > 0


def test_snapshot_rollback_smoke():
    """Smoke test POST /snapshots/rollback."""
    client = TestClient(app)
    
    # Create snapshot first
    create_resp = client.post(
        "/api/v1/homeostasis/snapshots",
        json={"run_id": "smoke-005", "reason": "rollback test"},
    )
    snapshot_id = create_resp.json()["snapshot_id"]
    
    # Rollback to it
    response = client.post(
        "/api/v1/homeostasis/snapshots/rollback",
        json={"run_id": "smoke-006", "snapshot_id": snapshot_id},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["snapshot_id"] == snapshot_id


def test_app_state_dependencies():
    """Verify app.state has all required homeostasis dependencies."""
    assert hasattr(app.state, "policy_engine")
    assert hasattr(app.state, "action_executor")
    assert hasattr(app.state, "audit_logger")
    assert hasattr(app.state, "snapshot_manager")
    
    # Verify stubs work
    assert app.state.policy_engine is not None
    assert app.state.action_executor is not None
    assert app.state.audit_logger is not None
    assert app.state.snapshot_manager is not None
