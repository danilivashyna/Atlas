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

from atlas.homeostasis.policy import (
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
    # Policy Engine
    "PolicyEngine",
    "Policy",
    "PolicyEvaluationResult",
    
    # Triggers
    "SimpleTrigger",
    "CompositeTrigger",
    
    # Actions & Criteria
    "Action",
    "SuccessCriteria",
    
    # Enums
    "Priority",
    "Operator",
    "CompositeLogic",
]
