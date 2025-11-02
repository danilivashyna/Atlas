"""
Тесты для Atlas Homeostasis Policy Engine (E4.1).

Проверяет:
- Загрузку и валидацию YAML-политик
- Оценку простых и композитных триггеров
- Dry-run режим
- Граничные случаи (edge cases)
"""

from pathlib import Path

import pytest

from atlas.homeostasis import (
    CompositeLogic,
    CompositeTrigger,
    Operator,
    PolicyEngine,
    Priority,
    SimpleTrigger,
)


class TestSimpleTrigger:
    """Тесты для простых триггеров."""

    def test_lt_operator(self):
        """Тест оператора <."""
        trigger = SimpleTrigger(
            metric="h_coherence",
            operator=Operator.LT,
            threshold=0.78,
            duration_minutes=5,
        )

        assert trigger.evaluate(0.75) is True  # 0.75 < 0.78
        assert trigger.evaluate(0.78) is False  # 0.78 не < 0.78
        assert trigger.evaluate(0.80) is False  # 0.80 не < 0.78

    def test_gt_operator(self):
        """Тест оператора >."""
        trigger = SimpleTrigger(
            metric="h_stability_drift",
            operator=Operator.GT,
            threshold=0.08,
            duration_minutes=10,
        )

        assert trigger.evaluate(0.10) is True  # 0.10 > 0.08
        assert trigger.evaluate(0.08) is False  # 0.08 не > 0.08
        assert trigger.evaluate(0.05) is False  # 0.05 не > 0.08

    def test_le_operator(self):
        """Тест оператора <=."""
        trigger = SimpleTrigger(
            metric="latency",
            operator=Operator.LE,
            threshold=100.0,
            duration_minutes=5,
        )

        assert trigger.evaluate(90.0) is True  # 90.0 <= 100.0
        assert trigger.evaluate(100.0) is True  # 100.0 <= 100.0
        assert trigger.evaluate(110.0) is False  # 110.0 не <= 100.0

    def test_duration_all_match(self):
        """Тест duration: все значения должны соответствовать."""
        trigger = SimpleTrigger(
            metric="h_coherence",
            operator=Operator.LT,
            threshold=0.78,
            duration_minutes=5,
        )

        # Все значения ниже порога → триггер активен
        history = [0.75, 0.76, 0.77, 0.75, 0.76]
        assert trigger.evaluate(0.75, history) is True

        # Одно значение выше порога → триггер не активен
        history_mixed = [0.75, 0.79, 0.77, 0.75, 0.76]
        assert trigger.evaluate(0.75, history_mixed) is False


class TestCompositeTrigger:
    """Тесты для композитных триггеров."""

    def test_and_logic_both_true(self):
        """Тест AND: оба условия истинны."""
        trigger = CompositeTrigger(
            composite=CompositeLogic.AND,
            conditions=[
                SimpleTrigger("h_coherence", Operator.LT, 0.78, 5),
                SimpleTrigger("h_stability_drift", Operator.GT, 0.08, 5),
            ],
        )

        metrics = {
            "h_coherence": 0.75,  # < 0.78 ✓
            "h_stability_drift": 0.10,  # > 0.08 ✓
        }
        assert trigger.evaluate(metrics) is True

    def test_and_logic_one_false(self):
        """Тест AND: одно условие ложно."""
        trigger = CompositeTrigger(
            composite=CompositeLogic.AND,
            conditions=[
                SimpleTrigger("h_coherence", Operator.LT, 0.78, 5),
                SimpleTrigger("h_stability_drift", Operator.GT, 0.08, 5),
            ],
        )

        metrics = {
            "h_coherence": 0.80,  # не < 0.78 ✗
            "h_stability_drift": 0.10,  # > 0.08 ✓
        }
        assert trigger.evaluate(metrics) is False

    def test_or_logic_one_true(self):
        """Тест OR: хотя бы одно условие истинно."""
        trigger = CompositeTrigger(
            composite=CompositeLogic.OR,
            conditions=[
                SimpleTrigger("h_coherence", Operator.LT, 0.78, 5),
                SimpleTrigger("h_stability_drift", Operator.GT, 0.08, 5),
            ],
        )

        metrics = {
            "h_coherence": 0.80,  # не < 0.78 ✗
            "h_stability_drift": 0.10,  # > 0.08 ✓
        }
        assert trigger.evaluate(metrics) is True

    def test_or_logic_all_false(self):
        """Тест OR: все условия ложны."""
        trigger = CompositeTrigger(
            composite=CompositeLogic.OR,
            conditions=[
                SimpleTrigger("h_coherence", Operator.LT, 0.78, 5),
                SimpleTrigger("h_stability_drift", Operator.GT, 0.08, 5),
            ],
        )

        metrics = {
            "h_coherence": 0.80,  # не < 0.78 ✗
            "h_stability_drift": 0.05,  # не > 0.08 ✗
        }
        assert trigger.evaluate(metrics) is False

    def test_not_logic(self):
        """Тест NOT: инверсия первого условия."""
        trigger = CompositeTrigger(
            composite=CompositeLogic.NOT,
            conditions=[
                SimpleTrigger("h_coherence", Operator.LT, 0.78, 5),
            ],
        )

        metrics_low = {"h_coherence": 0.75}  # < 0.78 → NOT → False
        assert trigger.evaluate(metrics_low) is False

        metrics_high = {"h_coherence": 0.80}  # не < 0.78 → NOT → True
        assert trigger.evaluate(metrics_high) is True


class TestPolicyEngine:
    """Тесты для Policy Engine."""

    @pytest.fixture
    def minimal_config(self, tmp_path: Path) -> Path:
        """Создать минимальную конфигурацию."""
        config = """
version: "1.0"
enabled: true

policies:
  - name: test_low_coherence
    description: "Test policy"
    priority: high
    enabled: true
    
    trigger:
      metric: h_coherence_sent_to_para
      operator: "<"
      threshold: 0.78
      duration_minutes: 5
      
    action:
      type: rebuild_shard
      params:
        level: sentence
      max_per_window: 2
      cooldown_minutes: 15
"""
        config_path = tmp_path / "homeostasis.yaml"
        config_path.write_text(config)
        return config_path

    def test_load_config(self, minimal_config: Path):
        """Тест загрузки конфигурации."""
        engine = PolicyEngine(config_path=minimal_config)

        assert len(engine.policies) == 1
        assert engine.policies[0].name == "test_low_coherence"
        assert engine.policies[0].priority == Priority.HIGH
        assert engine.policies[0].enabled is True

    def test_evaluate_policies_triggered(self, minimal_config: Path):
        """Тест оценки политик: триггер сработал."""
        engine = PolicyEngine(config_path=minimal_config)

        metrics = {"h_coherence_sent_to_para": 0.75}  # < 0.78
        results = engine.evaluate_policies(metrics)

        assert len(results) == 1
        assert results[0].triggered is True
        assert "h_coherence_sent_to_para" in results[0].reason

    def test_evaluate_policies_not_triggered(self, minimal_config: Path):
        """Тест оценки политик: триггер не сработал."""
        engine = PolicyEngine(config_path=minimal_config)

        metrics = {"h_coherence_sent_to_para": 0.85}  # не < 0.78
        results = engine.evaluate_policies(metrics)

        assert len(results) == 0

    def test_dry_run_mode(self, minimal_config: Path):
        """Тест dry-run режима."""
        engine = PolicyEngine(config_path=minimal_config, dry_run=True)

        metrics = {"h_coherence_sent_to_para": 0.75}
        results = engine.evaluate_policies(metrics)

        assert len(results) == 1
        assert results[0].dry_run is True

    def test_priority_sorting(self, tmp_path: Path):
        """Тест сортировки по приоритету."""
        config = """
version: "1.0"
enabled: true

policies:
  - name: medium_policy
    priority: medium
    enabled: true
    trigger:
      metric: test
      operator: ">"
      threshold: 0.5
      duration_minutes: 1
    action:
      type: test_action
      
  - name: critical_policy
    priority: critical
    enabled: true
    trigger:
      metric: test
      operator: ">"
      threshold: 0.5
      duration_minutes: 1
    action:
      type: test_action
      
  - name: low_policy
    priority: low
    enabled: true
    trigger:
      metric: test
      operator: ">"
      threshold: 0.5
      duration_minutes: 1
    action:
      type: test_action
"""
        config_path = tmp_path / "homeostasis.yaml"
        config_path.write_text(config)

        engine = PolicyEngine(config_path=config_path)

        # Политики должны быть отсортированы: critical, medium, low
        assert engine.policies[0].name == "critical_policy"
        assert engine.policies[1].name == "medium_policy"
        assert engine.policies[2].name == "low_policy"

    def test_disabled_policy_not_evaluated(self, tmp_path: Path):
        """Тест: выключенные политики не оцениваются."""
        config = """
version: "1.0"
enabled: true

policies:
  - name: disabled_policy
    priority: high
    enabled: false
    trigger:
      metric: test
      operator: ">"
      threshold: 0.5
      duration_minutes: 1
    action:
      type: test_action
"""
        config_path = tmp_path / "homeostasis.yaml"
        config_path.write_text(config)

        engine = PolicyEngine(config_path=config_path)

        metrics = {"test": 0.8}  # должен был сработать, но политика выключена
        results = engine.evaluate_policies(metrics)

        assert len(results) == 0

    def test_evaluate_limit(self, tmp_path: Path):
        """Тест лимита на количество сработавших политик."""
        config = """
version: "1.0"
enabled: true

policies:
  - name: policy1
    priority: high
    enabled: true
    trigger:
      metric: test
      operator: ">"
      threshold: 0.5
      duration_minutes: 1
    action:
      type: test_action
      
  - name: policy2
    priority: high
    enabled: true
    trigger:
      metric: test
      operator: ">"
      threshold: 0.5
      duration_minutes: 1
    action:
      type: test_action
      
  - name: policy3
    priority: high
    enabled: true
    trigger:
      metric: test
      operator: ">"
      threshold: 0.5
      duration_minutes: 1
    action:
      type: test_action
"""
        config_path = tmp_path / "homeostasis.yaml"
        config_path.write_text(config)

        engine = PolicyEngine(config_path=config_path)

        metrics = {"test": 0.8}  # все 3 политики должны сработать
        results = engine.evaluate_policies(metrics, limit=2)

        # Но лимит = 2
        assert len(results) == 2


class TestEdgeCases:
    """Тесты граничных случаев."""

    def test_missing_metric(self, tmp_path: Path):
        """Тест: метрика отсутствует в данных."""
        config = """
version: "1.0"
enabled: true

policies:
  - name: test_policy
    priority: high
    enabled: true
    trigger:
      metric: missing_metric
      operator: "<"
      threshold: 0.5
      duration_minutes: 1
    action:
      type: test_action
"""
        config_path = tmp_path / "homeostasis.yaml"
        config_path.write_text(config)

        engine = PolicyEngine(config_path=config_path)

        metrics = {"other_metric": 0.8}  # missing_metric отсутствует
        results = engine.evaluate_policies(metrics)

        # Триггер не должен сработать
        assert len(results) == 0

    def test_threshold_boundary(self, tmp_path: Path):
        """Тест граничного значения threshold."""
        config = """
version: "1.0"
enabled: true

policies:
  - name: test_boundary
    priority: high
    enabled: true
    trigger:
      metric: test
      operator: "<"
      threshold: 0.78
      duration_minutes: 1
    action:
      type: test_action
"""
        config_path = tmp_path / "homeostasis.yaml"
        config_path.write_text(config)

        engine = PolicyEngine(config_path=config_path)

        # Точно на границе
        metrics_equal = {"test": 0.78}
        results_equal = engine.evaluate_policies(metrics_equal)
        assert len(results_equal) == 0  # 0.78 не < 0.78

        # Чуть ниже
        metrics_below = {"test": 0.7799999}
        results_below = engine.evaluate_policies(metrics_below)
        assert len(results_below) == 1  # 0.7799999 < 0.78
