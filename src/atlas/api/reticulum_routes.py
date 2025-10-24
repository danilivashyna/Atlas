from __future__ import annotations

import logging
import math
import os
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field, PositiveInt

from atlas.memory import get_node_store
from atlas.metrics.mensum import metrics_ns

router = APIRouter(prefix="/reticulum", tags=["Reticulum"])
logger = logging.getLogger(__name__)


# ----- Request/Response Models -----


class LinkVersionRequest(BaseModel):
    node_path: str = Field(min_length=1)
    content_id: str = Field(min_length=1)
    version: PositiveInt = 1
    score: float = Field(ge=0.0, le=1.0, default=0.0)
    kind: str = "doc"
    meta: Optional[Dict[str, Any]] = None


class LinkVersionResponse(BaseModel):
    ok: bool = True


class ResolveRequest(BaseModel):
    content_id: str
    top_k: int = 10


class LinkRecord(BaseModel):
    node_path: str
    content_id: str
    version: int
    score: float
    kind: Optional[str] = None
    meta: Optional[dict] = None
    created_at_ts: float


class ResolveResponse(BaseModel):
    items: List[LinkRecord]
    history: Optional[List[LinkRecord]] = None


class RecencyQuery(BaseModel):
    path_prefix: Optional[str] = None
    top_k: int = 10
    lambda_per_day: float = 0.1


class RecentLinksResponse(BaseModel):
    items: List[LinkRecord]


class NeighborItem(BaseModel):
    content_id: str
    effective_score: float


class NeighborsResponse(BaseModel):
    items: List[NeighborItem]


class BackrefTouchRequest(BaseModel):
    content_id: str = Field(min_length=1)
    node_path: str = Field(min_length=1)


class BackrefTouchResponse(BaseModel):
    ok: bool = True


class BackrefRecord(BaseModel):
    node_path: str
    hit_count: int
    last_seen_at: float


class TopBackrefsResponse(BaseModel):
    items: List[BackrefRecord]


# ----- Routes -----


@router.post("/link_version", response_model=LinkVersionResponse)
def write_link_version(req: LinkVersionRequest) -> LinkVersionResponse:
    """Write a versioned link from node to content."""
    try:
        store = get_node_store()
        store.write_link_version(
            node_path=req.node_path,
            content_id=req.content_id,
            version=int(req.version),
            score=float(req.score),
            kind=req.kind,
            meta=req.meta,
        )
        logger.debug(
            f"Link written: {req.node_path} -> {req.content_id} v{req.version} (score={req.score})"
        )
        return LinkVersionResponse(ok=True)
    except Exception as e:
        logger.error(f"Failed to write link: {e}")
        return LinkVersionResponse(ok=False)


@router.post("/resolve", response_model=ResolveResponse)
def resolve_latest(req: ResolveRequest) -> ResolveResponse:
    """Resolve latest versions of a content across nodes."""
    try:
        store = get_node_store()
        items = store.resolve_latest(req.content_id, req.top_k)
        metrics_ns().inc_counter("reticulum_resolve_requests")
        logger.debug(f"Resolved {len(items)} versions for content {req.content_id}")
        return ResolveResponse(items=items)
    except Exception as e:
        logger.error(f"Failed to resolve content: {e}")
        return ResolveResponse(items=[])


@router.post("/recent", response_model=RecentLinksResponse)
def query_recent_links(req: RecencyQuery) -> RecentLinksResponse:
    """Query recent links with recency decay weighting."""
    try:
        import time as time_module

        start = time_module.time()

        store = get_node_store()

        # Record query metric
        metrics_ns().inc_counter(
            "reticulum_recent_queries",
            labels={"has_prefix": "yes" if req.path_prefix else "no"},
        )

        # Query with recency
        results = store.recent_links(
            lambda_per_day=req.lambda_per_day, top_k=req.top_k, path_prefix=req.path_prefix
        )

        items = [
            LinkRecord(
                node_path=r["node_path"],
                content_id=r["content_id"],
                version=r["version"],
                score=r["score"],
                kind=r["kind"],
                meta=r["meta"],
                created_at_ts=r["created_at_ts"],
            )
            for r in results
        ]

        # Record timing metric
        elapsed_ms = (time_module.time() - start) * 1000
        metrics_ns().observe_hist("reticulum_recent_latency_ms", elapsed_ms)

        logger.debug(
            f"Recent query returned {len(items)} items (lambda={req.lambda_per_day}, {elapsed_ms:.1f}ms)"
        )
        return RecentLinksResponse(items=items)

    except Exception as e:
        logger.error(f"Failed to query recent links: {e}")
        return RecentLinksResponse(items=[])


@router.get("/node/{path}/neighbors", response_model=NeighborsResponse)
def get_neighbors(path: str, top_k: int = 20, lambda_per_day: float = 0.1) -> NeighborsResponse:
    """Get neighbor content from a node with recency decay."""
    try:
        store = get_node_store()
        metrics_ns().inc_counter("reticulum_neighbors_queries")

        neighbor_ids = store.neighbors_from_node(
            node_path=path, top_k=top_k, lambda_per_day=lambda_per_day
        )

        # For response, compute effective scores
        now = time.time()
        items = []

        if store.conn:
            cursor = store.conn.cursor()
            for content_id in neighbor_ids:
                cursor.execute(
                    """
                    SELECT MAX(score) as max_score, MAX(strftime('%s', created_at)) as created_at
                    FROM link_versions
                    WHERE node_path = ? AND content_id = ?
                """,
                    (path, content_id),
                )
                row = cursor.fetchone()
                if row:
                    score, created_at_ts = row
                    ts = float(created_at_ts) if created_at_ts else now
                    age_days = max(0.0, (now - ts) / 86400.0)
                    eff = score * math.exp(-lambda_per_day * age_days)
                    items.append(NeighborItem(content_id=content_id, effective_score=eff))

        logger.debug(f"Neighbors for {path}: {len(items)} items")
        return NeighborsResponse(items=items)

    except Exception as e:
        logger.error(f"Failed to get neighbors for {path}: {e}")
        return NeighborsResponse(items=[])


@router.post("/backref/touch", response_model=BackrefTouchResponse)
def touch_backref(req: BackrefTouchRequest) -> BackrefTouchResponse:
    """Record or increment a backward reference."""
    try:
        store = get_node_store()
        store.backref_touch(content_id=req.content_id, node_path=req.node_path)
        logger.debug(f"Backref touched: {req.content_id} <- {req.node_path}")
        return BackrefTouchResponse(ok=True)
    except Exception as e:
        logger.error(f"Failed to touch backref: {e}")
        return BackrefTouchResponse(ok=False)


@router.get("/backref/top/{content_id}", response_model=TopBackrefsResponse)
def get_top_backrefs(content_id: str, top_k: int = 20) -> TopBackrefsResponse:
    """Get top nodes (most popular destinations) for a content."""
    try:
        store = get_node_store()
        backrefs = store.top_backrefs(content_id=content_id, top_k=top_k)

        items = [
            BackrefRecord(
                node_path=br["node_path"],
                hit_count=br["hit_count"],
                last_seen_at=br["last_seen_at"],
            )
            for br in backrefs
        ]

        logger.debug(f"Top backrefs for {content_id}: {len(items)} nodes")
        return TopBackrefsResponse(items=items)

    except Exception as e:
        logger.error(f"Failed to get top backrefs for {content_id}: {e}")
        return TopBackrefsResponse(items=[])
