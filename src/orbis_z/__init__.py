"""
Orbis Z-Space Integration Layer

Minimal adapter between FAB (Flex Adaptive Budget) and Z-Space slice representation.
Provides thin interface for deterministic node selection without tight coupling.

Phase 1: Compatible with existing FAB contracts (score-based selection)
Phase 2: Vec-based MMR diversity (future)
"""

from .contracts import ZSliceLite, ZNode, ZEdge
from .shim import ZSpaceShim

__all__ = ["ZSliceLite", "ZNode", "ZEdge", "ZSpaceShim"]
