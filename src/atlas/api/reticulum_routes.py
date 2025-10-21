"""
FastAPI routes for Reticulum: content links and mini-RAG.

Endpoints:
  POST /reticulum/link — Link content to a node
  POST /reticulum/query — Query linked content by path (with subtree support)
"""

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(tags=["Reticulum"])
logger = logging.getLogger(__name__)


# ----- Request/Response Models -----


class LinkContentRequest(BaseModel):
    """Link content to a node."""

    path: str = Field(..., min_length=1, description="Node path")
    content_id: str = Field(..., min_length=1, description="External content ID")
    kind: str = Field(default="doc", description="Content kind: doc | snippet | url")
    score: float = Field(default=0.0, ge=0.0, le=1.0, description="Relevance score")
    meta: Optional[dict] = Field(default=None, description="Metadata (title, url, tags)")


class LinkContentResponse(BaseModel):
    """Response for link creation."""

    ok: bool = True
    trace_id: Optional[str] = None


class LinkedContentItem(BaseModel):
    """Linked content entry."""

    content_id: str
    kind: str
    score: float
    meta: Optional[dict] = None


class QueryLinksRequest(BaseModel):
    """Query linked content."""

    path: Optional[str] = Field(default=None, description="Node path (or prefix for subtree)")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results")


class QueryLinksResponse(BaseModel):
    """Response for link query."""

    items: List[LinkedContentItem]
    trace_id: Optional[str] = None


# ----- Endpoints -----


@router.post("/reticulum/link", response_model=LinkContentResponse)
def reticulum_link(req: LinkContentRequest):
    """Link content to a node."""
    trace_id = str(uuid.uuid4())[:8]

    try:
        # Lazy import to avoid circular dependencies
        from atlas.memory import get_node_store

        node_store = get_node_store()

        # Write link
        node_store.write_link(
            node_path=req.path,
            content_id=req.content_id,
            kind=req.kind,
            score=req.score,
            meta=req.meta,
        )

        logger.info(f"Link created: {req.path} -> {req.content_id} (trace_id={trace_id})")
        return {"ok": True, "trace_id": trace_id}

    except Exception as e:
        logger.error(f"Link creation failed: {e} (trace_id={trace_id})")
        return {"ok": False, "trace_id": trace_id}


@router.post("/reticulum/query", response_model=QueryLinksResponse)
def reticulum_query(req: QueryLinksRequest):
    """Query linked content by node path (supports subtree search)."""
    trace_id = str(uuid.uuid4())[:8]

    try:
        # Lazy import
        from atlas.memory import get_node_store

        node_store = get_node_store()

        # Query links
        links = node_store.query_links(path_prefix=req.path, top_k=req.top_k)

        # Transform to response format
        items = [
            LinkedContentItem(
                content_id=link["content_id"],
                kind=link["kind"],
                score=link["score"],
                meta=link["meta"],
            )
            for link in links
        ]

        logger.info(f"Links queried: path={req.path}, results={len(items)} (trace_id={trace_id})")
        return {"items": items, "trace_id": trace_id}

    except Exception as e:
        logger.error(f"Link query failed: {e} (trace_id={trace_id})")
        return {"items": [], "trace_id": trace_id}
