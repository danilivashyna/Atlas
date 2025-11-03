"""
FAB SELF Bridge (Experimental) - адаптер для интеграции SELF в FABCore.

⚠️  EXP_SANDBOX: DO NOT MERGE INTO CORE WITHOUT REVIEW ⚠️

Этот модуль НЕ изменяет существующий FABCore.
Предоставляет wrapper функции для опциональной интеграции SELF токенов.

Активация:
    export AURIS_SELF=on

    from orbis_fab.fab_self_bridge_exp import attach, maybe_self_tick
    self_mgr = attach(fab_core_instance)

    # В цикле обработки
    maybe_self_tick(fab_core, self_mgr, id="fab-default")

Изоляция:
- Не импортируется автоматически
- Не модифицирует FABCore напрямую
- Активируется только явным вызовом
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def attach(fab_core: Any):
    """
    Создание SelfManager и привязка к FABCore instance.

    Args:
        fab_core: FABCore instance (только для чтения состояния)

    Returns:
        SelfManager instance

    Note:
        Не модифицирует fab_core, только читает его состояние.
    """
    # Lazy import для изоляции
    from orbis_self.manager import SelfManager

    # Проверяем feature flag
    if not os.getenv("AURIS_SELF", "off").lower() in ("on", "true", "1"):
        logger.info("AURIS_SELF=off, SelfManager not activated")
        return None

    self_mgr = SelfManager()

    logger.info("SelfManager attached to FABCore instance %s", fab_core.__class__.__name__)

    return self_mgr


def maybe_self_tick(
    fab_core: Any,
    self_mgr: Any,
    token_id: str = "fab-default",
    tick_interval: int = 1,
    heartbeat_interval: int = 50,
) -> bool:
    """
    Обновление SELF токена на основе текущего состояния FABCore.

    Args:
        fab_core: FABCore instance (для чтения состояния)
        self_mgr: SelfManager instance
        token_id: ID токена для обновления
        tick_interval: Частота обновления (каждые N тиков)
        heartbeat_interval: Частота записи heartbeat

    Returns:
        True если обновление произведено

    Поведение:
        1. Извлекает состояние FAB (mode, precision, stability)
        2. Вычисляет coherence через CoherenceBridge
        3. Обновляет SelfToken (presence↑, continuity, stress)
        4. Периодически вызывает heartbeat()

    Note:
        Если AURIS_SELF=off или self_mgr=None → no-op
    """
    # No-op если SELF отключён
    if self_mgr is None:
        return False

    if not os.getenv("AURIS_SELF", "off").lower() in ("on", "true", "1"):
        return False

    # Lazy imports
    from orbis_self.bridge import CoherenceBridge
    from orbis_self.contracts import CoherenceProbe

    # Получаем текущий тик FAB
    current_tick = getattr(fab_core, "current_tick", 0)

    # Проверяем tick_interval
    if current_tick % tick_interval != 0:
        return False

    # Создаём токен если не существует
    if self_mgr.get_token(token_id) is None:
        self_mgr.mint(token_id)

    token = self_mgr.get_token(token_id)
    previous_presence = token.presence

    # ──────────────────────────────────────────────────────────
    # Извлечение FAB состояния (безопасно, с fallback)
    # ──────────────────────────────────────────────────────────

    fab_state: CoherenceProbe = {
        "tick": current_tick,
        "fab_mode": getattr(getattr(fab_core, "st", None), "mode", None),
        "precision": None,  # TODO: извлечь из hysteresis state
        "stability_score": None,  # TODO: извлечь из stable_tracker
        "z_space_active": None,  # TODO: проверить Z-Space
    }

    # Atlas состояние (минимальное, для демонстрации)
    atlas_state: CoherenceProbe = {
        "tick": current_tick,
        "custom": {"source": "atlas"},
    }

    # ──────────────────────────────────────────────────────────
    # Вычисление метрик
    # ──────────────────────────────────────────────────────────

    # Coherence между FAB и Atlas
    coherence = CoherenceBridge.compute_coherence(fab_state, atlas_state)

    # Presence: растёт при активности
    presence = min(1.0, previous_presence + 0.05)  # Линейный рост

    # Continuity: на основе стабильности presence
    continuity = CoherenceBridge.compute_continuity(previous_presence, presence)

    # Stress: на основе stability_score и oscillation_rate
    stability_score = fab_state.get("stability_score")
    oscillation_rate = 0.0  # TODO: извлечь из hysteresis metrics
    stress = CoherenceBridge.compute_stress(stability_score, oscillation_rate)

    # ──────────────────────────────────────────────────────────
    # Обновление токена
    # ──────────────────────────────────────────────────────────

    self_mgr.update(
        token_id,
        tick=current_tick,
        presence=presence,
        coherence=coherence,
        continuity=continuity,
        stress=stress,
    )

    # Heartbeat
    self_mgr.heartbeat(token_id, every_n=heartbeat_interval)

    # Emit metrics через logging
    CoherenceBridge.emit_metrics(token_id, token.as_dict())

    return True


def extract_fab_state_safe(fab_core: Any) -> dict[str, Any]:
    """
    Безопасное извлечение FAB состояния с fallback на None.

    Args:
        fab_core: FABCore instance

    Returns:
        Словарь с FAB метриками (может содержать None значения)

    Note:
        Использует getattr с defaults для защиты от AttributeError.
        Адаптируется к изменениям FABCore структуры.
    """
    state = {
        "tick": getattr(fab_core, "current_tick", 0),
        "fab_mode": None,
        "precision": None,
        "stability_score": None,
        "dwell_counter": None,
        "oscillation_rate": None,
    }

    # FAB mode из StateTuple
    st = getattr(fab_core, "st", None)
    if st:
        state["fab_mode"] = getattr(st, "mode", None)

    # Hysteresis state (если доступен)
    # В реальной интеграции нужно добавить доступ к hysteresis_state

    # StabilityTracker (если доступен)
    stable_tracker = getattr(fab_core, "stable_tracker", None)
    if stable_tracker:
        state["stability_score"] = getattr(stable_tracker, "stability_score", None)

    return state


__all__ = [
    "attach",
    "maybe_self_tick",
    "extract_fab_state_safe",
]
