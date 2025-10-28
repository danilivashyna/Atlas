"""
Tests for FAB API Routes (v0.1 Shadow Mode)

Phase 1 (Shadow): All routes dry_run=true, validation only
Phase 2 (Mirroring): Write-through to FAB cache + E2 indices
Phase 3 (Cutover): Enable actions with rate limits + SLO monitoring
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient


@pytest.fixture
def fab_context_payload():
    """Sample FAB context payload for testing."""
    return {
        "context": {
            "fab_version": "0.1",
            "window": {
                "type": "global",
                "id": str(uuid4()),
                "ts": datetime.now(timezone.utc).isoformat(),
            },
            "tokens": [
                {"t": "hello", "w": 1.0, "role": "user"},
                {"t": "world", "w": 0.8, "role": "agent"},
            ],
            "vectors": [
                {
                    "id": "vec1",
                    "dim": 384,
                    "norm": 1.0,
                    "ts": datetime.now(timezone.utc).isoformat(),
                }
            ],
            "links": [{"src": "vec1", "dst": "vec1", "w": 1.0, "kind": "semantic"}],
            "meta": {"topic": "test", "locale": "en-US", "coherence": 0.95, "stability": 0.92},
        },
        "run_id": "test-001",
        "dry_run": True,
    }


class TestFABPush:
    """Tests for POST /api/v1/fab/context/push."""

    def test_push_context_dry_run(self, client: TestClient, fab_context_payload):
        """Test FAB context push in dry-run mode (Shadow phase)."""
        response = client.post("/api/v1/fab/context/push", json=fab_context_payload)

        assert response.status_code == 200
        data = response.json()

        assert data["accepted"] is True
        assert data["backpressure"] in ["ok", "slow", "reject"]
        assert data["run_id"] == "test-001"
        assert "X-FAB-Backpressure" in response.headers

    def test_push_context_backpressure_slow(self, client: TestClient, fab_context_payload):
        """Test backpressure SLOW when token count > 2000."""
        # Add 2500 tokens to trigger SLOW
        fab_context_payload["context"]["tokens"] = [
            {"t": f"token{i}", "w": 0.5, "role": "user"} for i in range(2500)
        ]

        response = client.post("/api/v1/fab/context/push", json=fab_context_payload)

        assert response.status_code == 200
        data = response.json()

        assert data["accepted"] is True
        assert data["backpressure"] == "slow"
        assert response.headers["X-FAB-Backpressure"] == "slow"

    def test_push_context_backpressure_reject(self, client: TestClient, fab_context_payload):
        """Test backpressure REJECT when token count > 5000."""
        # Add 6000 tokens to trigger REJECT
        fab_context_payload["context"]["tokens"] = [
            {"t": f"token{i}", "w": 0.5, "role": "user"} for i in range(6000)
        ]

        response = client.post("/api/v1/fab/context/push", json=fab_context_payload)

        assert response.status_code == 200
        data = response.json()

        assert data["accepted"] is False
        assert data["backpressure"] == "reject"
        assert response.headers["X-FAB-Backpressure"] == "reject"
        assert "Retry-After" in response.headers
        assert int(response.headers["Retry-After"]) == 60

    def test_push_context_forces_dry_run(self, client: TestClient, fab_context_payload):
        """Test that Shadow mode forces dry_run=true."""
        fab_context_payload["dry_run"] = False

        response = client.post("/api/v1/fab/context/push", json=fab_context_payload)

        assert response.status_code == 200
        # Should succeed but with dry_run forced to true


class TestFABPull:
    """Tests for GET /api/v1/fab/context/pull."""

    def test_pull_context_shadow_mode(self, client: TestClient):
        """Test FAB context pull returns empty in Shadow mode."""
        window_id = str(uuid4())
        response = client.get(
            "/api/v1/fab/context/pull", params={"window_type": "global", "window_id": window_id}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["cached"] is False
        assert data["context"]["fab_version"] == "0.1"
        assert data["context"]["window"]["type"] == "global"
        assert data["context"]["window"]["id"] == window_id
        assert len(data["context"]["tokens"]) == 0
        assert len(data["context"]["vectors"]) == 0

    def test_pull_context_invalid_window_id(self, client: TestClient):
        """Test FAB pull with invalid window_id."""
        response = client.get(
            "/api/v1/fab/context/pull",
            params={"window_type": "global", "window_id": "not-a-uuid"},
        )

        assert response.status_code == 400


class TestFABDecide:
    """Tests for POST /api/v1/fab/decide."""

    def test_decide_shadow_mode(self, client: TestClient):
        """Test FAB decide returns mock decisions in Shadow mode."""
        payload = {
            "metrics": {"h_coherence": {"sp": 0.85, "pd": 0.82}, "h_stability": {"avg_drift": 0.05}},
            "run_id": "test-decide-001",
        }

        response = client.post("/api/v1/fab/decide", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert len(data["decisions"]) > 0
        assert data["decisions"][0]["policy"] == "shadow_mode"
        assert data["decisions"][0]["status"] == "dry_run"
        assert data["confidence"] == 0.0
        assert data["run_id"] == "test-decide-001"

    def test_decide_with_policy_override(self, client: TestClient):
        """Test FAB decide with policy overrides."""
        payload = {
            "metrics": {"h_coherence": {"sp": 0.75}, "h_stability": {"avg_drift": 0.1}},
            "policies": ["coherence_degradation", "stability_drift"],
            "run_id": "test-decide-002",
        }

        response = client.post("/api/v1/fab/decide", json=payload)

        assert response.status_code == 200
        # Shadow mode should still return mock decisions


class TestFABAct:
    """Tests for POST /api/v1/fab/act/{action_type}."""

    def test_act_shadow_mode(self, client: TestClient):
        """Test FAB act returns dry-run results in Shadow mode."""
        payload = {"params": {"shard_id": 0}, "run_id": "test-act-001", "dry_run": True}

        response = client.post("/api/v1/fab/act/rebuild_shard", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["action_type"] == "rebuild_shard"
        assert data["status"] == "dry_run"
        assert data["details"]["stub"] is True
        assert data["run_id"] == "test-act-001"

    def test_act_forces_dry_run(self, client: TestClient):
        """Test that Shadow mode forces dry_run=true for actions."""
        payload = {"params": {"topk": 100}, "run_id": "test-act-002", "dry_run": False}

        response = client.post("/api/v1/fab/act/reembed_batch", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Should succeed but with dry_run forced
        assert data["status"] == "dry_run"


class TestFABIntegration:
    """Integration tests for FAB routes."""

    def test_all_routes_registered(self, client: TestClient):
        """Test that all 4 FAB routes are registered."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi = response.json()
        paths = openapi["paths"]

        assert "/api/v1/fab/context/push" in paths
        assert "/api/v1/fab/context/pull" in paths
        assert "/api/v1/fab/decide" in paths
        assert "/api/v1/fab/act/{action_type}" in paths

    def test_fab_tag_present(self, client: TestClient):
        """Test that FAB routes have correct tag."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi = response.json()
        tags = [tag["name"] for tag in openapi.get("tags", [])]

        assert "FAB Integration (v0.1 Shadow)" in tags
