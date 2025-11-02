"""
Atlas β API Schemas (Pydantic models)

All request/response models for REST API, generated from configs/api/schemas.json.
Single source of truth: JSON Schema → Pydantic validation.

Version: 0.2.0-beta
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ==================== /encode endpoint ====================

class EncodeRequest(BaseModel):
    """Request body for /encode endpoint (5D semantic encoding)."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=100000,
        description="Text to encode into 5D space"
    )
    lang: Literal["ru", "en", "de", "fr", "es"] = Field(
        default="ru",
        description="Language code"
    )
    normalize: bool = Field(
        default=True,
        description="L2-normalize the output embedding"
    )

    class Config:
        extra = "forbid"  # additionalProperties: false


class EncodeMeta(BaseModel):
    """Metadata for encoding operation."""

    len: int = Field(..., description="Input text length")
    lang: str = Field(..., description="Detected/used language")
    normalized: bool = Field(..., description="Whether L2-normalized")


class EncodeResponse(BaseModel):
    """Response body for /encode endpoint."""

    embedding_5d: List[float] = Field(
        ...,
        min_length=5,
        max_length=5,
        description="5D semantic vector (normalized)"
    )
    dimensions: List[str] = Field(
        default=["A", "B", "C", "D", "E"],
        min_length=5,
        max_length=5,
        description="Dimension names (A, B, C, D, E)"
    )
    meta: EncodeMeta

    class Config:
        extra = "forbid"


# ==================== /decode endpoint ====================

class DecodeRequest(BaseModel):
    """Request body for /decode endpoint (5D → text reconstruction)."""

    embedding_5d: List[float] = Field(
        ...,
        min_length=5,
        max_length=5,
        description="5D semantic vector to decode"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Top-k reconstructions to return"
    )

    class Config:
        extra = "forbid"


class DecodeResponse(BaseModel):
    """Response body for /decode endpoint."""

    text: str = Field(..., description="Reconstructed text (best match)")
    rationale: List[str] = Field(
        ...,
        description="Per-dimension explanations (e.g., 'dimA↑ => abstraction')"
    )
    path: List[str] = Field(
        ...,
        description="Hierarchical path in semantic space"
    )

    class Config:
        extra = "forbid"


# ==================== /explain endpoint ====================

class ExplainRequest(BaseModel):
    """Request body for /explain endpoint (5D vector interpretation)."""

    embedding_5d: List[float] = Field(
        ...,
        min_length=5,
        max_length=5,
        description="5D vector to explain"
    )

    class Config:
        extra = "forbid"


class DimensionExplanation(BaseModel):
    """Explanation for a single dimension."""

    name: str = Field(..., description="Dimension name (A-E)")
    weight: float = Field(..., ge=0.0, le=1.0, description="Normalized weight")
    examples: List[str] = Field(..., description="Example concepts for this dimension")


class ExplainResponse(BaseModel):
    """Response body for /explain endpoint."""

    dimensions: List[DimensionExplanation] = Field(
        ...,
        min_length=5,
        max_length=5,
        description="Per-dimension interpretations"
    )
    normalization: Literal["L2", "L1", "none"] = Field(
        ...,
        description="Normalization method applied"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional interpretation notes"
    )

    class Config:
        extra = "forbid"


# ==================== /encode_h endpoint ====================

class EncodeHierarchicalRequest(BaseModel):
    """Request body for /encode_h endpoint (hierarchical multi-level encoding)."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=1000000,
        description="Full text to encode hierarchically"
    )
    levels: List[Literal["token", "sentence", "paragraph", "document"]] = Field(
        default=["sentence", "paragraph", "document"],
        description="Hierarchical levels to encode"
    )
    proj_dim: int = Field(
        default=384,
        ge=128,
        le=768,
        description="Projection dimension for intermediate levels"
    )
    normalize: bool = Field(
        default=True,
        description="L2-normalize all outputs"
    )

    class Config:
        extra = "forbid"


class EncodeHierarchicalResponse(BaseModel):
    """Response body for /encode_h endpoint."""

    levels: Dict[str, List[List[float]]] = Field(
        ...,
        description="Per-level embeddings (arrays of vectors)"
    )
    masks: Dict[str, List[List[int]]] = Field(
        ...,
        description="Hierarchical masks (token->sent->para->doc)"
    )

    class Config:
        extra = "forbid"

    @field_validator("masks")
    @classmethod
    def validate_masks(cls, v: Dict[str, List[List[int]]]) -> Dict[str, List[List[int]]]:
        """Ensure masks contain only 0/1 values."""
        for level, mask_lists in v.items():
            for mask in mask_lists:
                if not all(val in (0, 1) for val in mask):
                    raise ValueError(f"Mask for level '{level}' contains non-binary values")
        return v


# ==================== /search endpoint ====================

class SearchRequest(BaseModel):
    """Request body for /search endpoint (multi-level semantic search)."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=100000,
        description="Search query text"
    )
    levels: List[Literal["sentence", "paragraph", "document"]] = Field(
        default=["sentence", "paragraph", "document"],
        description="Levels to search across"
    )
    top_k: int = Field(
        default=7,
        ge=1,
        le=1000,
        description="Top-k results per level"
    )
    fuse: Literal["RRF", "max_sim"] = Field(
        default="RRF",
        description="Fusion method: RRF (Reciprocal Rank Fusion) or max similarity"
    )

    class Config:
        extra = "forbid"


class SearchHit(BaseModel):
    """Single search result hit."""

    level: Literal["sentence", "paragraph", "document"] = Field(
        ...,
        description="Hierarchical level"
    )
    id: str = Field(
        ...,
        description="Hierarchical ID (e.g., 's:123', 'p:45', 'd:1')"
    )
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fused score"
    )
    trace: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Debug trace (ranks, similarities, etc.)"
    )


class SearchDebug(BaseModel):
    """Debug information for search operation."""

    per_level: Optional[Dict[str, List[float]]] = Field(
        default=None,
        description="Per-level scores before fusion"
    )
    fuse_weights: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Fusion parameters (e.g., RRF_k=60)"
    )


class SearchResponse(BaseModel):
    """Response body for /search endpoint."""

    hits: List[SearchHit] = Field(..., description="Ranked results after fusion")
    debug: Optional[SearchDebug] = Field(default=None, description="Debug information")
    query_time_ms: Optional[float] = Field(default=None, description="Total query time")

    class Config:
        extra = "forbid"


# ==================== /health endpoint ====================

class HealthResponse(BaseModel):
    """Response body for /health endpoint."""

    status: Literal["healthy"] = Field(..., description="Health status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(..., description="Current server timestamp")

    class Config:
        extra = "forbid"


# ==================== /ready endpoint ====================

class ReadyChecks(BaseModel):
    """Readiness check results."""

    indices_loaded: bool = Field(..., description="HNSW/FAISS indices loaded")
    manifest_valid: bool = Field(..., description="MANIFEST integrity verified")
    memory_available: bool = Field(..., description="Sufficient memory available")


class ReadyResponse(BaseModel):
    """Response body for /ready endpoint."""

    ready: bool = Field(..., description="All checks passed")
    checks: ReadyChecks = Field(..., description="Individual check results")

    class Config:
        extra = "forbid"


# ==================== Error responses ====================

class ErrorResponse(BaseModel):
    """Generic error response body."""

    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable message")
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )
    trace_id: Optional[str] = Field(default=None, description="Request trace ID")
    timestamp: datetime = Field(..., description="Error timestamp")

    class Config:
        extra = "forbid"
