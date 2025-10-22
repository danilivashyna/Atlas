from __future__ import annotations

import math
import os
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field, PositiveInt

from atlas.memory import get_node_store
from atlas.metrics.mensum import metrics

router = APIRouter(prefix="/reticulum", tags=["Reticulum"])


class LinkVersionRequest(BaseModel):
    path: str = Field(min_length=1)
    content_id: str = Field(min_length=1)
    version: PositiveInt = 1
    score: float = Field(ge=0.0, le=1.0, default=0.0)
    kind: str = "doc"
    meta: Optional[Dict[str, Any]] = None


@router.post("/link_version")
def link_version(req: LinkVersionRequest):
    store = get_node_store()
    store.write_link_version(
        node_path=req.path,
        content_id=req.content_id,
        version=int(req.version),
        score=float(req.score),
        kind=req.kind,
        meta=req.meta,
    )
    metrics.inc_counter("reticulum.versioned_links_total")
    return {"ok": True}


class ResolveQuery(BaseModel):
    content_id: str
    top_k: int = 5
    with_history: bool = False


@router.post("/resolve")
def resolve(req: ResolveQuery):
    store = get_node_store()
    rows = store.resolve_latest(req.content_id, top_k=int(req.top_k))
    metrics.inc_counter("reticulum.resolve_requests_total")
    return {
        "items": rows,
        "history": store.get_link_versions(req.content_id) if req.with_history else None,
    }


class RecencyQuery(BaseModel):
    path_prefix: Optional[str] = None
    top_k: int = 10


@router.post("/recent")
def recent(req: RecencyQuery):
    store = get_node_store()
    lam = float(os.getenv("ATLAS_RECENCY_LAMBDA", "0.05"))
    items = store.query_link_versions(req.path_prefix, req.top_k * 5)  # брать с запасом
    now = time.time()
    scored = []
    for it in items:
        ts = it.get("created_at_ts") or now  # если есть
        age_days = max(0.0, (now - ts) / 86400.0)
        eff = it["score"] * math.exp(-lam * age_days)
        scored.append((eff, it))
    scored.sort(key=lambda t: t[0], reverse=True)
    return {"items": [x[1] for x in scored[: req.top_k]]}
