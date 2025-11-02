# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Type coercion helpers for test fixtures (PR#6.1: Type Safety Cleanup).

These helpers ensure type-safe parameter passing to FABCore across all test files,
eliminating reportArgumentType errors from dict-based configuration merging.
"""

from typing import Optional, Tuple, cast
from orbis_fab.types import Budgets
from orbis_z import ZSliceLite  # Use orbis_z definition for Z-space tests


def as_str(v: object, default: str = "") -> str:
    """Coerce value to str with fallback."""
    return str(v) if v is not None else default


def as_opt_str(v: object) -> Optional[str]:
    """Coerce value to Optional[str], treating empty/None as None."""
    return None if v in (None, "", "None") else str(v)


def as_bool(v: object, default: bool = False) -> bool:
    """Coerce value to bool with intelligent parsing."""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in {"1", "true", "yes", "y", "on"}:
            return True
        if s in {"0", "false", "no", "n", "off"}:
            return False
    return default


def as_int(v: object, default: int = 0) -> int:
    """Coerce value to int with fallback."""
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        try:
            return int(float(v))
        except ValueError:
            return default
    return default


def as_float(v: object, default: float = 0.0) -> float:
    """Coerce value to float with fallback."""
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return default
    return default


def as_bounds_tuple(v: object, default: Tuple[float, float] = (0.0, 0.0)) -> Tuple[float, float]:
    """Parse bounds tuple from various formats: '0.1,0.9' | [0.1, 0.9] | (0.1, 0.9)."""
    if isinstance(v, (list, tuple)) and len(v) == 2:
        return (as_float(v[0]), as_float(v[1]))
    if isinstance(v, str) and "," in v:
        a, b = v.split(",", 1)
        return (as_float(a), as_float(b))
    return default


def as_weights4(
    v: object, 
    default: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
) -> Tuple[float, float, float, float]:
    """Parse 4-tuple of floats from various formats."""
    if isinstance(v, (list, tuple)) and len(v) == 4:
        return (as_float(v[0]), as_float(v[1]), as_float(v[2]), as_float(v[3]))
    if isinstance(v, str) and "," in v:
        parts = [p.strip() for p in v.split(",")]
        if len(parts) == 4:
            return (as_float(parts[0]), as_float(parts[1]), as_float(parts[2]), as_float(parts[3]))
    return default


# TypedDict factory helpers for test data construction

def make_budgets(
    tokens: int = 8000,
    nodes: int = 8,
    edges: int = 0,
    time_ms: int = 50
) -> Budgets:
    """Create type-safe Budgets TypedDict for testing.
    
    IMPORTANT: Field is 'time_ms' (not 'time'). Legacy tests with 'time' field
    will cause reportArgumentType errors.
    """
    return cast(Budgets, {
        "tokens": tokens,
        "nodes": nodes,
        "edges": edges,
        "time_ms": time_ms,
    })


def make_z(
    nodes: Optional[list] = None,
    edges: Optional[list] = None,
    seed: str = "test-z",
    tokens: int = 8000,
    nodes_quota: int = 128,
    edges_quota: int = 0,
    time_ms: int = 30
) -> ZSliceLite:
    """Create type-safe ZSliceLite TypedDict for testing.
    
    Args:
        nodes: List of node dicts (default: 10 dummy nodes)
        edges: List of edge dicts (default: empty)
        seed: Z-slice seed for determinism
        tokens: Token quota
        nodes_quota: Node quota
        edges_quota: Edge quota
        time_ms: Time budget in ms
        
    Note: Returns nodes/edges as lists (mutable sequences) which are
    compatible with Sequence[ZNode]/Sequence[ZEdge] type annotations.
    """
    if nodes is None:
        nodes = [{"id": f"n{i}", "score": 1.0 - i * 0.01} for i in range(10)]
    if edges is None:
        edges = []
    
    return cast(ZSliceLite, {
        "nodes": nodes,  # list is subtype of Sequence
        "edges": edges,  # list is subtype of Sequence
        "quotas": {
            "tokens": tokens,
            "nodes": nodes_quota,
            "edges": edges_quota,
            "time_ms": time_ms
        },
        "seed": seed,
        "zv": "v0.1.0",
    })
