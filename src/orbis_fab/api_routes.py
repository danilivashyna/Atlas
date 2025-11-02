"""FAB Shadow Mode API Routes (v0.1)

Lightweight HTTP endpoints for FAB observability and control without external I/O.
All routes operate on in-memory FABCore instance (no OneBlock/Atlas interaction).

Routes:
- POST /api/v1/fab/context/push — feed Z-slice, get diagnostics
- GET  /api/v1/fab/context/pull — current windows + gauges
- POST /api/v1/fab/decide — run step_stub with metrics
- POST /api/v1/fab/act — placeholder (no-op in Shadow Mode)

Design:
- Shadow Mode: FAB operates independently, no writes to Atlas
- Observability: diagnostics in every response
- Determinism: seeded operations for reproducibility
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status

from .core import FABCore
from .types import Budgets, ZSliceLite, FabMode


# === Request/Response Models ===

class ZNode(BaseModel):
    """Z-space node (vector representation)"""
    id: str
    score: float = Field(ge=0.0, le=1.0, description="Relevance score [0.0, 1.0]")
    # Optional: embedding vector (not used in Phase A/C)
    vec: Optional[List[float]] = None


class PushContextRequest(BaseModel):
    """Request to push Z-slice context into FAB"""
    mode: FabMode = Field(description="Target FAB mode (FAB0/FAB1/FAB2)")
    budgets: Budgets = Field(description="Fixed capacity for this tick")
    z_slice: Dict[str, Any] = Field(
        description="Z-slice with nodes/edges/quotas/seed",
        examples=[{
            "nodes": [{"id": "n1", "score": 0.95}, {"id": "n2", "score": 0.80}],
            "edges": [],
            "quotas": {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30},
            "seed": "test-run-42",
            "zv": "0.1"
        }]
    )


class PushContextResponse(BaseModel):
    """Response from push operation"""
    status: str = "ok"
    tick: int = Field(description="Current tick number")
    diagnostics: Dict[str, Any] = Field(description="Counters and gauges snapshot")


class PullContextResponse(BaseModel):
    """Response from pull operation (current FAB state)"""
    mode: str = Field(description="Current FAB mode")
    global_size: int = Field(description="Global window size")
    stream_size: int = Field(description="Stream window size")
    global_precision: str = Field(description="Global window precision")
    stream_precision: str = Field(description="Stream window precision")
    diagnostics: Dict[str, Any] = Field(description="Diagnostics snapshot")


class DecideRequest(BaseModel):
    """Request to run decision step"""
    stress: float = Field(ge=0.0, le=1.0, description="Load stress [0.0, 1.0]")
    self_presence: float = Field(ge=0.0, le=1.0, description="SELF token presence")
    error_rate: float = Field(ge=0.0, le=1.0, description="Error rate [0.0, 1.0]")


class DecideResponse(BaseModel):
    """Response from decision step"""
    mode: str = Field(description="Mode after decision")
    stable: bool = Field(description="Stability status")
    stable_ticks: int = Field(description="Consecutive stable ticks")
    diagnostics: Dict[str, Any] = Field(description="Diagnostics snapshot")


class ActResponse(BaseModel):
    """Response from act operation (no-op in Shadow Mode)"""
    status: str = "shadow_mode"
    message: str = "No external I/O in Shadow Mode v0.1"


# === FAB Shadow Mode Router ===

def create_fab_router(fab_core: Optional[FABCore] = None) -> APIRouter:
    """Create FAB Shadow Mode API router

    Args:
        fab_core: Optional pre-initialized FABCore instance.
                 If None, creates new instance with default config.

    Returns:
        FastAPI router with FAB Shadow Mode routes

    Example:
        app = FastAPI()
        fab_router = create_fab_router()
        app.include_router(fab_router, prefix="/api/v1/fab", tags=["FAB"])
    """
    router = APIRouter()

    # Initialize FABCore (or use provided instance)
    fab = fab_core or FABCore(envelope_mode="legacy")

    @router.post("/context/push", response_model=PushContextResponse)
    async def push_context(req: PushContextRequest) -> PushContextResponse:
        """Push Z-slice context into FAB

        Executes:
        1. init_tick(mode, budgets)
        2. fill(z_slice)
        3. mix() → get diagnostics

        Returns:
            Diagnostics snapshot after processing Z-slice

        Example:
            POST /api/v1/fab/context/push
            {
                "mode": "FAB1",
                "budgets": {"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30},
                "z_slice": {
                    "nodes": [{"id": "n1", "score": 0.95}],
                    "edges": [],
                    "quotas": {"tokens": 4096, "nodes": 256},
                    "seed": "test-42"
                }
            }
        """
        try:
            # Execute FAB tick
            fab.init_tick(mode=req.mode, budgets=req.budgets)
            # Type hint: z_slice is Dict but ZSliceLite is TypedDict, compatible at runtime
            fab.fill(req.z_slice)  # type: ignore[arg-type]
            ctx = fab.mix()

            return PushContextResponse(
                status="ok",
                tick=fab.current_tick,
                diagnostics=ctx["diagnostics"]
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"FAB push failed: {str(e)}"
            )

    @router.get("/context/pull", response_model=PullContextResponse)
    async def pull_context() -> PullContextResponse:
        """Pull current FAB state (windows + diagnostics)

        Returns current window sizes, precisions, and diagnostics
        without modifying state.

        Returns:
            Current FAB state snapshot

        Example:
            GET /api/v1/fab/context/pull
            Response:
            {
                "mode": "FAB1",
                "global_size": 200,
                "stream_size": 56,
                "diagnostics": {...}
            }
        """
        try:
            ctx = fab.mix()

            return PullContextResponse(
                mode=ctx["mode"],
                global_size=ctx["global_size"],
                stream_size=ctx["stream_size"],
                global_precision=ctx["global_precision"],
                stream_precision=ctx["stream_precision"],
                diagnostics=ctx["diagnostics"]
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"FAB pull failed: {str(e)}"
            )

    @router.post("/decide", response_model=DecideResponse)
    async def decide(req: DecideRequest) -> DecideResponse:
        """Run FAB decision step (state transitions)

        Executes step_stub() with provided metrics to drive
        FAB state machine transitions.

        Args:
            req: Metrics (stress, self_presence, error_rate)

        Returns:
            Mode after transition + stability status + diagnostics

        Example:
            POST /api/v1/fab/decide
            {
                "stress": 0.3,
                "self_presence": 0.85,
                "error_rate": 0.0
            }
        """
        try:
            result = fab.step_stub(
                stress=req.stress,
                self_presence=req.self_presence,
                error_rate=req.error_rate
            )

            # Get current diagnostics
            ctx = fab.mix()

            return DecideResponse(
                mode=result["mode"],
                stable=result["stable"],
                stable_ticks=result["stable_ticks"],
                diagnostics=ctx["diagnostics"]
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"FAB decide failed: {str(e)}"
            )

    @router.post("/act", response_model=ActResponse)
    async def act() -> ActResponse:
        """Execute FAB actions (no-op in Shadow Mode)

        Placeholder for future Phase 2:
        - Write to Atlas memory
        - Update OneBlock cache
        - Trigger E2 encoder

        In Shadow Mode v0.1: returns no-op response.

        Returns:
            Shadow mode status message
        """
        return ActResponse(
            status="shadow_mode",
            message="No external I/O in Shadow Mode v0.1. Future: Atlas writes, cache updates."
        )

    return router
