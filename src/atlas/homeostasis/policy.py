"""
Atlas Homeostasis Policy Engine

Загружает и валидирует политики гомеостаза из YAML,
оценивает триггеры на основе метрик E3, возвращает
рекомендуемые действия с учётом приоритетов и лимитов.

Архитектурная роль:
- E3 (Self-awareness): Метрики осознанности (H-Coherence, H-Stability)
- E4.1 (Policy Engine): Правила реагирования на метрики → E4.2 (Decision Engine)
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import jsonschema
import yaml


class Priority(str, Enum):
    """Приоритет политики."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    def compare(self, other: "Priority") -> int:
        """
        Сравнение приоритетов для сортировки.

        Returns:
            <0 если self < other, 0 если равны, >0 если self > other
        """
        order = {
            Priority.CRITICAL: 0,
            Priority.HIGH: 1,
            Priority.MEDIUM: 2,
            Priority.LOW: 3,
        }
        return order[self] - order[other]


class Operator(str, Enum):
    """Операторы сравнения для триггеров."""
    LT = "<"
    LE = "<="
    GT = ">"
    GE = ">="
    EQ = "=="
    NE = "!="


class CompositeLogic(str, Enum):
    """Логика для композитных триггеров."""
    AND = "and"
    OR = "or"
    NOT = "not"


@dataclass
class SimpleTrigger:
    """Простой триггер: metric operator threshold."""

    metric: str
    operator: Operator
    threshold: float
    duration_minutes: int

    def evaluate(self, metric_value: float, metric_history: Optional[List[float]] = None) -> bool:
        """
        Оценить триггер.

        Args:
            metric_value: Текущее значение метрики
            metric_history: История значений за duration_minutes (опционально)

        Returns:
            True если триггер активен
        """
        # Простая оценка: сравнить текущее значение
        if self.operator == Operator.LT:
            current_match = metric_value < self.threshold
        elif self.operator == Operator.LE:
            current_match = metric_value <= self.threshold
        elif self.operator == Operator.GT:
            current_match = metric_value > self.threshold
        elif self.operator == Operator.GE:
            current_match = metric_value >= self.threshold
        elif self.operator == Operator.EQ:
            current_match = abs(metric_value - self.threshold) < 1e-6
        elif self.operator == Operator.NE:
            current_match = abs(metric_value - self.threshold) >= 1e-6
        else:
            return False

        # Если есть история, проверить duration
        if metric_history is not None and len(metric_history) > 0:
            # Все значения за duration должны соответствовать условию
            if self.operator == Operator.LT:
                return all(v < self.threshold for v in metric_history)
            elif self.operator == Operator.LE:
                return all(v <= self.threshold for v in metric_history)
            elif self.operator == Operator.GT:
                return all(v > self.threshold for v in metric_history)
            elif self.operator == Operator.GE:
                return all(v >= self.threshold for v in metric_history)
            elif self.operator == Operator.EQ:
                return all(abs(v - self.threshold) < 1e-6 for v in metric_history)
            elif self.operator == Operator.NE:
                return all(abs(v - self.threshold) >= 1e-6 for v in metric_history)

        return current_match


@dataclass
class CompositeTrigger:
    """Композитный триггер: AND/OR/NOT над простыми триггерами."""

    composite: CompositeLogic
    conditions: List[SimpleTrigger]

    def evaluate(self, metrics: Dict[str, float]) -> bool:
        """
        Оценить композитный триггер.

        Args:
            metrics: Словарь {metric_name: value}

        Returns:
            True если триггер активен
        """
        results = []
        for condition in self.conditions:
            metric_value = metrics.get(condition.metric)
            if metric_value is None:
                # Метрика недоступна → триггер не активен
                results.append(False)
            else:
                results.append(condition.evaluate(metric_value))

        if self.composite == CompositeLogic.AND:
            return all(results)
        elif self.composite == CompositeLogic.OR:
            return any(results)
        elif self.composite == CompositeLogic.NOT:
            # NOT применяется к первому условию
            return not results[0] if results else False

        return False


@dataclass
class Action:
    """Действие, которое нужно выполнить при срабатывании триггера."""

    action_type: str  # rebuild_shard, reembed_batch, etc.
    params: Dict[str, Any] = field(default_factory=dict)
    max_per_window: int = 1
    cooldown_minutes: int = 15


@dataclass
class SuccessCriteria:
    """Критерий успешности действия."""

    metric: str
    improvement_min: Optional[float] = None
    value_max: Optional[float] = None
    value_min: Optional[float] = None


@dataclass
class Policy:
    """Политика гомеостаза."""

    name: str
    description: str
    priority: Priority
    enabled: bool
    trigger: Union[SimpleTrigger, CompositeTrigger]
    action: Action
    success_criteria: Optional[Union[SuccessCriteria, CompositeTrigger]] = None

    def evaluate(self, metrics: Dict[str, float]) -> bool:
        """
        Оценить политику.

        Args:
            metrics: Текущие значения метрик

        Returns:
            True если триггер активен
        """
        if not self.enabled:
            return False

        if isinstance(self.trigger, SimpleTrigger):
            metric_value = metrics.get(self.trigger.metric)
            if metric_value is None:
                return False
            return self.trigger.evaluate(metric_value)
        elif isinstance(self.trigger, CompositeTrigger):
            return self.trigger.evaluate(metrics)

        return False


@dataclass
class PolicyEvaluationResult:
    """Результат оценки политики."""

    policy: Policy
    triggered: bool
    reason: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    dry_run: bool = False


class PolicyEngine:
    """
    Policy Engine для контура гомеостаза.

    Загружает политики из YAML, валидирует через JSON Schema,
    оценивает триггеры на основе метрик E3.
    """

    def __init__(
        self,
        config_path: Path,
        schema_path: Optional[Path] = None,
        dry_run: bool = False,
    ):
        """
        Args:
            config_path: Путь к homeostasis.yaml
            schema_path: Путь к JSON Schema (опционально)
            dry_run: Режим симуляции (не выполнять действия)
        """
        self.config_path = config_path
        self.schema_path = schema_path
        self.dry_run = dry_run

        self.policies: List[Policy] = []
        self.global_limits: Dict[str, Any] = {}
        self.safety_config: Dict[str, Any] = {}

        self._load_config()

    def _load_config(self) -> None:
        """Загрузить и валидировать конфигурацию."""
        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Валидация через JSON Schema (если указан)
        if self.schema_path:
            with open(self.schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
            jsonschema.validate(instance=config, schema=schema)

        # Проверка версии
        version = config.get("version", "1.0")
        if not version.startswith("1."):
            raise ValueError(f"Unsupported policy version: {version}")

        # Глобальные настройки
        self.global_limits = config.get("global_limits", {})
        self.safety_config = config.get("safety", {})

        # Dry-run режим (из конфига или конструктора)
        if "dry_run" in self.global_limits:
            self.dry_run = self.global_limits["dry_run"] or self.dry_run

        # Парсинг политик
        for policy_dict in config.get("policies", []):
            policy = self._parse_policy(policy_dict)
            self.policies.append(policy)

        # Сортировка по приоритету (critical → high → medium → low)
        self.policies.sort(key=lambda p: p.priority.compare(Priority.CRITICAL))

    def _parse_policy(self, policy_dict: Dict[str, Any]) -> Policy:
        """Распарсить политику из словаря."""
        # Trigger
        trigger_dict = policy_dict["trigger"]
        if "composite" in trigger_dict:
            # Композитный триггер
            conditions = [
                SimpleTrigger(
                    metric=c["metric"],
                    operator=Operator(c["operator"]),
                    threshold=c["threshold"],
                    duration_minutes=c.get("duration_minutes", 0),
                )
                for c in trigger_dict["conditions"]
            ]
            trigger = CompositeTrigger(
                composite=CompositeLogic(trigger_dict["composite"]),
                conditions=conditions,
            )
        else:
            # Простой триггер
            trigger = SimpleTrigger(
                metric=trigger_dict["metric"],
                operator=Operator(trigger_dict["operator"]),
                threshold=trigger_dict["threshold"],
                duration_minutes=trigger_dict.get("duration_minutes", 0),
            )

        # Action
        action_dict = policy_dict["action"]
        action = Action(
            action_type=action_dict["type"],
            params=action_dict.get("params", {}),
            max_per_window=action_dict.get("max_per_window", 1),
            cooldown_minutes=action_dict.get("cooldown_minutes", 15),
        )

        # Success criteria (опционально)
        success_criteria = None
        if "success_criteria" in policy_dict:
            sc_dict = policy_dict["success_criteria"]
            if "composite" in sc_dict:
                # Композитный критерий (пока не реализован)
                pass
            else:
                success_criteria = SuccessCriteria(
                    metric=sc_dict["metric"],
                    improvement_min=sc_dict.get("improvement_min"),
                    value_max=sc_dict.get("value_max"),
                    value_min=sc_dict.get("value_min"),
                )

        return Policy(
            name=policy_dict["name"],
            description=policy_dict.get("description", ""),
            priority=Priority(policy_dict["priority"]),
            enabled=policy_dict.get("enabled", True),
            trigger=trigger,
            action=action,
            success_criteria=success_criteria,
        )

    def evaluate_policies(
        self,
        metrics: Dict[str, float],
        limit: Optional[int] = None,
    ) -> List[PolicyEvaluationResult]:
        """
        Оценить все политики на основе текущих метрик.

        Args:
            metrics: Словарь {metric_name: value}
            limit: Максимальное количество сработавших политик (None = без лимита)

        Returns:
            Список результатов оценки (отсортированы по приоритету)
        """
        results = []

        for policy in self.policies:
            triggered = policy.evaluate(metrics)

            if triggered:
                # Определить причину срабатывания
                if isinstance(policy.trigger, SimpleTrigger):
                    metric_value = metrics.get(policy.trigger.metric, 0.0)
                    reason = (
                        f"{policy.trigger.metric} = {metric_value:.4f} "
                        f"{policy.trigger.operator.value} {policy.trigger.threshold}"
                    )
                else:
                    reason = f"Composite trigger: {policy.trigger.composite.value}"

                result = PolicyEvaluationResult(
                    policy=policy,
                    triggered=True,
                    reason=reason,
                    dry_run=self.dry_run,
                )
                results.append(result)

                # Лимит на количество сработавших политик
                if limit and len(results) >= limit:
                    break

        return results

    def get_policy_by_name(self, name: str) -> Optional[Policy]:
        """Получить политику по имени."""
        for policy in self.policies:
            if policy.name == name:
                return policy
        return None

    def validate_config(self) -> bool:
        """
        Валидировать конфигурацию без загрузки.

        Returns:
            True если конфигурация валидна
        """
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if self.schema_path:
                with open(self.schema_path, "r", encoding="utf-8") as f:
                    schema = json.load(f)
                jsonschema.validate(instance=config, schema=schema)

            return True
        except (OSError, yaml.YAMLError, jsonschema.ValidationError) as e:
            print(f"Validation error: {e}")
            return False
