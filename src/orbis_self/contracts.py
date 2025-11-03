"""
SELF Contracts - базовые типы данных для системы самореференции.

Все метрики нормализованы в диапазон [0.0, 1.0]:
- presence: "я есть" - степень активности системы
- coherence: согласованность FAB ↔ Atlas состояний
- continuity: непрерывность потока выполнения
- stress: уровень перегрузки/отклонения от номинала
"""

from dataclasses import dataclass, field
from typing import TypedDict, Literal, Any


# ─────────────────────────────────────────────────────────────
# Core Scores
# ─────────────────────────────────────────────────────────────


class SelfScores(TypedDict):
    """Основные метрики SELF токена в нормализованном виде [0.0, 1.0]."""

    presence: float  # Степень присутствия/активности
    coherence: float  # Согласованность состояния FAB↔Atlas
    continuity: float  # Непрерывность выполнения
    stress: float  # Уровень стресса/перегрузки


# ─────────────────────────────────────────────────────────────
# Events
# ─────────────────────────────────────────────────────────────

SelfEventKind = Literal["mint", "update", "transfer", "replicate", "heartbeat"]


@dataclass
class SelfEvent:
    """Событие жизненного цикла SELF токена."""

    ts: str  # ISO8601 timestamp
    kind: SelfEventKind  # Тип события
    token_id: str  # ID токена
    data: dict[str, Any] = field(default_factory=dict)  # Дополнительные данные

    def to_jsonl(self) -> str:
        """Сериализация в JSONL формат для identity.jsonl."""
        import json

        return json.dumps(
            {"ts": self.ts, "kind": self.kind, "token_id": self.token_id, **self.data}
        )


# ─────────────────────────────────────────────────────────────
# Coherence Probes
# ─────────────────────────────────────────────────────────────


class CoherenceProbe(TypedDict, total=False):
    """
    Зонд для измерения согласованности состояний FAB ↔ Atlas.

    Минимальный контракт - любые поля опциональны.
    Используется CoherenceBridge для вычисления coherence метрики.
    """

    tick: int  # Текущий тик системы
    fab_mode: str | None  # FAB0/FAB1/FAB2
    precision: str | None  # Текущая точность (mxfp4.12, etc)
    stability_score: float | None  # Скор стабильности из StabilityTracker
    z_space_active: bool | None  # Z-Space активен?
    custom: dict[str, Any] | None  # Произвольные доп. данные


# ─────────────────────────────────────────────────────────────
# Validation utilities
# ─────────────────────────────────────────────────────────────


def clip_01(value: float) -> float:
    """Клип значения в диапазон [0.0, 1.0]."""
    return max(0.0, min(1.0, value))


def validate_scores(scores: SelfScores) -> SelfScores:
    """
    Валидация и нормализация SelfScores.

    Все значения клипаются в [0.0, 1.0].
    """
    return SelfScores(
        presence=clip_01(scores.get("presence", 0.0)),
        coherence=clip_01(scores.get("coherence", 0.0)),
        continuity=clip_01(scores.get("continuity", 0.0)),
        stress=clip_01(scores.get("stress", 0.0)),
    )


__all__ = [
    "SelfScores",
    "SelfEvent",
    "SelfEventKind",
    "CoherenceProbe",
    "clip_01",
    "validate_scores",
]
