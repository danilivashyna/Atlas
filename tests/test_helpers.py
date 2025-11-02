# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Type coercion helpers for test fixtures (PR#6.1: Type Safety Cleanup).

These helpers ensure type-safe parameter passing to FABCore across all test files,
eliminating reportArgumentType errors from dict-based configuration merging.
"""

from typing import Optional, Tuple


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
