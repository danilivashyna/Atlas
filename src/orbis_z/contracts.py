"""
Z-Space Data Contracts

Minimal TypedDict definitions for Z-Space slice representation.
Designed for compatibility with existing FAB infrastructure.

Design principles:
- Thin interface (no OneBlock dependency)
- Deterministic (seed-based reproducibility)
- Budget-aware (respects token/node/edge quotas)
- Vec-ready (optional embeddings for MMR Phase 2)
"""

from typing import TypedDict, NotRequired


class ZNode(TypedDict):
    """
    Single node in Z-Space slice.

    Required:
        id: Unique node identifier (str)
        score: Relevance score [0.0, 1.0] for ranking

    Optional (Phase 2):
        vec: Embedding vector for MMR diversity (list[float])
        metadata: Additional node attributes (dict)
    """

    id: str
    score: float
    vec: NotRequired[list[float]]  # Optional: for vec-based MMR (Phase 2)
    metadata: NotRequired[dict]


class ZEdge(TypedDict):
    """
    Edge in Z-Space slice graph.

    Required:
        src: Source node ID
        dst: Destination node ID
        weight: Edge weight/strength [0.0, 1.0]

    Optional:
        rel_type: Relationship type (e.g., "similar", "causal")
    """

    src: str
    dst: str
    weight: float
    rel_type: NotRequired[str]


class ZQuotas(TypedDict):
    """
    Resource quotas for Z-Space slice processing.

    Limits:
        tokens: Maximum token budget for LLM context
        nodes: Maximum nodes to select (stream + global)
        edges: Maximum edges to include
        time_ms: Maximum processing time (milliseconds)
    """

    tokens: int
    nodes: int
    edges: int
    time_ms: int


class ZSliceLite(TypedDict):
    """
    Lightweight Z-Space slice representation.

    Minimal contract for FAB integration without OneBlock dependency.

    Fields:
        nodes: List of candidate nodes (scored, optionally with vecs)
        edges: List of edges between nodes
        quotas: Resource limits for selection
        seed: Deterministic seed for reproducibility
        zv: Z-Space version stamp (e.g., "v0.1.0")

    Example:
        >>> z_slice: ZSliceLite = {
        ...     "nodes": [
        ...         {"id": "n1", "score": 0.95},
        ...         {"id": "n2", "score": 0.87, "vec": [0.1, 0.2, ...]},
        ...     ],
        ...     "edges": [
        ...         {"src": "n1", "dst": "n2", "weight": 0.8}
        ...     ],
        ...     "quotas": {"tokens": 8000, "nodes": 64, "edges": 128, "time_ms": 500},
        ...     "seed": "session-abc-123",
        ...     "zv": "v0.1.0"
        ... }
    """

    nodes: list[ZNode]
    edges: list[ZEdge]
    quotas: ZQuotas
    seed: str
    zv: str  # Z-Space version (e.g., "v0.1.0")


# Type aliases for convenience
ZNodeList = list[ZNode]
ZEdgeList = list[ZEdge]
