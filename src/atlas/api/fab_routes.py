"""
FAB API Routes (v0.1 — Shadow Mode)

Atlas × FAB Integration endpoints as specified in
AURIS_FAB_Integration_Plan_v0.1.txt

Routes:
    POST /api/v1/fab/context/push  — Push context to FAB (dry_run default)
    GET  /api/v1/fab/context/pull  — Pull merged context (E2 + FAB overlays)
    POST /api/v1/fab/decide        — E4.1/E4.2 policy decisions
    POST /api/v1/fab/act/{action_type} — E4.3 action execution (dry_run default)

Phased Rollout (current: Shadow):
    - Phase 1 (Shadow): All routes dry_run=true, collect metrics only
    - Phase 2 (Mirroring): Write-through to FAB cache + E2 indices
    - Phase 3 (Cutover): Enable actions with rate limits + SLO monitoring

Backpressure:
    - Token bucket per-actor/per-window
    - Response headers: X-FAB-Backpressure (ok|slow|reject), Retry-After
    - Anti-oscillation: Tied to E4.2 anti-flapping (300s cooldown)

Dependencies:
    - E2 Index Builders (HNSW/FAISS)
    - E3 Metrics (h_coherence, h_stability)
    - E4 Homeostasis (policy engine, decision engine, action adapters)
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Request, Response

from .fab_schemas import (
    BackpressureStatus,
    FABActRequest,
    FABActResponse,
    FABDecideRequest,
    FABDecideResponse,
    FABPullResponse,
    FABPushRequest,
    FABPushResponse,
)

logger = logging.getLogger(__name__)


def create_fab_router() -> APIRouter:
    """
    Create FAB integration router with 4 endpoints.

    Returns:
        APIRouter: Configured router for /api/v1/fab/*
    """
    router = APIRouter(prefix="/api/v1/fab", tags=["FAB Integration (v0.1 Shadow)"])

    @router.post(
        "/context/push",
        response_model=FABPushResponse,
        summary="Push context to FAB",
        description="""
        Push FAB context window (global or stream) to Atlas.

        **Phase 1 (Shadow):**
        - Default: dry_run=true (safe mode)
        - Validates JSON schema
        - Checks backpressure limits
        - Collects metrics (no actual indexing)

        **Backpressure:**
        - ok: Normal operation
        - slow: Approaching limits (reduce rate)
        - reject: Over limit (retry after delay)

        **Response Headers:**
        - X-FAB-Backpressure: ok|slow|reject
        - Retry-After: Seconds to wait (if reject)
        """,
    )
    async def push_context(
        _request: Request,  # pylint: disable=unused-argument
        response: Response,
        body: FABPushRequest,
        x_fab_actor: Optional[str] = Header(None, description="Actor ID for rate limiting"),
    ) -> FABPushResponse:
        """
        Push FAB context window.

        Phase 1 (Shadow): Dry-run only, no actual indexing.
        """
        try:
            # Shadow mode: always dry_run in v0.1
            if not body.dry_run:
                logger.warning(
                    "FAB v0.1 Shadow mode: forcing dry_run=true (write-through not enabled)"
                )
                body.dry_run = True

            # Validate schema (already done by Pydantic)
            context = body.context

            # Check token bucket (stub in Shadow mode)
            actor_id = x_fab_actor or "anonymous"
            backpressure_status = _check_backpressure(actor_id, len(context.tokens))

            if backpressure_status == BackpressureStatus.REJECT:
                response.headers["X-FAB-Backpressure"] = "reject"
                response.headers["Retry-After"] = "60"  # 1 minute
                return FABPushResponse(
                    accepted=False,
                    backpressure=BackpressureStatus.REJECT,
                    reasons=["Rate limit exceeded", f"Actor: {actor_id}"],
                    ids=[],
                    run_id=body.run_id,
                )

            # Shadow mode: no actual work, just validate + metrics
            logger.info(
                "FAB push (shadow): window=%s, tokens=%d, vectors=%d, run_id=%s",
                context.window.type.value,
                len(context.tokens),
                len(context.vectors),
                body.run_id,
            )

            # Set backpressure header
            response.headers["X-FAB-Backpressure"] = backpressure_status.value

            return FABPushResponse(
                accepted=True,
                backpressure=backpressure_status,
                reasons=[],
                ids=[],  # Shadow mode: no indexing yet
                run_id=body.run_id,
            )

        except Exception as e:
            logger.exception("FAB push failed")
            raise HTTPException(status_code=500, detail=f"FAB push failed: {e}") from e

    @router.get(
        "/context/pull",
        response_model=FABPullResponse,
        summary="Pull FAB context",
        description="""
        Pull merged FAB context window (E2 indices + FAB overlays).

        **Phase 1 (Shadow):**
        - Returns empty context (no FAB cache yet)
        - Validates window_type and window_id

        **Phase 2 (Mirroring):**
        - Returns merged view of E2 indices + FAB cache
        """,
    )
    async def pull_context(
        window_type: str,
        window_id: str,
    ) -> FABPullResponse:
        """
        Pull FAB context window.

        Phase 1 (Shadow): Returns empty context (no cache yet).
        """
        try:
            # Shadow mode: no FAB cache yet
            logger.info("FAB pull (shadow): window_type=%s, id=%s", window_type, window_id)

            # Would query E2 indices + FAB overlays in Phase 2
            # For now, return empty context
            from datetime import datetime, timezone
            from uuid import UUID

            from .fab_schemas import FABContext, FABMeta, FABWindow, WindowType

            context = FABContext(
                fab_version="0.1",
                window=FABWindow(
                    type=WindowType(window_type),
                    id=UUID(window_id),
                    ts=datetime.now(timezone.utc),
                ),
                tokens=[],
                vectors=[],
                links=[],
                meta=FABMeta(),
            )

            return FABPullResponse(context=context, cached=False)

        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid window parameters: {e}") from e
        except Exception as e:
            logger.exception("FAB pull failed")
            raise HTTPException(status_code=500, detail=f"FAB pull failed: {e}") from e

    @router.post(
        "/decide",
        response_model=FABDecideResponse,
        summary="FAB policy decisions (E4.1/E4.2)",
        description="""
        Use E4.1 Policy Engine + E4.2 Decision Engine to determine actions.

        **Inputs:**
        - metrics: E3 metrics (h_coherence, h_stability)
        - policies: Optional policy overrides (E4.1)

        **Outputs:**
        - decisions: Proposed actions from E4.2
        - confidence: Decision confidence (0.0-1.0)

        **Phase 1 (Shadow):**
        - Validates metrics format
        - Returns mock decisions (no actual E4 calls)
        """,
    )
    async def decide(body: FABDecideRequest) -> FABDecideResponse:
        """
        Run E4.1/E4.2 policy decisions.

        Phase 1 (Shadow): Mock decisions, no actual E4 calls.
        """
        try:
            logger.info("FAB decide (shadow): metrics=%s, run_id=%s", body.metrics, body.run_id)

            # Shadow mode: return mock decisions
            # Phase 2 will call actual E4.1/E4.2
            return FABDecideResponse(
                decisions=[
                    {
                        "policy": "shadow_mode",
                        "status": "dry_run",
                        "reason": "FAB v0.1 Shadow mode: no actual E4 calls",
                        "actions": [],
                    }
                ],
                confidence=0.0,
                run_id=body.run_id,
            )

        except Exception as e:
            logger.exception("FAB decide failed")
            raise HTTPException(status_code=500, detail=f"FAB decide failed: {e}") from e

    @router.post(
        "/act/{action_type}",
        response_model=FABActResponse,
        summary="Execute FAB action (E4.3)",
        description="""
        Proxy to E4.3 Action Adapters for FAB-triggered actions.

        **Default: dry_run=true** (safe mode)

        **Phase 1 (Shadow):**
        - Validates action_type and params
        - Returns dry_run results (no actual execution)

        **Phase 3 (Cutover):**
        - Calls E4.3 with rate limits (tied to E4.2 anti-flapping)
        - Respects backpressure + SLO monitors
        """,
    )
    async def act(action_type: str, body: FABActRequest) -> FABActResponse:
        """
        Execute FAB action via E4.3.

        Phase 1 (Shadow): Dry-run only, no actual execution.
        """
        try:
            # Shadow mode: always dry_run
            if not body.dry_run:
                logger.warning(
                    "FAB v0.1 Shadow mode: forcing dry_run=true for action=%s", action_type
                )
                body.dry_run = True

            logger.info(
                "FAB act (shadow): action=%s, params=%s, run_id=%s",
                action_type,
                body.params,
                body.run_id,
            )

            return FABActResponse(
                action_type=action_type,
                status="dry_run",
                message=f"FAB v0.1 Shadow mode: dry-run for {action_type}",
                details={"params": body.params, "would_execute": True, "stub": True},
                run_id=body.run_id,
            )

        except Exception as e:
            logger.exception("FAB act failed: action=%s", action_type)
            raise HTTPException(
                status_code=500, detail=f"FAB act failed for {action_type}: {e}"
            ) from e

    return router


def _check_backpressure(actor_id: str, token_count: int) -> BackpressureStatus:
    """
    Check backpressure status for actor.

    Phase 1 (Shadow): Simple threshold-based logic.
    Phase 2+: Token bucket per-actor/per-window.

    Args:
        actor_id: Actor identifier for rate limiting
        token_count: Number of tokens in request

    Returns:
        BackpressureStatus: ok, slow, or reject
    """
    # Shadow mode: simple thresholds
    # Phase 2+ will use token bucket with E4.2 anti-flapping
    if token_count > 5000:  # Hard limit
        logger.warning("Backpressure REJECT: actor=%s, tokens=%d", actor_id, token_count)
        return BackpressureStatus.REJECT

    if token_count > 2000:  # Soft limit
        logger.warning("Backpressure SLOW: actor=%s, tokens=%d", actor_id, token_count)
        return BackpressureStatus.SLOW

    return BackpressureStatus.OK
