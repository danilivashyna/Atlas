"""
CoherenceBridge - вычисление согласованности между FAB и Atlas состояниями.

Основная задача: измерить степень согласованности (coherence) между:
- FAB состоянием (precision, stability, mode)
- Atlas состоянием (embeddings, Z-Space)

Используется простая эвристика на основе косинусного сходства или
пересечения ключей состояний.
"""

import logging
import math
from typing import Any

from .contracts import CoherenceProbe, SelfScores

logger = logging.getLogger(__name__)


class CoherenceBridge:
    """
    Мост для вычисления согласованности FAB ↔ Atlas состояний.

    Реализует простую эвристику без сложных зависимостей.
    """

    @staticmethod
    def compute_coherence(
        fab_state: dict[str, Any] | CoherenceProbe,
        atlas_state: dict[str, Any] | CoherenceProbe,
    ) -> float:
        """
        Вычисление coherence между FAB и Atlas состояниями.

        Args:
            fab_state: FAB состояние (tick, fab_mode, precision, stability_score)
            atlas_state: Atlas состояние (embeddings, z_space_active, etc)

        Returns:
            Coherence в диапазоне [0.0, 1.0]

        Эвристика:
        1. Если недостаточно данных → 1.0 (оптимистичный default)
        2. Вычисляем пересечение ключей
        3. Для числовых значений - косинусное сходство
        4. Для категориальных - exact match
        """
        # Пустые состояния → максимальная согласованность (нет конфликта)
        if not fab_state or not atlas_state:
            return 1.0

        # Находим общие ключи
        fab_keys = set(fab_state.keys())
        atlas_keys = set(atlas_state.keys())
        common_keys = fab_keys & atlas_keys

        if not common_keys:
            # Нет пересечения → считаем согласованными (независимые системы)
            return 1.0

        # Вычисляем согласованность по общим ключам
        matches = 0
        total = 0

        for key in common_keys:
            fab_val = fab_state[key]
            atlas_val = atlas_state[key]

            # Пропускаем None значения
            if fab_val is None or atlas_val is None:
                continue

            total += 1

            # Числовые значения - нормализованная разница
            if isinstance(fab_val, (int, float)) and isinstance(atlas_val, (int, float)):
                # Для bool (0/1) - exact match
                if isinstance(fab_val, bool) and isinstance(atlas_val, bool):
                    if fab_val == atlas_val:
                        matches += 1
                else:
                    # Нормализуем в [0, 1] и вычисляем близость
                    try:
                        diff = abs(float(fab_val) - float(atlas_val))
                        # Предполагаем значения в разумном диапазоне [0, 10]
                        similarity = max(0.0, 1.0 - diff / 10.0)
                        matches += similarity
                    except (ValueError, ZeroDivisionError):
                        pass

            # Строковые/категориальные - exact match
            elif isinstance(fab_val, str) and isinstance(atlas_val, str):
                if fab_val.lower() == atlas_val.lower():
                    matches += 1

            # Остальное - exact match
            else:
                if fab_val == atlas_val:
                    matches += 1

        # Если не было совпадений для сравнения
        if total == 0:
            return 1.0

        coherence = matches / total
        return max(0.0, min(1.0, coherence))

    @staticmethod
    def compute_coherence_cosine(
        vec_a: list[float],
        vec_b: list[float],
    ) -> float:
        """
        Косинусное сходство между двумя векторами.

        Args:
            vec_a: Первый вектор
            vec_b: Второй вектор

        Returns:
            Косинусное сходство в [0.0, 1.0] (нормализовано из [-1, 1])

        Note:
            Используется для сравнения embedding векторов.
        """
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 1.0  # Default для несовместимых векторов

        # Dot product
        dot = sum(a * b for a, b in zip(vec_a, vec_b))

        # Magnitudes
        mag_a = math.sqrt(sum(a * a for a in vec_a))
        mag_b = math.sqrt(sum(b * b for b in vec_b))

        if mag_a == 0.0 or mag_b == 0.0:
            return 0.0

        # Cosine similarity [-1, 1]
        cos_sim = dot / (mag_a * mag_b)

        # Normalize to [0, 1]
        return (cos_sim + 1.0) / 2.0

    @staticmethod
    def emit_metrics(prefix: str, scores: SelfScores) -> None:
        """
        Эмиссия SELF метрик через logging.

        В будущем можно заменить на Prometheus/StatsD.

        Args:
            prefix: Префикс для метрик (например "fab-default")
            scores: SelfScores для логирования
        """
        logger.info(
            "SELF_METRICS[%s]: presence=%.3f coherence=%.3f continuity=%.3f stress=%.3f",
            prefix,
            scores["presence"],
            scores["coherence"],
            scores["continuity"],
            scores["stress"],
        )

    @staticmethod
    def compute_continuity(
        previous_presence: float,
        current_presence: float,
    ) -> float:
        """
        Вычисление continuity на основе стабильности presence.

        Args:
            previous_presence: Предыдущее значение presence
            current_presence: Текущее значение presence

        Returns:
            Continuity в [0.0, 1.0]

        Формула:
            continuity = 1.0 - |current - previous|

        Чем меньше изменение presence, тем выше continuity.
        """
        diff = abs(current_presence - previous_presence)
        return max(0.0, 1.0 - diff)

    @staticmethod
    def compute_stress(
        stability_score: float | None,
        oscillation_rate: float | None,
    ) -> float:
        """
        Вычисление stress на основе метрик стабильности.

        Args:
            stability_score: Скор стабильности из StabilityTracker [0.0, 1.0]
            oscillation_rate: Частота осцилляций из hysteresis [0.0, ∞)

        Returns:
            Stress в [0.0, 1.0]

        Эвристика:
            stress = (1 - stability) * 0.7 + min(1.0, oscillation_rate) * 0.3
        """
        # Default значения если данные отсутствуют
        if stability_score is None:
            stability_score = 0.8  # Оптимистичный default

        if oscillation_rate is None:
            oscillation_rate = 0.0

        # Инверсия stability (низкая стабильность = высокий стресс)
        stability_stress = (1.0 - stability_score) * 0.7

        # Нормализация oscillation_rate (предполагаем <1.0 это норма)
        oscillation_stress = min(1.0, oscillation_rate) * 0.3

        stress = stability_stress + oscillation_stress
        return max(0.0, min(1.0, stress))


__all__ = ["CoherenceBridge"]
