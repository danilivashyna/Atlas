from __future__ import annotations

import os
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from atlas.memory import get_node_store
from atlas.metrics.mensum import metrics
from atlas.router.ann_index import get_ann_index, get_query_cache

router = APIRouter(prefix="/router", tags=["Router"])


class BatchRouteItem(BaseModel):
    text: str = Field(min_length=1, max_length=50000)
    top_k: int = 5
    use_ann: bool = True


class BatchRouteRequest(BaseModel):
    items: List[BatchRouteItem]


class BatchRouteResponse(BaseModel):
    results: List[dict]
    trace_id: Optional[str] = None


class IndexUpdateRequest(BaseModel):
    action: str = Field(pattern="^(add|remove|sync)$")
    paths: Optional[List[str]] = None
    backend: Optional[str] = None


@router.post("/route_batch", response_model=BatchRouteResponse)
def route_batch(req: BatchRouteRequest):
    # NOTE: используем кэш эмбеддингов и ANN (если включен)
    backend = os.getenv("ATLAS_ANN_BACKEND", "inproc").lower()
    ann = get_ann_index(backend)
    cache = get_query_cache(
        size=int(os.getenv("ATLAS_QUERY_CACHE_SIZE", "2048")),
        ttl=float(os.getenv("ATLAS_QUERY_CACHE_TTL", "300")),
    )
    store = get_node_store()
    results = []
    for item in req.items:
        # embed cache key — простая хеш-строка
        def _compute():
            # TODO: заменить на реальный encoder → vec5; временно эвристика
            import numpy as np

            # Простая заглушка: случайный 5D вектор
            return np.random.rand(5).tolist()

        vec5, hit = cache.get_or_compute(f"q:{item.text}", _compute)
        if hit:
            metrics.inc_counter("router.qcache_hits")
        else:
            metrics.inc_counter("router.qcache_misses")

        if item.use_ann:
            candidates = ann.search(vec5, item.top_k)
            payload = [{"path": p, "score": float(s)} for p, s in candidates]
        else:
            # fallback: полный перебор из БД
            nodes = store.get_all_nodes()
            payload = []
            import math

            def cos(a, b):
                num = sum(x * y for x, y in zip(a, b))
                na = math.sqrt(sum(x * x for x in a)) or 1e-9
                nb = math.sqrt(sum(y * y for y in b)) or 1e-9
                return num / (na * nb)

            scored = [(n["path"], cos(vec5, n["vec5"])) for n in nodes]
            scored.sort(key=lambda t: t[1], reverse=True)
            payload = [{"path": p, "score": float(s)} for p, s in scored[: item.top_k]]

        results.append({"items": payload})
    return {"results": results}


@router.post("/index/update")
def index_update(req: IndexUpdateRequest):
    backend = (req.backend or os.getenv("ATLAS_ANN_BACKEND", "inproc")).lower()
    ann = get_ann_index(backend)
    store = get_node_store()
    if req.action == "sync":
        items = [(n["path"], n["vec5"]) for n in store.get_all_nodes()]
        size = ann.rebuild(items)
        metrics.set_gauge("ann.index_size", size)
        metrics.inc_counter("ann.rebuilds_total")
        return {"ok": True, "size": size}
    elif req.action == "add":
        nodes = [store.get_node(p) for p in (req.paths or []) if store.get_node(p)]
        added = ann.add_nodes([(n["path"], n["vec5"]) for n in nodes])
        metrics.add_gauge("ann.index_size", added)
        metrics.inc_counter("ann.updates_total", added)
        return {"ok": True, "added": added}
    elif req.action == "remove":
        removed = ann.remove_nodes(req.paths or [])
        metrics.add_gauge("ann.index_size", -removed)
        metrics.inc_counter("ann.removes_total", removed)
        return {"ok": True, "removed": removed}
    return {"ok": False}
