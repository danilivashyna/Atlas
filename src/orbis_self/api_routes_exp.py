"""
SELF API Routes (Phase C.3)

Operator-facing API endpoints for monitoring and controlling SELF canary deployment:
- GET /self/health → текущие SELF метрики и статус canary
- POST /self/canary → безопасное изменение AURIS_SELF_CANARY

Phase: C.3 (Operator API)
Status: Experimental (2025-11-05)
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/self", tags=["SELF (Experimental)"])


# ════════════════════════════════════════════════════════════════════════
# Request/Response Models
# ════════════════════════════════════════════════════════════════════════


class SelfHealthResponse(BaseModel):
    """Response for GET /self/health."""

    enabled: bool = Field(description="AURIS_SELF master switch (on/off)")
    canary_sampling: float = Field(description="Current canary sampling rate [0.0, 1.0]")
    heartbeat_count: int = Field(description="Total heartbeats in identity.jsonl")
    last_heartbeat: Optional[Dict[str, Any]] = Field(description="Most recent heartbeat record")
    averages: Dict[str, float] = Field(description="Average SELF metrics (last 20 heartbeats)")
    slo_status: Dict[str, bool] = Field(description="Phase C SLO pass/fail status")


class CanaryUpdateRequest(BaseModel):
    """Request for POST /self/canary."""

    new_sampling: float = Field(ge=0.0, le=1.0, description="New canary sampling rate [0.0, 1.0]")
    reason: str = Field(
        min_length=5, max_length=200, description="Reason for change (for audit log)"
    )


class CanaryUpdateResponse(BaseModel):
    """Response for POST /self/canary."""

    success: bool = Field(description="Whether change was applied")
    old_sampling: float = Field(description="Previous canary sampling")
    new_sampling: float = Field(description="New canary sampling")
    reason: str = Field(description="Reason from request")
    note: str = Field(description="Additional notes (e.g., restart required)")


# ════════════════════════════════════════════════════════════════════════
# Helper Functions
# ════════════════════════════════════════════════════════════════════════


def _parse_identity_file() -> list:
    """Parse data/identity.jsonl and return heartbeat records."""
    identity_file = Path("data/identity.jsonl")
    if not identity_file.exists():
        return []

    heartbeats = []
    with open(identity_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if record.get("kind") == "heartbeat":
                    heartbeats.append(record)
            except json.JSONDecodeError:
                continue

    return heartbeats


def _compute_averages(heartbeats: list, last_n: int = 20) -> Dict[str, float]:
    """Compute average SELF metrics from last N heartbeats."""
    if not heartbeats:
        return {
            "coherence": 0.0,
            "continuity": 0.0,
            "presence": 0.0,
            "stress": 0.0,
        }

    recent = heartbeats[-last_n:]

    coherence_sum = sum(h.get("coherence", 0.0) for h in recent)
    continuity_sum = sum(h.get("continuity", 0.0) for h in recent)
    presence_sum = sum(h.get("presence", 0.0) for h in recent)
    stress_sum = sum(h.get("stress", 0.0) for h in recent)

    count = len(recent)

    return {
        "coherence": coherence_sum / count,
        "continuity": continuity_sum / count,
        "presence": presence_sum / count,
        "stress": stress_sum / count,
    }


def _check_slo_status(averages: Dict[str, float]) -> Dict[str, bool]:
    """Check SLO targets (Phase C)."""
    return {
        "coherence_slo": averages["coherence"] >= 0.80,
        "continuity_slo": averages["continuity"] >= 0.90,
        "stress_slo": averages["stress"] <= 0.30,
    }


# ════════════════════════════════════════════════════════════════════════
# Endpoints
# ════════════════════════════════════════════════════════════════════════


@router.get("/health", response_model=SelfHealthResponse)
def get_self_health() -> SelfHealthResponse:
    """
    Get SELF health status and canary metrics.

    Returns:
        SelfHealthResponse with current SELF state

    Example:
        ```bash
        curl http://localhost:8000/self/health
        ```

        Response:
        ```json
        {
          "enabled": true,
          "canary_sampling": 0.05,
          "heartbeat_count": 42,
          "last_heartbeat": {
            "kind": "heartbeat",
            "coherence": 0.95,
            "continuity": 0.98,
            "presence": 1.0,
            "stress": 0.12
          },
          "averages": {
            "coherence": 0.93,
            "continuity": 0.96,
            "presence": 1.0,
            "stress": 0.14
          },
          "slo_status": {
            "coherence_slo": true,
            "continuity_slo": true,
            "stress_slo": true
          }
        }
        ```
    """
    # Check if SELF is enabled
    self_enabled = os.getenv("AURIS_SELF", "off").lower() in ("on", "true", "1")

    # Get current canary sampling
    try:
        canary_sampling = float(os.getenv("AURIS_SELF_CANARY", "0.05"))
    except ValueError:
        canary_sampling = 0.05

    # Parse heartbeats
    heartbeats = _parse_identity_file()

    # Get last heartbeat
    last_heartbeat = heartbeats[-1] if heartbeats else None

    # Compute averages
    averages = _compute_averages(heartbeats, last_n=20)

    # Check SLO status
    slo_status = _check_slo_status(averages)

    return SelfHealthResponse(
        enabled=self_enabled,
        canary_sampling=canary_sampling,
        heartbeat_count=len(heartbeats),
        last_heartbeat=last_heartbeat,
        averages=averages,
        slo_status=slo_status,
    )


@router.post("/canary", response_model=CanaryUpdateResponse)
def update_canary_sampling(req: CanaryUpdateRequest) -> CanaryUpdateResponse:
    """
    Update AURIS_SELF_CANARY sampling rate.

    Args:
        req: CanaryUpdateRequest with new_sampling and reason

    Returns:
        CanaryUpdateResponse with old/new values and notes

    Raises:
        HTTPException: If update fails

    Example:
        ```bash
        curl -X POST http://localhost:8000/self/canary \\
          -H "Content-Type: application/json" \\
          -d '{
            "new_sampling": 0.25,
            "reason": "Advancing to 25% after 24h green metrics"
          }'
        ```

        Response:
        ```json
        {
          "success": true,
          "old_sampling": 0.05,
          "new_sampling": 0.25,
          "reason": "Advancing to 25% after 24h green metrics",
          "note": "⚠️  Restart required: systemctl restart atlas-api"
        }
        ```
    """
    # Get current sampling
    try:
        old_sampling = float(os.getenv("AURIS_SELF_CANARY", "0.05"))
    except ValueError:
        old_sampling = 0.05

    # Validate new_sampling
    new_sampling = req.new_sampling
    if not 0.0 <= new_sampling <= 1.0:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid new_sampling: {new_sampling} (must be [0.0, 1.0])",
        )

    # Log change for audit
    logger.info(
        "🔧 SELF canary update: %.2f → %.2f (reason: %s)",
        old_sampling,
        new_sampling,
        req.reason,
    )

    # Update env var (in-process only, requires restart for persistence)
    try:
        os.environ["AURIS_SELF_CANARY"] = str(new_sampling)
        success = True
    except Exception as e:
        logger.error("Failed to update AURIS_SELF_CANARY: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update env var: {e}",
        )

    return CanaryUpdateResponse(
        success=success,
        old_sampling=old_sampling,
        new_sampling=new_sampling,
        reason=req.reason,
        note="⚠️  Restart required for persistence: systemctl restart atlas-api",
    )
