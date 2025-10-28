# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna
"""
Atlas Homeostasis API Routes (E4.7)

Control plane for homeostasis subsystem:
- POST /api/v1/homeostasis/policies/test: Dry-run policy decisions
- POST /api/v1/homeostasis/actions/{action_type}: Manual repairs (default dry_run=true)
- GET /api/v1/homeostasis/audit: Query WAL by run_id/event_type/time window
- POST /api/v1/homeostasis/snapshots: Create snapshot with checksums
- POST /api/v1/homeostasis/snapshots/rollback: Rollback by snapshot_id

All routes support run_id for idempotency. Errors mapped to 4xx/5xx with reason.
Audit chain: POLICY_TRIGGERED → DECISION_MADE → ACTION_*.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field


class PolicyTestRequest(BaseModel):
    """Request body for POST /policies/test."""
    run_id: Optional[str] = Field(default=None, description="Idempotency key")
    metrics: Dict[str, Any] = Field(..., description="Snapshot of E3 metrics")
    options: Dict[str, Any] = Field(default_factory=dict)


class PolicyDecision(BaseModel):
    """Single policy decision result."""
    policy: str
    status: str
    reason: str
    actions: List[Dict[str, Any]] = []


class PolicyTestResponse(BaseModel):
    """Response for POST /policies/test."""
    run_id: Optional[str]
    decisions: List[PolicyDecision]


class ActionRequest(BaseModel):
    """Request body for POST /actions/{action_type}."""
    run_id: Optional[str] = None
    dry_run: bool = True
    params: Dict[str, Any] = Field(default_factory=dict)


class ActionResponse(BaseModel):
    """Response for POST /actions/{action_type}."""
    run_id: Optional[str]
    action_type: str
    status: str
    message: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class AuditQueryResponse(BaseModel):
    """Response for GET /audit."""
    items: List[Dict[str, Any]]
    count: int


class SnapshotCreateRequest(BaseModel):
    """Request body for POST /snapshots."""
    run_id: Optional[str] = None
    reason: str = "manual"


class SnapshotCreateResponse(BaseModel):
    """Response for POST /snapshots."""
    run_id: Optional[str]
    snapshot_id: str
    created_at: datetime
    checksums: Dict[str, str] = Field(default_factory=dict)


class SnapshotRollbackRequest(BaseModel):
    """Request body for POST /snapshots/rollback."""
    run_id: Optional[str] = None
    snapshot_id: str


class SnapshotRollbackResponse(BaseModel):
    """Response for POST /snapshots/rollback."""
    run_id: Optional[str]
    snapshot_id: str
    status: str
    message: str


def _require(obj: Any, name: str) -> Any:
    """Require that an object is not None, or raise 503."""
    if obj is None:
        raise HTTPException(status_code=503, detail=f"{name} not initialized")
    return obj


def create_homeostasis_router() -> APIRouter:
    """
    Create homeostasis router.
    
    Expects app.state to have:
    - policy_engine: PolicyEngine instance
    - action_executor: ActionExecutor instance
    - audit_logger: AuditLogger instance (optional)
    - snapshot_manager: SnapshotManager instance
    """
    r = APIRouter(prefix="/api/v1/homeostasis", tags=["homeostasis"])

    @r.post("/policies/test", response_model=PolicyTestResponse)
    async def policies_test(req: Request, body: PolicyTestRequest) -> PolicyTestResponse:
        """
        Dry-run policy decisions against metrics snapshot.
        
        No side effects, returns list of decisions that would be made.
        Logs POLICY_TRIGGERED and DECISION_MADE to audit if available.
        """
        state = req.app.state
        policy_engine = _require(getattr(state, "policy_engine", None), "PolicyEngine")
        audit = getattr(state, "audit_logger", None)

        decisions = policy_engine.test(body.metrics, options=body.options)
        if audit:
            try:
                for d in decisions:
                    audit.log_policy_triggered(
                        run_id=body.run_id,
                        policy=d.get("policy"),
                        metrics=body.metrics,
                        reason=d.get("reason", ""),
                    )
                    audit.log_decision_made(
                        run_id=body.run_id, policy=d.get("policy"), decision=d
                    )
            except Exception:  # noqa: BLE001
                # Audit failures should not break the operation
                pass
        return PolicyTestResponse(
            run_id=body.run_id, decisions=[PolicyDecision(**d) for d in decisions]
        )

    @r.post("/actions/{action_type}", response_model=ActionResponse)
    async def actions_execute(
        req: Request, action_type: str, body: ActionRequest
    ) -> ActionResponse:
        """
        Execute or dry-run a homeostasis action.
        
        Default dry_run=true for safety. Set dry_run=false for actual execution.
        Logs ACTION_STARTED, ACTION_SKIPPED/COMPLETED/FAILED to audit.
        """
        state = req.app.state
        executor = _require(getattr(state, "action_executor", None), "ActionExecutor")
        audit = getattr(state, "audit_logger", None)

        started = datetime.utcnow()
        if audit:
            try:
                audit.log_action_started(
                    run_id=body.run_id,
                    action_type=action_type,
                    params=body.params,
                    dry_run=body.dry_run,
                )
            except Exception:  # noqa: BLE001
                # Audit failures should not break the operation
                pass

        try:
            if body.dry_run:
                details = executor.dry_run(action_type, **body.params)
                if audit:
                    try:
                        audit.log_action_skipped(
                            run_id=body.run_id,
                            action_type=action_type,
                            reason="dry_run",
                        )
                    except Exception:  # noqa: BLE001
                        # Audit failures should not break the operation
                        pass
                return ActionResponse(
                    run_id=body.run_id,
                    action_type=action_type,
                    status="dry_run",
                    message="Dry-run completed",
                    started_at=started,
                    finished_at=datetime.utcnow(),
                    details=details,
                )

            details = executor.execute(action_type, **body.params)
            if audit:
                try:
                    audit.log_action_completed(
                        run_id=body.run_id, action_type=action_type, details=details
                    )
                except Exception:  # noqa: BLE001
                    # Audit failures should not break the operation
                    pass
            return ActionResponse(
                run_id=body.run_id,
                action_type=action_type,
                status="completed",
                message="Action executed",
                started_at=started,
                finished_at=datetime.utcnow(),
                details=details,
            )
        except Exception as e:
            if audit:
                try:
                    audit.log_action_failed(
                        run_id=body.run_id, action_type=action_type, error=str(e)
                    )
                except Exception:  # noqa: BLE001
                    # Audit failures should not break the operation
                    pass
            raise HTTPException(
                status_code=500, detail=f"Action '{action_type}' failed: {e}"
            ) from e

    @r.get("/audit", response_model=AuditQueryResponse)
    async def audit_query(
        req: Request,
        run_id: Optional[str] = Query(default=None),
        event_type: Optional[str] = Query(default=None),
        since: Optional[str] = Query(default=None, description="ISO8601"),
        until: Optional[str] = Query(default=None, description="ISO8601"),
        limit: int = Query(default=100, ge=1, le=1000),
    ) -> AuditQueryResponse:
        """
        Query audit log (WAL).
        
        Filters: run_id, event_type, time window (since/until ISO8601), limit.
        Returns list of audit events matching criteria.
        """
        audit = _require(getattr(req.app.state, "audit_logger", None), "AuditLogger")
        try:
            items = audit.query(
                run_id=run_id,
                event_type=event_type,
                since=since,
                until=until,
                limit=limit,
            )
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"audit query error: {e}"
            ) from e
        return AuditQueryResponse(items=items, count=len(items))

    @r.post("/snapshots", response_model=SnapshotCreateResponse)
    async def snapshot_create(
        req: Request, body: SnapshotCreateRequest
    ) -> SnapshotCreateResponse:
        """
        Create snapshot of current state.
        
        Includes indices, MANIFEST, SHA256 checksums.
        Returns snapshot_id for future rollback.
        """
        sm = _require(getattr(req.app.state, "snapshot_manager", None), "SnapshotManager")
        snap = sm.create_snapshot(reason=body.reason)
        return SnapshotCreateResponse(
            run_id=body.run_id,
            snapshot_id=snap["snapshot_id"],
            created_at=datetime.utcfromtimestamp(snap["created_at"]),
            checksums=snap.get("checksums", {}),
        )

    @r.post("/snapshots/rollback", response_model=SnapshotRollbackResponse)
    async def snapshot_rollback(
        req: Request, body: SnapshotRollbackRequest
    ) -> SnapshotRollbackResponse:
        """
        Rollback to previous snapshot.
        
        Verifies SHA256 checksums before rollback.
        Creates backup of current state before overwriting.
        """
        sm = _require(getattr(req.app.state, "snapshot_manager", None), "SnapshotManager")
        try:
            sm.rollback(body.snapshot_id)
            return SnapshotRollbackResponse(
                run_id=body.run_id,
                snapshot_id=body.snapshot_id,
                status="ok",
                message="rollback completed",
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"rollback failed: {e}"
            ) from e

    return r
