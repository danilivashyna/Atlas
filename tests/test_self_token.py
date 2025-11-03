"""
Unit tests для SelfToken.

Проверяются:
- normalize(): клипает значения в [0.0, 1.0]
- decay(): экспоненциальная деградация метрик
- as_dict(): идемпотентная сериализация
- compute_status(): правильное вычисление статуса
- update_from_dict(): частичные апдейты
"""

import pytest
from src.orbis_self.token import SelfToken


class TestSelfTokenNormalize:
    """Тесты нормализации значений в [0.0, 1.0]."""

    def test_normalize_clips_high_values(self):
        """Значения >1.0 клипаются до 1.0."""
        token = SelfToken(
            presence=1.5,
            coherence=2.0,
            continuity=10.0,
            stress=3.5,
        )

        token.normalize()

        assert token.presence == 1.0
        assert token.coherence == 1.0
        assert token.continuity == 1.0
        assert token.stress == 1.0

    def test_normalize_clips_low_values(self):
        """Значения <0.0 клипаются до 0.0."""
        token = SelfToken(
            presence=-0.5,
            coherence=-1.0,
            continuity=-10.0,
            stress=-2.0,
        )

        token.normalize()

        assert token.presence == 0.0
        assert token.coherence == 0.0
        assert token.continuity == 0.0
        assert token.stress == 0.0

    def test_normalize_preserves_valid_values(self):
        """Значения в [0.0, 1.0] не изменяются."""
        token = SelfToken(
            presence=0.5,
            coherence=0.75,
            continuity=0.25,
            stress=0.9,
        )

        original = token.as_dict()
        token.normalize()

        assert token.as_dict() == original

    def test_normalize_returns_self(self):
        """normalize() возвращает self для chaining."""
        token = SelfToken()
        result = token.normalize()

        assert result is token


class TestSelfTokenDecay:
    """Тесты экспоненциальной деградации метрик."""

    def test_decay_reduces_presence(self):
        """Decay уменьшает presence."""
        token = SelfToken(presence=1.0, coherence=1.0, continuity=1.0, stress=0.0)

        token.decay(rate=0.1)  # 10% деградация

        assert token.presence < 1.0
        assert token.presence == pytest.approx(0.9, abs=0.01)

    def test_decay_does_not_affect_stress(self):
        """Stress НЕ деградирует (только растёт от внешних факторов)."""
        token = SelfToken(presence=1.0, coherence=1.0, continuity=1.0, stress=0.8)

        token.decay(rate=0.1)

        assert token.stress == 0.8  # Без изменений

    def test_decay_never_goes_negative(self):
        """Decay не уводит значения < 0.0."""
        token = SelfToken(presence=0.01, coherence=0.01, continuity=0.01)

        # Многократный decay
        for _ in range(100):
            token.decay(rate=0.5)

        assert token.presence >= 0.0
        assert token.coherence >= 0.0
        assert token.continuity >= 0.0

    def test_decay_invalid_rate_raises_error(self):
        """Decay с rate вне [0.0, 1.0] вызывает ValueError."""
        token = SelfToken()

        with pytest.raises(ValueError, match="Decay rate must be in"):
            token.decay(rate=1.5)

        with pytest.raises(ValueError, match="Decay rate must be in"):
            token.decay(rate=-0.1)

    def test_decay_returns_self(self):
        """decay() возвращает self для chaining."""
        token = SelfToken(presence=1.0)
        result = token.decay()

        assert result is token

    def test_decay_default_rate(self):
        """Decay с default rate=0.01."""
        token = SelfToken(presence=1.0)

        token.decay()  # Без аргументов

        assert token.presence == pytest.approx(0.99, abs=0.01)


class TestSelfTokenAsDict:
    """Тесты сериализации в SelfScores."""

    def test_as_dict_returns_valid_self_scores(self):
        """as_dict() возвращает валидный SelfScores TypedDict."""
        token = SelfToken(
            presence=0.8,
            coherence=0.6,
            continuity=0.9,
            stress=0.2,
        )

        scores = token.as_dict()

        assert isinstance(scores, dict)
        assert scores["presence"] == 0.8
        assert scores["coherence"] == 0.6
        assert scores["continuity"] == 0.9
        assert scores["stress"] == 0.2

    def test_as_dict_is_idempotent(self):
        """Повторные вызовы as_dict() возвращают одинаковый результат."""
        token = SelfToken(presence=0.5, coherence=0.7, continuity=0.3, stress=0.1)

        scores1 = token.as_dict()
        scores2 = token.as_dict()

        assert scores1 == scores2

    def test_as_dict_independent_from_token(self):
        """Изменение токена не влияет на ранее полученный dict."""
        token = SelfToken(presence=0.5)

        scores_before = token.as_dict()
        token.presence = 0.8
        scores_after = token.as_dict()

        assert scores_before["presence"] == 0.5
        assert scores_after["presence"] == 0.8


class TestSelfTokenComputeStatus:
    """Тесты вычисления статуса на основе stress."""

    def test_compute_status_stable(self):
        """Stress <0.5 → stable."""
        token = SelfToken(stress=0.3)
        assert token.compute_status() == "stable"

    def test_compute_status_degraded(self):
        """Stress ≥0.5 и <0.7 → degraded."""
        token = SelfToken(stress=0.6)
        assert token.compute_status() == "degraded"

    def test_compute_status_critical(self):
        """Stress ≥0.7 → critical."""
        token = SelfToken(stress=0.8)
        assert token.compute_status() == "critical"

    def test_compute_status_boundary_degraded(self):
        """Граница stress=0.5 → degraded."""
        token = SelfToken(stress=0.5)
        assert token.compute_status() == "degraded"

    def test_compute_status_boundary_critical(self):
        """Граница stress=0.7 → critical."""
        token = SelfToken(stress=0.7)
        assert token.compute_status() == "critical"


class TestSelfTokenUpdateFromDict:
    """Тесты безопасного обновления из словаря."""

    def test_update_from_dict_partial_update(self):
        """Частичные апдейты не трогают остальные поля."""
        token = SelfToken(presence=0.5, coherence=0.5, continuity=0.5, stress=0.5)

        token.update_from_dict({"presence": 0.8, "stress": 0.2})

        assert token.presence == 0.8
        assert token.coherence == 0.5  # Не изменилось
        assert token.continuity == 0.5  # Не изменилось
        assert token.stress == 0.2

    def test_update_from_dict_ignores_unknown_keys(self):
        """Неизвестные ключи игнорируются."""
        token = SelfToken(presence=0.5)

        token.update_from_dict({"presence": 0.8, "unknown_field": 999})

        assert token.presence == 0.8
        assert not hasattr(token, "unknown_field")

    def test_update_from_dict_normalizes(self):
        """Значения автоматически нормализуются."""
        token = SelfToken()

        token.update_from_dict({"presence": 1.5, "stress": -0.5})

        assert token.presence == 1.0  # Клипнут
        assert token.stress == 0.0  # Клипнут

    def test_update_from_dict_returns_self(self):
        """update_from_dict() возвращает self для chaining."""
        token = SelfToken()
        result = token.update_from_dict({"presence": 0.8})

        assert result is token


class TestSelfTokenRepr:
    """Тесты строкового представления."""

    def test_repr_contains_key_info(self):
        """__repr__ содержит ID и метрики."""
        token = SelfToken(
            token_id="test-token",
            presence=0.8,
            coherence=0.6,
            continuity=0.9,
            stress=0.2,
        )

        repr_str = repr(token)

        assert "test-token" in repr_str
        assert "0.800" in repr_str  # presence
        assert "stable" in repr_str  # status
