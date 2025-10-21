"""
FastAPI routes for path-aware routing with hierarchical memory.

Endpoints:
  POST /router/route — Route text to top-k hierarchical nodes
  POST /router/activate — Soft-activate children of a node
"""

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(tags=["Router"])
logger = logging.getLogger(__name__)


# ----- Request/Response Models -----


class RouterRouteRequest(BaseModel):
    """Route a text to hierarchical nodes."""

    text: str = Field(..., min_length=1, description="Input text to route")
    top_k: int = Field(default=3, ge=1, le=50, description="Number of top nodes")


class PathScoreItem(BaseModel):
    """Scored path in routing result."""

    path: str
    score: float
    label: Optional[str] = None
    meta: Optional[dict] = None


class RouterRouteResponse(BaseModel):
    """Routing result."""

    items: List[PathScoreItem]
    trace_id: Optional[str] = None


class RouterActivateRequest(BaseModel):
    """Activate children of a node."""

    path: str = Field(..., min_length=1, description="Parent node path")
    text: str = Field(..., min_length=1, description="Input text for scoring")


class ChildActivationItem(BaseModel):
    """Soft-activated child."""

    path: str
    p: float = Field(..., description="Probability (softmax result)")


class RouterActivateResponse(BaseModel):
    """Child activation result."""

    children: List[ChildActivationItem]
    trace_id: Optional[str] = None


# ----- Routes -----


@router.post("/router/route", response_model=RouterRouteResponse)
def router_route(req: RouterRouteRequest):
    """Route text to top-k nodes via 5D encoding + hierarchical scoring."""
    trace_id = str(uuid.uuid4())[:8]

    try:
        # Check if router is disabled
        import os

        if os.getenv("ATLAS_ROUTER_MODE", "on").lower() == "off":
            logger.info(f"Router disabled (trace_id={trace_id})")
            return {"items": [], "trace_id": trace_id}

        # Lazy import to avoid circular dependencies
        from atlas import SemanticSpace
        from atlas.memory import get_node_store
        from atlas.router import PathRouter

        # Get singletons
        space = SemanticSpace()
        node_store = get_node_store()

        # Create router with env parameters
        router_instance = PathRouter(space, node_store)

        # Route text
        results = router_instance.route(req.text, top_k=req.top_k)

        items = [
            PathScoreItem(path=r.path, score=r.score, label=r.label, meta=r.meta) for r in results
        ]

        logger.info(f"Route: {len(items)} nodes returned (trace_id={trace_id})")
        return {"items": items, "trace_id": trace_id}

    except Exception as e:
        logger.error(f"router_route failed (trace_id={trace_id}): {e}")
        return {"items": [], "trace_id": trace_id}


@router.post("/router/activate", response_model=RouterActivateResponse)
def router_activate(req: RouterActivateRequest):
    """Soft-activate children of a node via softmax."""
    trace_id = str(uuid.uuid4())[:8]

    try:
        # Check if router is disabled
        import os

        if os.getenv("ATLAS_ROUTER_MODE", "on").lower() == "off":
            logger.info(f"Router disabled (trace_id={trace_id})")
            return {"children": [], "trace_id": trace_id}

        # Lazy import
        from atlas import SemanticSpace
        from atlas.memory import get_node_store
        from atlas.router import PathRouter

        # Get singletons
        space = SemanticSpace()
        node_store = get_node_store()

        # Create router
        router_instance = PathRouter(space, node_store)

        # Activate children
        results = router_instance.activate_child(req.path, req.text)

        children = [ChildActivationItem(path=r.path, p=r.p) for r in results]

        logger.info(f"Activate {req.path}: {len(children)} children (trace_id={trace_id})")
        return {"children": children, "trace_id": trace_id}

    except Exception as e:
        logger.error(f"router_activate failed (trace_id={trace_id}): {e}")
        return {"children": [], "trace_id": trace_id}
