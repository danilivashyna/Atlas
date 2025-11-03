"""
SelfToken - ядро системы самореференции.

Токен хранит 4 основные метрики состояния системы:
1. presence: "я есть" - активность, степень присутствия
2. coherence: согласованность между FAB и Atlas
3. continuity: непрерывность выполнения во времени
4. stress: уровень перегрузки/отклонения

Токен поддерживает:
- normalize(): приведение всех значений к [0.0, 1.0]
- decay(): экспоненциальная деградация метрик со временем
- as_dict(): сериализация в SelfScores
"""

from dataclasses import dataclass, field
from typing import Any

from .contracts import SelfScores, clip_01


@dataclass
class SelfToken:
    """
    Токен самореференции с основными метриками состояния.

    Все значения нормализованы в [0.0, 1.0].
    """

    presence: float = 0.0  # Степень присутствия/активности
    coherence: float = 0.0  # Согласованность FAB↔Atlas
    continuity: float = 0.0  # Непрерывность во времени
    stress: float = 0.0  # Уровень перегрузки

    # Metadata
    token_id: str = ""
    tick: int = 0  # Последний тик обновления
    metadata: dict[str, Any] = field(default_factory=dict)

    def normalize(self) -> "SelfToken":
        """
        Нормализация всех метрик в диапазон [0.0, 1.0].

        Изменяет объект in-place и возвращает self для chaining.
        """
        self.presence = clip_01(self.presence)
        self.coherence = clip_01(self.coherence)
        self.continuity = clip_01(self.continuity)
        self.stress = clip_01(self.stress)
        return self

    def decay(self, rate: float = 0.01) -> "SelfToken":
        """
        Экспоненциальная деградация метрик со временем.

        Args:
            rate: Скорость деградации [0.0, 1.0]. По умолчанию 0.01 (1% за тик).

        Returns:
            self для chaining

        Формула: value *= (1 - rate)

        Stress НЕ деградирует (только растёт от внешних факторов).
        """
        if not 0.0 <= rate <= 1.0:
            raise ValueError(f"Decay rate must be in [0.0, 1.0], got {rate}")

        decay_factor = 1.0 - rate

        self.presence *= decay_factor
        self.coherence *= decay_factor
        self.continuity *= decay_factor
        # stress НЕ деградирует автоматически

        # Clip после decay для безопасности
        return self.normalize()

    def as_dict(self) -> SelfScores:
        """
        Сериализация в SelfScores TypedDict.

        Идемпотентна: повторные вызовы возвращают одинаковый результат.
        """
        return SelfScores(
            presence=self.presence,
            coherence=self.coherence,
            continuity=self.continuity,
            stress=self.stress,
        )

    def compute_status(self) -> str:
        """
        Вычисление статуса токена на основе stress метрики.

        Returns:
            "stable" | "degraded" | "critical"
        """
        if self.stress >= 0.7:
            return "critical"
        if self.stress >= 0.5:
            return "degraded"
        return "stable"

    def update_from_dict(self, scores: dict[str, float]) -> "SelfToken":
        """
        Безопасное обновление метрик из словаря.

        Принимает частичные апдейты, игнорирует неизвестные ключи.
        Автоматически нормализует после обновления.
        """
        if "presence" in scores:
            self.presence = scores["presence"]
        if "coherence" in scores:
            self.coherence = scores["coherence"]
        if "continuity" in scores:
            self.continuity = scores["continuity"]
        if "stress" in scores:
            self.stress = scores["stress"]

        return self.normalize()

    def __repr__(self) -> str:
        """Читаемое представление токена."""
        status = self.compute_status()
        return (
            f"SelfToken(id={self.token_id!r}, "
            f"P={self.presence:.3f}, C={self.coherence:.3f}, "
            f"Co={self.continuity:.3f}, S={self.stress:.3f}, "
            f"status={status})"
        )


__all__ = ["SelfToken"]
