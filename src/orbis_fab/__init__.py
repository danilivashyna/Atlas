"""orbis_fab package - Phase A MVP + Phase B Enhancements

FAB (Focal Attention Buffer) - Autonomous state machine with dual windows.

Public API:
- FABCore: Main orchestrator (init_tick/fill/mix/step_stub)
- FabMode: State machine modes (FAB0/FAB1/FAB2)
- Budgets: Fixed capacity per tick
- ZSliceLite: Minimal Z-space slice
- Metrics: Health metrics for transitions
- classify_backpressure: Token-bucket backpressure control
- assign_precision: Bit-envelope precision assignment
- Diagnostics: Lightweight counters and gauges (Phase B.5)

Phase B Components (v0.2 enhancements):
- Hysteresis: Dead band precision control (B.1)
- Stability: Exponential cool-down tracking (B.2)
- Rebalance: MMR-like diversity (B.3)
- Seeding: Deterministic tie-breaking (B.4)
- Diagnostics: Counters/gauges for observability (B.5)

Usage:
    from orbis_fab import FABCore, Budgets, ZSliceLite, Diagnostics

    fab = FABCore()
    fab.init_tick(mode="FAB0", budgets={"tokens": 4096, "nodes": 256, "edges": 0, "time_ms": 30})
    fab.fill(z_slice)
    context = fab.mix()  # context["diagnostics"] included
    result = fab.step_stub(stress=0.3, self_presence=0.85, error_rate=0.0)
"""

from .core import FABCore
from .types import FabMode, Budgets, ZSliceLite, Metrics, ZNode, ZEdge
from .state import FabState, Window
from .backpressure import classify_backpressure
from .envelope import assign_precision, precision_level
from .diagnostics import Diagnostics
from .api_routes import create_fab_router

__version__ = "0.1.0-alpha"

__all__ = [
    "FABCore",
    "FabMode",
    "Budgets",
    "ZSliceLite",
    "Metrics",
    "ZNode",
    "ZEdge",
    "FabState",
    "Window",
    "classify_backpressure",
    "assign_precision",
    "precision_level",
    "Diagnostics",
    "create_fab_router",
]
