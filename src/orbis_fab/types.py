"""FAB Type Definitions - Phase A MVP

Fundamental types for FAB state machine:
- FabMode: FAB0 (no SELF) / FAB1 (SELF present) / FAB2 (SELF + Ego)
- Budgets: Fixed capacity per tick (tokens/nodes/edges/time)
- ZSliceLite: Minimal Z-space slice (nodes/edges without Atlas dependency)
- Metrics: Stress/self_presence/error_rate for state transitions

Invariants:
- Budgets fixed per tick (immutable during tick)
- ZSliceLite contains only IDs and scores (no embedding data)
- Metrics drive FAB0→FAB1→FAB2 transitions
"""

from enum import Enum
from typing import TypedDict, Literal, Sequence, NotRequired


# FAB State Machine Modes
FabMode = Literal["FAB0", "FAB1", "FAB2"]


class Budgets(TypedDict):
    """Fixed capacity per tick (immutable during tick execution)"""
    tokens: int      # Max tokens in context (default: 4096)
    nodes: int       # Max nodes across windows (default: 256)
    edges: int       # Max edges in Z-slice (default: 0 for Phase A)
    time_ms: int     # Max tick duration (default: 30ms)


class ZNode(TypedDict):
    """Minimal node representation from Z-space"""
    id: str          # Node identifier
    score: float     # Relevance score [0.0, 1.0]
    vec: NotRequired[list[float]]  # Optional: embedding for vec-based MMR (Phase 2)


class ZEdge(TypedDict):
    """Minimal edge representation from Z-space"""
    src: str         # Source node ID
    dst: str         # Destination node ID
    w: float         # Edge weight [0.0, 1.0]
    kind: str        # Edge type (semantic/episodic/etc)


class ZSliceLite(TypedDict):
    """Lightweight Z-space slice (no Atlas dependency)
    
    Used by FAB.fill() to populate global/stream windows.
    Phase A: nodes only, edges reserved for future.
    """
    nodes: Sequence[ZNode]     # Sorted by score descending
    edges: Sequence[ZEdge]     # Reserved (empty in Phase A)
    quotas: Budgets            # Original request budgets
    seed: str                  # Selection seed/run_id
    zv: str                    # Z-Selector version


class Metrics(TypedDict):
    """FAB health metrics for state transitions"""
    stress: float            # Load stress [0.0, 1.0] (>0.7 triggers degradation)
    self_presence: float     # SELF token presence [0.0, 1.0] (≥0.8 for FAB0→FAB1)
    error_rate: float        # Error rate [0.0, 1.0] (>0.05 triggers degradation)
