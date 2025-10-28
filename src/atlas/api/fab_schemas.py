"""
FAB Context Window Schemas (v0.1)

JSON Schema for FAB windows as specified in AURIS_FAB_Integration_Plan_v0.1.txt

Window Types:
    - Global (FABᴳ): System-wide z-space, immutable per step
    - Stream (FABˢ): Per-flow localized context, refresh on step change

Schema Structure:
    {
      "fab_version": "0.1",
      "window": {"type": "global|stream", "id": "UUID", "ts": "ISO8601"},
      "tokens": [{"t":"str", "w":0.0, "role":"system|user|agent"}],
      "vectors": [{"id":"node|edge|doc", "dim":384, "norm":1.0, "ts":"ISO8601"}],
      "links": [{"src":"id", "dst":"id", "w":0.0, "kind":"semantic|temporal|causal"}],
      "meta": {"topic":"str", "locale":"str", "coherence":0.0, "stability":0.0}
    }
"""

from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class WindowType(str, Enum):
    """FAB window type: global (system-wide) or stream (per-flow)."""

    GLOBAL = "global"
    STREAM = "stream"


class TokenRole(str, Enum):
    """Token role in FAB context."""

    SYSTEM = "system"
    USER = "user"
    AGENT = "agent"


class LinkKind(str, Enum):
    """Link type between FAB nodes."""

    SEMANTIC = "semantic"
    TEMPORAL = "temporal"
    CAUSAL = "causal"


class FABWindow(BaseModel):
    """FAB window metadata."""

    type: WindowType = Field(..., description="Window type (global or stream)")
    id: UUID = Field(..., description="Unique window identifier")
    ts: datetime = Field(..., description="Window creation timestamp (ISO8601)")


class FABToken(BaseModel):
    """Token in FAB context window."""

    t: str = Field(..., min_length=1, max_length=1000, description="Token text")
    w: float = Field(0.0, ge=0.0, le=1.0, description="Token weight (0.0-1.0)")
    role: TokenRole = Field(TokenRole.USER, description="Token role")


class FABVector(BaseModel):
    """Vector in FAB context window."""

    id: str = Field(..., min_length=1, max_length=256, description="Vector ID (node|edge|doc)")
    dim: int = Field(384, ge=1, le=4096, description="Vector dimensionality")
    norm: float = Field(1.0, ge=0.0, description="Vector norm (L2)")
    ts: datetime = Field(..., description="Vector timestamp (ISO8601)")

    @field_validator("dim")
    @classmethod
    def validate_dim(cls, v: int) -> int:
        """Validate vector dimension is power of 2 or standard size."""
        standard_dims = {128, 256, 384, 512, 768, 1024, 1536, 2048, 4096}
        if v not in standard_dims:
            raise ValueError(f"dim must be one of {standard_dims}, got {v}")
        return v


class FABLink(BaseModel):
    """Link between FAB vectors."""

    src: str = Field(..., min_length=1, max_length=256, description="Source vector ID")
    dst: str = Field(..., min_length=1, max_length=256, description="Destination vector ID")
    w: float = Field(0.0, ge=0.0, le=1.0, description="Link weight (0.0-1.0)")
    kind: LinkKind = Field(LinkKind.SEMANTIC, description="Link type")


class FABMeta(BaseModel):
    """FAB window metadata (E3 metrics + context)."""

    topic: str = ""
    locale: str = "en-US"
    coherence: float = 0.0
    stability: float = 0.0


class FABContext(BaseModel):
    """
    FAB Context Window (v0.1).

    Complete schema for FAB global/stream windows as specified in
    AURIS_FAB_Integration_Plan_v0.1.txt
    """

    fab_version: Literal["0.1"] = Field("0.1", description="FAB schema version")
    window: FABWindow = Field(..., description="Window metadata")
    tokens: list[FABToken] = Field(default_factory=list, description="Tokens in window")
    vectors: list[FABVector] = Field(default_factory=list, description="Vectors in window")
    links: list[FABLink] = Field(default_factory=list, description="Links between vectors")
    meta: FABMeta = Field(default_factory=lambda: FABMeta(), description="Window metadata + E3 metrics")

    @field_validator("tokens")
    @classmethod
    def validate_tokens_count(cls, v: list[FABToken]) -> list[FABToken]:
        """Validate token count (max 10k for backpressure)."""
        if len(v) > 10_000:
            raise ValueError(f"tokens count exceeds limit (10k), got {len(v)}")
        return v

    @field_validator("vectors")
    @classmethod
    def validate_vectors_count(cls, v: list[FABVector]) -> list[FABVector]:
        """Validate vector count (max 100k for memory limits)."""
        if len(v) > 100_000:
            raise ValueError(f"vectors count exceeds limit (100k), got {len(v)}")
        return v


class FABPushRequest(BaseModel):
    """Request schema for POST /api/v1/fab/context/push."""

    context: FABContext = Field(..., description="FAB context window")
    run_id: Optional[str] = Field(None, max_length=128, description="Idempotency key")
    dry_run: bool = Field(True, description="Dry-run mode (default: true for safety)")


class BackpressureStatus(str, Enum):
    """Backpressure status from FAB."""

    OK = "ok"  # Accepting requests normally
    SLOW = "slow"  # Slow down, approaching limits
    REJECT = "reject"  # Rejecting new requests, retry later


class FABPushResponse(BaseModel):
    """Response schema for POST /api/v1/fab/context/push."""

    accepted: bool = Field(..., description="Whether context was accepted")
    backpressure: BackpressureStatus = Field(..., description="Backpressure status")
    reasons: list[str] = Field(default_factory=list, description="Rejection reasons (if any)")
    ids: list[str] = Field(default_factory=list, description="IDs of indexed vectors")
    run_id: Optional[str] = Field(None, description="Echo of request run_id")


class FABPullRequest(BaseModel):
    """Request schema for GET /api/v1/fab/context/pull."""

    window_type: WindowType = Field(..., description="Window type to pull")
    window_id: UUID = Field(..., description="Window ID")


class FABPullResponse(BaseModel):
    """Response schema for GET /api/v1/fab/context/pull."""

    context: FABContext = Field(..., description="Merged FAB context (E2 + overlays)")
    cached: bool = Field(..., description="Whether context was cached")


class FABDecideRequest(BaseModel):
    """Request schema for POST /api/v1/fab/decide."""

    metrics: dict = Field(..., description="E3 metrics (h_coherence, h_stability)")
    policies: Optional[list[str]] = Field(None, description="Policy overrides (E4.1)")
    run_id: Optional[str] = Field(None, max_length=128, description="Idempotency key")


class FABDecideResponse(BaseModel):
    """Response schema for POST /api/v1/fab/decide."""

    decisions: list[dict] = Field(..., description="Proposed actions from E4.2")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Decision confidence")
    run_id: Optional[str] = Field(None, description="Echo of request run_id")


class FABActRequest(BaseModel):
    """Request schema for POST /api/v1/fab/act/{action_type}."""

    params: dict = Field(default_factory=dict, description="Action parameters")
    run_id: Optional[str] = Field(None, max_length=128, description="Idempotency key")
    dry_run: bool = Field(True, description="Dry-run mode (default: true for safety)")


class FABActResponse(BaseModel):
    """Response schema for POST /api/v1/fab/act/{action_type}."""

    action_type: str = Field(..., description="Action type executed")
    status: str = Field(..., description="Execution status (dry_run, success, failed)")
    message: str = Field(..., description="Human-readable message")
    details: dict = Field(default_factory=dict, description="Execution details")
    run_id: Optional[str] = Field(None, description="Echo of request run_id")
