"""
FastAPI routes for router batch operations and ANN index management.

Endpoints:
  POST /router/route_batch — Batch routing queries
  POST /router/index/rebuild — Rebuild ANN index
"""

import logging
import os
import uuid
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(tags=["Router"])
logger = logging.getLogger(__name__)


# ----- Request/Response Models -----


class RouteBatchItem(BaseModel):
    """Single item in batch route request."""

    text: str = Field(..., min_length=1, description="Input text")
    top_k: int = Field(default=3, ge=1, le=50, description="Number of top nodes")


class RouteBatchRequest(BaseModel):
    """Batch routing request."""

    items: List[RouteBatchItem] = Field(..., min_length=1, max_length=100)
    use_ann: bool = Field(default=True, description="Use ANN for candidate selection")
    rebuild_index: bool = Field(default=False, description="Rebuild ANN index before routing")


class PathScoreItem(BaseModel):
    """Scored path in routing result."""

    path: str
    score: float
    label: Optional[str] = None
    meta: Optional[dict] = None


class RouteBatchResultItem(BaseModel):
    """Single result in batch response."""

    items: List[PathScoreItem]


class RouteBatchResponse(BaseModel):
    """Response for batch routing."""

    results: List[RouteBatchResultItem]
    trace_id: Optional[str] = None


class IndexRebuildRequest(BaseModel):
    """Request to rebuild ANN index."""

    backend: str = Field(default="inproc", description="ANN backend: inproc | faiss | off")


class IndexRebuildResponse(BaseModel):
    """Response from index rebuild."""

    ok: bool
    count: int = Field(0, description="Number of nodes indexed")
    backend: str = Field(default="inproc")
    trace_id: Optional[str] = None


# ----- Endpoints -----


@router.post("/router/route_batch", response_model=RouteBatchResponse)
def router_route_batch(req: RouteBatchRequest):
    """Route multiple texts in batch. Optionally rebuild ANN index first."""
    trace_id = str(uuid.uuid4())[:8]

    try:
        from atlas import SemanticSpace
        from atlas.memory import get_node_store
        from atlas.router import PathRouter

        # Lazy import ANN
        from atlas.router.ann_index import get_ann_index

        # Get singletons
        space = SemanticSpace()
        node_store = get_node_store()

        # Create router instance
        router_instance = PathRouter(space, node_store)

        # Optionally rebuild ANN index
        if req.rebuild_index:
            ann_backend = os.getenv("ATLAS_ANN_BACKEND", "inproc")
            if ann_backend != "off":
                ann_index = get_ann_index(ann_backend)
                nodes = node_store.get_all_nodes()
                ann_index.build(nodes)
                router_instance.ann_index = ann_index
                logger.info(
                    f"ANN index rebuilt: {ann_index.index_size} nodes "
                    f"(backend={ann_backend}, trace_id={trace_id})"
                )

        # Process batch
        results = []
        for item in req.items:
            path_scores = router_instance.route(item.text, top_k=item.top_k, use_ann=req.use_ann)
            result_items = [
                PathScoreItem(
                    path=ps.path,
                    score=ps.score,
                    label=ps.label,
                    meta=ps.meta,
                )
                for ps in path_scores
            ]
            results.append(RouteBatchResultItem(items=result_items))

        logger.info(f"Batch routed: {len(req.items)} queries (trace_id={trace_id})")
        return {"results": results, "trace_id": trace_id}

    except Exception as e:
        logger.error(f"Batch routing failed: {e} (trace_id={trace_id})")
        # Return empty results for each item
        results = [RouteBatchResultItem(items=[]) for _ in req.items]
        return {"results": results, "trace_id": trace_id}


@router.post("/router/index/rebuild", response_model=IndexRebuildResponse)
def router_index_rebuild(req: IndexRebuildRequest):
    """Rebuild ANN index from current nodes."""
    trace_id = str(uuid.uuid4())[:8]

    try:
        from atlas.memory import get_node_store
        from atlas.router.ann_index import get_ann_index

        node_store = get_node_store()

        # Get ANN backend
        ann_backend = req.backend
        if ann_backend == "off":
            logger.info(f"ANN disabled (backend=off, trace_id={trace_id})")
            return {"ok": True, "count": 0, "backend": "off", "trace_id": trace_id}

        # Get nodes
        nodes = node_store.get_all_nodes()
        if not nodes:
            logger.warning(f"No nodes to index (trace_id={trace_id})")
            return {"ok": True, "count": 0, "backend": ann_backend, "trace_id": trace_id}

        # Build index
        ann_index = get_ann_index(ann_backend)
        if ann_index is None:
            logger.error(f"Failed to create ANN index (backend={ann_backend}, trace_id={trace_id})")
            return {"ok": False, "count": 0, "backend": ann_backend, "trace_id": trace_id}

        ann_index.build(nodes)

        # Save index to disk
        index_path = os.getenv("ATLAS_ANN_INDEX_PATH", "/tmp/atlas_nodes.faiss")
        try:
            ann_index.save(index_path)
            logger.info(f"ANN index saved to {index_path}")
        except Exception as e:
            logger.warning(f"Failed to save ANN index: {e}")

        logger.info(
            f"ANN index rebuilt: {ann_index.index_size} nodes "
            f"(backend={ann_backend}, trace_id={trace_id})"
        )
        return {
            "ok": True,
            "count": ann_index.index_size,
            "backend": ann_backend,
            "trace_id": trace_id,
        }

    except Exception as e:
        logger.error(f"Index rebuild failed: {e} (trace_id={trace_id})")
        return {"ok": False, "count": 0, "backend": req.backend, "trace_id": trace_id}
