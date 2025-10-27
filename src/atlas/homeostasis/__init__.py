"""
Atlas Homeostasis — автоматический контур саморегуляции.

Компоненты:
- policy: Policy Engine (YAML-правила реагирования на метрики)
- decision: Decision Engine (превращение метрик в решения)
- actions: Action Adapters (выполнение действий с pre-checks)
- snapshot: Snapshot & Rollback (атомарные снапшоты)
- audit: Audit & WAL (идемпотентный журнал)
- sleep: Sleep & Consolidation (ночной "сон")

Архитектурная роль:
E4 замыкает контур самосознания:
    Observe (E3) → Decide (policy) → Act (actions) → Reflect (audit) → Observe
"""

"""Atlas Homeostasis module for E4 (self-healing loop)."""

from .actions import ActionAdapter, ActionResult, ActionStatus
from .audit import AuditEvent, AuditEventType, AuditLogger
from .decision import ActionDecision, CooldownEntry, DecisionEngine, RateLimitWindow
from .policy import (
    Action,
    CompositeLogic,
    CompositeTrigger,
    Operator,
    Policy,
    PolicyEngine,
    PolicyEvaluationResult,
    Priority,
    SimpleTrigger,
    SuccessCriteria,
)

__all__ = [
    # Policy Engine (E4.1)
    "PolicyEngine",
    "Policy",
    "SimpleTrigger",
    "CompositeTrigger",
    "Action",
    "SuccessCriteria",
    "Priority",
    "Operator",
    "CompositeLogic",
    "PolicyEvaluationResult",
    # Decision Engine (E4.2)
    "DecisionEngine",
    "ActionDecision",
    "CooldownEntry",
    "RateLimitWindow",
    # Action Adapters (E4.3)
    "ActionAdapter",
    "ActionResult",
    "ActionStatus",
    # Audit Logger (E4.5)
    "AuditLogger",
    "AuditEvent",
    "AuditEventType",
]
