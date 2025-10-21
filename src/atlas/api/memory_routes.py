from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field, PositiveInt, field_validator

# Do NOT import or include app here to avoid circular imports. Export router
# and let src/atlas/api/app.py include it after app creation.
router = APIRouter(tags=["Memory"])

Vec5 = List[float]


class MemoryWriteRequest(BaseModel):
    id: str = Field(min_length=1)
    vector: Vec5
    meta: Optional[dict[str, Any]] = None

    @field_validator("vector")
    @classmethod
    def _check_vector_len(cls, v):
        if not isinstance(v, list) or len(v) != 5:
            raise ValueError("vector must be a list of 5 floats")
        return v


class MemoryWriteResponse(BaseModel):
    ok: bool = True
    trace_id: Optional[str] = None


class MemoryQueryRequest(BaseModel):
    vector: Vec5
    top_k: PositiveInt = 5

    @field_validator("vector")
    @classmethod
    def _check_vector_len(cls, v):
        if not isinstance(v, list) or len(v) != 5:
            raise ValueError("vector must be a list of 5 floats")
        return v


class MemoryQueryResponse(BaseModel):
    items: List[dict]
    trace_id: Optional[str] = None


class MemoryFlushResponse(BaseModel):
    removed: int = Field(..., description="Number of records removed")


class MemoryLoadRequest(BaseModel):
    path: str = Field(..., description="Path to .jsonl file")


class MemoryLoadResponse(BaseModel):
    loaded: int = Field(..., description="Number of records loaded")


class MemoryStatsResponse(BaseModel):
    backend: str = Field(..., description="Backend type (inproc or sqlite)")
    count: int = Field(..., description="Number of records in memory")
    path: Optional[str] = Field(None, description="Database path (for sqlite)")
    size_bytes: Optional[int] = Field(None, description="Database size in bytes")


@router.post("/memory/write", response_model=MemoryWriteResponse, summary="Write vector to memory")
def memory_write(req: MemoryWriteRequest):
    # Lazy import to avoid import-time dependency on atlas.memory package
    from atlas.memory import get_memory

    mem = get_memory()
    mem.write(req.id, list(req.vector), req.meta)
    return {"ok": True}


@router.post(
    "/memory/query", response_model=MemoryQueryResponse, summary="Query similar vectors from memory"
)
def memory_query(req: MemoryQueryRequest):
    from atlas.memory import get_memory

    mem = get_memory()
    items = mem.query(list(req.vector), top_k=int(req.top_k))
    return {"items": items}


@router.post(
    "/memory/flush", response_model=MemoryFlushResponse, summary="Delete all records from memory"
)
def memory_flush():
    from atlas.memory import get_memory

    mem = get_memory()
    removed = mem.flush()
    return {"removed": removed}


@router.post("/memory/load", response_model=MemoryLoadResponse, summary="Bulk load from JSONL file")
def memory_load(req: MemoryLoadRequest):
    from atlas.memory import get_memory

    mem = get_memory()
    loaded = mem.load(req.path)
    return {"loaded": loaded}


@router.get("/memory/stats", response_model=MemoryStatsResponse, summary="Get memory statistics")
def memory_stats():
    from atlas.memory import get_memory

    mem = get_memory()
    stats = mem.stats()
    return MemoryStatsResponse(**stats)
