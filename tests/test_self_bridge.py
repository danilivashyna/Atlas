"""
Unit tests для CoherenceBridge.

Проверяются:
- compute_coherence(): вычисление согласованности между состояниями
- compute_coherence_cosine(): косинусное сходство векторов
- compute_continuity(): вычисление непрерывности
- compute_stress(): вычисление стресса
- emit_metrics(): логирование метрик
"""

import logging
import pytest
from src.orbis_self.bridge import CoherenceBridge
from src.orbis_self.contracts import SelfScores, CoherenceProbe


class TestCoherenceBridgeComputeCoherence:
    """Тесты вычисления coherence между состояниями."""

    def test_empty_states_return_max_coherence(self):
        """Пустые состояния → max coherence (нет конфликта)."""
        coherence = CoherenceBridge.compute_coherence({}, {})
        assert coherence == 1.0

    def test_no_common_keys_return_max_coherence(self):
        """Нет общих ключей → max coherence (независимые системы)."""
        fab_state = {"tick": 100, "fab_mode": "FAB2"}
        atlas_state = {"z_space_active": True}

        coherence = CoherenceBridge.compute_coherence(fab_state, atlas_state)
        assert coherence == 1.0

    def test_exact_match_return_max_coherence(self):
        """Полное совпадение → max coherence."""
        state = {"tick": 100, "mode": "FAB2", "active": True}

        coherence = CoherenceBridge.compute_coherence(state, state)
        assert coherence == 1.0

    def test_string_mismatch_reduces_coherence(self):
        """Несовпадение строк → coherence <1.0."""
        fab_state = {"mode": "FAB2"}
        atlas_state = {"mode": "FAB1"}

        coherence = CoherenceBridge.compute_coherence(fab_state, atlas_state)
        assert coherence == 0.0

    def test_numeric_similarity(self):
        """Числовые значения учитывают близость."""
        fab_state = {"score": 0.8}
        atlas_state = {"score": 0.7}

        coherence = CoherenceBridge.compute_coherence(fab_state, atlas_state)
        assert 0.0 < coherence < 1.0


class TestCoherenceBridgeComputeCoherenceCosine:
    """Тесты косинусного сходства."""

    def test_identical_vectors(self):
        """Идентичные векторы → max similarity."""
        vec = [1.0, 2.0, 3.0]

        similarity = CoherenceBridge.compute_coherence_cosine(vec, vec)
        assert similarity == pytest.approx(1.0, abs=0.01)

    def test_opposite_vectors(self):
        """Противоположные векторы → min similarity."""
        vec_a = [1.0, 0.0]
        vec_b = [-1.0, 0.0]

        similarity = CoherenceBridge.compute_coherence_cosine(vec_a, vec_b)
        assert similarity == pytest.approx(0.0, abs=0.01)

    def test_orthogonal_vectors(self):
        """Ортогональные векторы → средняя similarity."""
        vec_a = [1.0, 0.0]
        vec_b = [0.0, 1.0]

        similarity = CoherenceBridge.compute_coherence_cosine(vec_a, vec_b)
        assert similarity == pytest.approx(0.5, abs=0.01)

    def test_empty_vectors(self):
        """Пустые векторы → default 1.0."""
        similarity = CoherenceBridge.compute_coherence_cosine([], [])
        assert similarity == 1.0

    def test_different_length_vectors(self):
        """Векторы разной длины → default 1.0."""
        similarity = CoherenceBridge.compute_coherence_cosine([1.0], [1.0, 2.0])
        assert similarity == 1.0


class TestCoherenceBridgeComputeContinuity:
    """Тесты вычисления continuity."""

    def test_no_change_max_continuity(self):
        """Без изменения presence → max continuity."""
        continuity = CoherenceBridge.compute_continuity(0.8, 0.8)
        assert continuity == 1.0

    def test_small_change_high_continuity(self):
        """Малое изменение → высокая continuity."""
        continuity = CoherenceBridge.compute_continuity(0.8, 0.85)
        assert continuity == pytest.approx(0.95, abs=0.01)

    def test_large_change_low_continuity(self):
        """Большое изменение → низкая continuity."""
        continuity = CoherenceBridge.compute_continuity(0.1, 0.9)
        assert continuity == pytest.approx(0.2, abs=0.01)

    def test_complete_reversal_zero_continuity(self):
        """Полное изменение → zero continuity."""
        continuity = CoherenceBridge.compute_continuity(0.0, 1.0)
        assert continuity == 0.0


class TestCoherenceBridgeComputeStress:
    """Тесты вычисления stress."""

    def test_high_stability_low_stress(self):
        """Высокая stability → низкий stress."""
        stress = CoherenceBridge.compute_stress(stability_score=0.9, oscillation_rate=0.0)
        assert stress < 0.3

    def test_low_stability_high_stress(self):
        """Низкая stability → высокий stress."""
        stress = CoherenceBridge.compute_stress(stability_score=0.2, oscillation_rate=0.0)
        assert stress > 0.5

    def test_high_oscillation_increases_stress(self):
        """Высокая oscillation → увеличивает stress."""
        stress_low = CoherenceBridge.compute_stress(
            stability_score=0.8, oscillation_rate=0.0
        )
        stress_high = CoherenceBridge.compute_stress(
            stability_score=0.8, oscillation_rate=1.0
        )

        assert stress_high > stress_low

    def test_none_values_use_defaults(self):
        """None значения → использует defaults."""
        stress = CoherenceBridge.compute_stress(
            stability_score=None, oscillation_rate=None
        )
        assert 0.0 <= stress <= 1.0


class TestCoherenceBridgeEmitMetrics:
    """Тесты эмиссии метрик."""

    def test_emit_metrics_logs_to_logger(self, caplog):
        """emit_metrics() логирует метрики."""
        scores: SelfScores = {
            "presence": 0.8,
            "coherence": 0.6,
            "continuity": 0.9,
            "stress": 0.2,
        }

        with caplog.at_level(logging.INFO):
            CoherenceBridge.emit_metrics("test-prefix", scores)

        assert len(caplog.records) == 1
        assert "SELF_METRICS[test-prefix]" in caplog.text
        assert "presence=0.800" in caplog.text
        assert "coherence=0.600" in caplog.text
