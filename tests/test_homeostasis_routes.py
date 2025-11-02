# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Tests for Atlas Homeostasis API Routes (E4.7)

Проверяет:
- POST /policies/test: Dry-run policy decisions
- POST /actions/{action_type}: Manual repairs with dry_run
- GET /audit: Query WAL
- POST /snapshots: Create snapshot
- POST /snapshots/rollback: Rollback to snapshot

Uses mock dependencies in app.state for isolation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from atlas.api.homeostasis_routes import create_homeostasis_router


class MockPolicyEngine:
    """Mock PolicyEngine for testing."""

    def test(
        self, metrics: Dict[str, Any], options: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Return mock policy decisions."""
        return [
            {
                "policy": "test_policy",
                "status": "triggered",
                "reason": "test metric exceeded threshold",
                "actions": [{"type": "rebuild_shard", "shard_id": 0}],
            }
        ]


class MockActionExecutor:
    """Mock ActionExecutor for testing."""

    def dry_run(self, action_type: str, **params: Any) -> Dict[str, Any]:
        """Return mock dry-run result."""
        return {"action_type": action_type, "params": params, "would_execute": True}

    def execute(self, action_type: str, **params: Any) -> Dict[str, Any]:
        """Return mock execution result."""
        return {"action_type": action_type, "params": params, "executed": True}


class MockAuditLogger:
    """Mock AuditLogger for testing."""

    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []

    def log_policy_triggered(
        self, run_id: Optional[str], policy: str, metrics: Dict[str, Any], reason: str
    ) -> None:
        """Log policy triggered event."""
        self.events.append(
            {
                "event_type": "POLICY_TRIGGERED",
                "run_id": run_id,
                "policy": policy,
                "reason": reason,
            }
        )

    def log_decision_made(
        self, run_id: Optional[str], policy: str, decision: Dict[str, Any]
    ) -> None:
        """Log decision made event."""
        self.events.append({"event_type": "DECISION_MADE", "run_id": run_id, "policy": policy})

    def log_action_started(
        self,
        run_id: Optional[str],
        action_type: str,
        params: Dict[str, Any],
        dry_run: bool,
    ) -> None:
        """Log action started event."""
        self.events.append(
            {
                "event_type": "ACTION_STARTED",
                "run_id": run_id,
                "action_type": action_type,
                "dry_run": dry_run,
            }
        )

    def log_action_skipped(self, run_id: Optional[str], action_type: str, reason: str) -> None:
        """Log action skipped event."""
        self.events.append(
            {
                "event_type": "ACTION_SKIPPED",
                "run_id": run_id,
                "action_type": action_type,
                "reason": reason,
            }
        )

    def log_action_completed(
        self, run_id: Optional[str], action_type: str, details: Dict[str, Any]
    ) -> None:
        """Log action completed event."""
        self.events.append(
            {
                "event_type": "ACTION_COMPLETED",
                "run_id": run_id,
                "action_type": action_type,
            }
        )

    def log_action_failed(self, run_id: Optional[str], action_type: str, error: str) -> None:
        """Log action failed event."""
        self.events.append(
            {
                "event_type": "ACTION_FAILED",
                "run_id": run_id,
                "action_type": action_type,
                "error": error,
            }
        )

    def query(
        self,
        run_id: Optional[str] = None,
        event_type: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query audit events."""
        filtered = self.events

        if run_id:
            filtered = [e for e in filtered if e.get("run_id") == run_id]

        if event_type:
            filtered = [e for e in filtered if e.get("event_type") == event_type]

        return filtered[:limit]


class MockSnapshotManager:
    """Mock SnapshotManager for testing."""

    def create_snapshot(self, reason: str = "manual") -> Dict[str, Any]:
        """Return mock snapshot metadata."""
        now = datetime.utcnow().timestamp()
        return {
            "snapshot_id": "20251028_120000_000000",
            "created_at": now,
            "reason": reason,
            "checksums": {"indices/shard_0.bin": "abc123", "MANIFEST.json": "def456"},
        }

    def rollback(self, snapshot_id: str) -> None:
        """Mock rollback (no-op)."""
        if snapshot_id == "invalid_id":
            raise ValueError("Snapshot not found")


@pytest.fixture
def app() -> FastAPI:
    """Create FastAPI app with homeostasis router and mock dependencies."""
    app = FastAPI()

    # Setup mock dependencies in app.state
    app.state.policy_engine = MockPolicyEngine()
    app.state.action_executor = MockActionExecutor()
    app.state.audit_logger = MockAuditLogger()
    app.state.snapshot_manager = MockSnapshotManager()

    # Include homeostasis router
    app.include_router(create_homeostasis_router())

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


class TestPoliciesTest:
    """Tests for POST /api/v1/homeostasis/policies/test."""

    def test_policies_test_success(self, client: TestClient) -> None:
        """Тест успешного dry-run решений."""
        response = client.post(
            "/api/v1/homeostasis/policies/test",
            json={
                "run_id": "test_run_1",
                "metrics": {"h_coherence": 0.5, "h_stability": 0.3},
                "options": {},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == "test_run_1"
        assert len(data["decisions"]) == 1
        assert data["decisions"][0]["policy"] == "test_policy"
        assert data["decisions"][0]["status"] == "triggered"

    def test_policies_test_no_run_id(self, client: TestClient) -> None:
        """Тест без run_id (опциональный)."""
        response = client.post(
            "/api/v1/homeostasis/policies/test",
            json={"metrics": {"h_coherence": 0.8}},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] is None


class TestActionsExecute:
    """Tests for POST /api/v1/homeostasis/actions/{action_type}."""

    def test_action_dry_run_default(self, client: TestClient) -> None:
        """Тест dry_run=true по умолчанию."""
        response = client.post(
            "/api/v1/homeostasis/actions/rebuild_shard",
            json={"run_id": "test_run_2", "params": {"shard_id": 0}},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["action_type"] == "rebuild_shard"
        assert data["status"] == "dry_run"
        assert data["message"] == "Dry-run completed"
        assert "would_execute" in data["details"]

    def test_action_execute(self, client: TestClient) -> None:
        """Тест реального выполнения (dry_run=false)."""
        response = client.post(
            "/api/v1/homeostasis/actions/rebuild_shard",
            json={
                "run_id": "test_run_3",
                "dry_run": False,
                "params": {"shard_id": 0},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["message"] == "Action executed"
        assert data["details"]["executed"] is True


class TestAuditQuery:
    """Tests for GET /api/v1/homeostasis/audit."""

    def test_audit_query_all(self, client: TestClient, app: FastAPI) -> None:
        """Тест выборки всех событий."""
        # Trigger some events first
        client.post(
            "/api/v1/homeostasis/policies/test",
            json={"run_id": "test_run_4", "metrics": {}},
        )

        response = client.get("/api/v1/homeostasis/audit")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 2  # POLICY_TRIGGERED + DECISION_MADE
        assert len(data["items"]) >= 2

    def test_audit_query_by_run_id(self, client: TestClient) -> None:
        """Тест фильтрации по run_id."""
        client.post(
            "/api/v1/homeostasis/policies/test",
            json={"run_id": "test_run_5", "metrics": {}},
        )

        response = client.get("/api/v1/homeostasis/audit?run_id=test_run_5")

        assert response.status_code == 200
        data = response.json()
        assert all(item.get("run_id") == "test_run_5" for item in data["items"])

    def test_audit_query_by_event_type(self, client: TestClient) -> None:
        """Тест фильтрации по event_type."""
        client.post(
            "/api/v1/homeostasis/policies/test",
            json={"run_id": "test_run_6", "metrics": {}},
        )

        response = client.get("/api/v1/homeostasis/audit?event_type=POLICY_TRIGGERED")

        assert response.status_code == 200
        data = response.json()
        assert all(item.get("event_type") == "POLICY_TRIGGERED" for item in data["items"])

    def test_audit_query_with_limit(self, client: TestClient) -> None:
        """Тест с ограничением количества."""
        response = client.get("/api/v1/homeostasis/audit?limit=1")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 1


class TestSnapshots:
    """Tests for POST /api/v1/homeostasis/snapshots."""

    def test_snapshot_create(self, client: TestClient) -> None:
        """Тест создания снапшота."""
        response = client.post(
            "/api/v1/homeostasis/snapshots",
            json={"run_id": "test_run_7", "reason": "manual test"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == "test_run_7"
        assert "snapshot_id" in data
        assert "created_at" in data
        assert len(data["checksums"]) > 0


class TestSnapshotRollback:
    """Tests for POST /api/v1/homeostasis/snapshots/rollback."""

    def test_rollback_success(self, client: TestClient) -> None:
        """Тест успешного отката."""
        response = client.post(
            "/api/v1/homeostasis/snapshots/rollback",
            json={"run_id": "test_run_8", "snapshot_id": "20251028_120000_000000"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["message"] == "rollback completed"

    def test_rollback_not_found(self, client: TestClient) -> None:
        """Тест отката с несуществующим snapshot_id."""
        response = client.post(
            "/api/v1/homeostasis/snapshots/rollback",
            json={"run_id": "test_run_9", "snapshot_id": "invalid_id"},
        )

        assert response.status_code == 500
        assert "rollback failed" in response.json()["detail"]


class TestErrorCases:
    """Tests for error handling."""

    def test_missing_policy_engine(self, app: FastAPI, client: TestClient) -> None:
        """Тест отсутствия policy_engine."""
        app.state.policy_engine = None

        response = client.post("/api/v1/homeostasis/policies/test", json={"metrics": {}})

        assert response.status_code == 503
        assert "PolicyEngine not initialized" in response.json()["detail"]

        # Restore for other tests
        app.state.policy_engine = MockPolicyEngine()

    def test_missing_audit_logger(self, app: FastAPI, client: TestClient) -> None:
        """Тест отсутствия audit_logger (не должно ломать операцию)."""
        original_audit = app.state.audit_logger
        app.state.audit_logger = None

        response = client.post("/api/v1/homeostasis/policies/test", json={"metrics": {}})

        # Should still succeed without audit
        assert response.status_code == 200

        # Restore
        app.state.audit_logger = original_audit
