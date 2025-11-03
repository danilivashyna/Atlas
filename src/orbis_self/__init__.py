"""
SELF (Self-Experimental Lifecycle Framework) - экспериментальная система самореференции.

Этот модуль реализует концепцию "токена присутствия" для отслеживания когерентности
и непрерывности работы системы. Активируется через env var AURIS_SELF=on.

Основные компоненты:
- SelfToken: токен с метриками (presence, coherence, continuity, stress)
- SelfManager: управление жизненным циклом токенов (mint/update/transfer/replicate)
- CoherenceBridge: синхронизация FAB ↔ Atlas состояний

Изоляция:
Модуль полностью независим от основного кода FABCore/ZSpace и не изменяет их поведение.
Интеграция возможна только через явный адаптер (fab_self_bridge_exp.py) при AURIS_SELF=on.
"""

import os
from typing import Literal

__version__ = "0.1.0-exp"

# Feature flag
ACTIVE = os.getenv("AURIS_SELF", "off").lower() in ("on", "true", "1")

# Type shortcuts
SelfStatus = Literal["stable", "degraded", "critical"]
SelfEventKind = Literal["mint", "update", "transfer", "replicate", "heartbeat"]

__all__ = [
    "ACTIVE",
    "SelfStatus",
    "SelfEventKind",
]
