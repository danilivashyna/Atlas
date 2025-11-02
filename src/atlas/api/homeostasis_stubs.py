# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Homeostasis Stubs for App.State

Temporary stub implementations for E4 components to enable API routes
until full integration is complete. These stubs provide minimal functionality
to satisfy the interface contracts expected by homeostasis_routes.py.

Usage:
    from atlas.api.homeostasis_stubs import create_homeostasis_stubs

    app.state.policy_engine = stubs["policy_engine"]
    app.state.action_executor = stubs["action_executor"]
    app.state.audit_logger = stubs["audit_logger"]
    app.state.snapshot_manager = stubs["snapshot_manager"]
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional


class StubPolicyEngine:
    """Stub PolicyEngine for E4.7 API routes."""

    def test(
        self, metrics: Dict[str, Any], options: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Return mock policy decisions based on metrics.

        Real implementation will evaluate E4.1 policies against metrics.
        """
        decisions = []

        # Check h_coherence (stub threshold: 0.85)
        h_coh = metrics.get("h_coherence", {})
        if isinstance(h_coh, dict):
            sp = h_coh.get("sp", 1.0)
            pd = h_coh.get("pd", 1.0)
            if sp < 0.85 or pd < 0.85:
                decisions.append({
                    "policy": "coherence_degradation",
                    "status": "triggered",
                    "reason": f"h_coherence below threshold (sp={sp:.2f}, pd={pd:.2f})",
                    "actions": [{"type": "rebuild_shard", "shard_id": 0}],
                })

        # Check h_stability (stub threshold: drift > 0.05)
        h_stab = metrics.get("h_stability", {})
        if isinstance(h_stab, dict):
            drift = h_stab.get("avg_drift", 0.0)
            if drift > 0.05:
                decisions.append({
                    "policy": "stability_drift",
                    "status": "triggered",
                    "reason": f"h_stability drift exceeded (drift={drift:.3f})",
                    "actions": [{"type": "reembed_batch", "topk": 100}],
                })

        if not decisions:
            decisions.append({
                "policy": "noop",
                "status": "ok",
                "reason": "All metrics within thresholds",
                "actions": [],
            })

        return decisions


class StubActionExecutor:
    """Stub ActionExecutor for E4.7 API routes."""

    def dry_run(self, action_type: str, **params: Any) -> Dict[str, Any]:
        """
        Return dry-run result (what would be done).

        Real implementation will call E4.3 ActionAdapter.dry_run().
        """
        return {
            "action_type": action_type,
            "params": params,
            "would_execute": True,
            "estimated_duration": "5-30s",
            "stub": True,
        }

    def execute(self, action_type: str, **params: Any) -> Dict[str, Any]:
        """
        Return execution result (stub: no actual work).

        Real implementation will call E4.3 ActionAdapter.execute().
        """
        time.sleep(0.1)  # Simulate brief work
        return {
            "action_type": action_type,
            "params": params,
            "executed": True,
            "duration": "0.1s",
            "stub": True,
            "warning": "Stub implementation - no actual homeostasis action performed",
        }


class StubAuditLogger:
    """Stub AuditLogger for E4.7 API routes."""

    def __init__(self) -> None:
        """Initialize in-memory event log."""
        self.events: List[Dict[str, Any]] = []

    def log_policy_triggered(
        self,
        run_id: Optional[str],
        policy: str,
        metrics: Dict[str, Any],
        reason: str,
    ) -> None:
        """Log POLICY_TRIGGERED event."""
        self.events.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "POLICY_TRIGGERED",
            "run_id": run_id,
            "policy": policy,
            "reason": reason,
        })

    def log_decision_made(
        self, run_id: Optional[str], policy: str, decision: Dict[str, Any]
    ) -> None:
        """Log DECISION_MADE event."""
        self.events.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "DECISION_MADE",
            "run_id": run_id,
            "policy": policy,
            "status": decision.get("status"),
        })

    def log_action_started(
        self,
        run_id: Optional[str],
        action_type: str,
        params: Dict[str, Any],
        dry_run: bool,
    ) -> None:
        """Log ACTION_STARTED event."""
        self.events.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "ACTION_STARTED",
            "run_id": run_id,
            "action_type": action_type,
            "dry_run": dry_run,
        })

    def log_action_skipped(
        self, run_id: Optional[str], action_type: str, reason: str
    ) -> None:
        """Log ACTION_SKIPPED event."""
        self.events.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "ACTION_SKIPPED",
            "run_id": run_id,
            "action_type": action_type,
            "reason": reason,
        })

    def log_action_completed(
        self, run_id: Optional[str], action_type: str, details: Dict[str, Any]
    ) -> None:
        """Log ACTION_COMPLETED event."""
        self.events.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "ACTION_COMPLETED",
            "run_id": run_id,
            "action_type": action_type,
        })

    def log_action_failed(
        self, run_id: Optional[str], action_type: str, error: str
    ) -> None:
        """Log ACTION_FAILED event."""
        self.events.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "ACTION_FAILED",
            "run_id": run_id,
            "action_type": action_type,
            "error": error,
        })

    def query(
        self,
        run_id: Optional[str] = None,
        event_type: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Query audit events with filters.

        Real implementation will read from E4.5 WAL (JSONL file).
        """
        filtered = self.events

        if run_id:
            filtered = [e for e in filtered if e.get("run_id") == run_id]

        if event_type:
            filtered = [e for e in filtered if e.get("event_type") == event_type]

        if since:
            filtered = [e for e in filtered if e.get("timestamp", "") >= since]

        if until:
            filtered = [e for e in filtered if e.get("timestamp", "") <= until]

        return filtered[-limit:] if limit else filtered


class StubSnapshotManager:
    """Stub SnapshotManager for E4.7 API routes."""

    def __init__(self) -> None:
        """Initialize in-memory snapshot registry."""
        self.snapshots: Dict[str, Dict[str, Any]] = {}

    def create_snapshot(
        self, reason: str = "manual", metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create snapshot metadata (stub: no actual files).

        Real implementation will copy indices + MANIFEST to E4.4 snapshot dir.
        """
        now = time.time()
        snapshot_id = time.strftime("%Y%m%d_%H%M%S", time.gmtime(now))

        snapshot = {
            "snapshot_id": snapshot_id,
            "created_at": now,
            "reason": reason,
            "checksums": {
                "indices/shard_0.bin": "stub_checksum_abc123",
                "MANIFEST.json": "stub_checksum_def456",
            },
            "stub": True,
        }

        self.snapshots[snapshot_id] = snapshot
        return snapshot

    def rollback(self, snapshot_id: str) -> None:
        """
        Rollback to snapshot (stub: verify existence only).

        Real implementation will verify checksums and copy files from E4.4 snapshot.
        """
        if snapshot_id not in self.snapshots:
            raise ValueError(f"Snapshot '{snapshot_id}' not found")

        # Stub: no actual file operations
        return None

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """List all snapshots (stub: in-memory registry)."""
        return list(self.snapshots.values())

    def get_snapshot_age(self, snapshot_id: str) -> float:
        """Get snapshot age in seconds."""
        if snapshot_id not in self.snapshots:
            raise ValueError(f"Snapshot '{snapshot_id}' not found")

        created_at = self.snapshots[snapshot_id]["created_at"]
        return time.time() - created_at


def create_homeostasis_stubs() -> Dict[str, Any]:
    """
    Create stub instances for homeostasis components.

    Returns:
        Dict with keys: policy_engine, action_executor, audit_logger, snapshot_manager

    Example:
        stubs = create_homeostasis_stubs()
        app.state.policy_engine = stubs["policy_engine"]
        app.state.action_executor = stubs["action_executor"]
        app.state.audit_logger = stubs["audit_logger"]
        app.state.snapshot_manager = stubs["snapshot_manager"]
    """
    return {
        "policy_engine": StubPolicyEngine(),
        "action_executor": StubActionExecutor(),
        "audit_logger": StubAuditLogger(),
        "snapshot_manager": StubSnapshotManager(),
    }
