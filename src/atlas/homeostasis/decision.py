"""
Atlas Homeostasis Decision Engine

Принимает решения на основе сработавших политик E4.1,
применяет anti-flapping, rate-limits, priority resolution.
Интегрируется напрямую с метриками E3 (HCoherenceMetric, HStabilityMetric).

Архитектурная роль:
- E3 (Self-awareness): Метрики осознанности
- E4.1 (Policy Engine): Сработавшие политики → E4.2 (Decision Engine) → E4.3 (Actions)

Детерминизм: одни и те же метрики + политики → одно решение (для воспроизводимости).
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from atlas.homeostasis.policy import (
    Action,
    PolicyEngine,
    PolicyEvaluationResult,
    Priority,
)
from atlas.metrics import HCoherenceMetric, HStabilityMetric


@dataclass
class ActionDecision:
    """
    Решение о выполнении действия.

    Attributes:
        action: Действие из политики
        policy_name: Имя сработавшей политики
        priority: Приоритет политики
        reason: Причина принятия решения (триггер)
        scheduled_at: Время запланированного выполнения
        run_id: Уникальный идентификатор прогона
        decision_id: Уникальный идентификатор решения (для WAL)
    """
    action: Action
    policy_name: str
    priority: Priority
    reason: str
    scheduled_at: datetime
    run_id: str
    decision_id: str


@dataclass
class CooldownEntry:
    """
    Запись о времени последнего выполнения действия.

    Attributes:
        action_type: Тип действия (rebuild_shard, reembed_batch, и т.д.)
        action_params: Параметры действия (для уникальности)
        last_execution: Время последнего выполнения
        cooldown_until: Время окончания cooldown
    """
    action_type: str
    action_params: Dict[str, Any]
    last_execution: datetime
    cooldown_until: datetime


@dataclass
class RateLimitWindow:
    """
    Окно rate-limit для контроля частоты действий.

    Attributes:
        window_start: Начало окна
        window_duration: Длительность окна (мин)
        max_actions: Максимум действий в окне
        executed_count: Сколько уже выполнено
    """
    window_start: datetime
    window_duration: int
    max_actions: int
    executed_count: int = 0


class DecisionEngine:
    """
    Decision Engine для гомеостаза.

    Функции:
    - Получение метрик от E3 (HCoherenceMetric, HStabilityMetric)
    - Оценка политик через PolicyEngine
    - Anti-flapping: отслеживание cooldown между действиями
    - Rate-limits: ограничение количества действий в единицу времени
    - Priority resolution: когда несколько политик конфликтуют
    - Детерминизм: одинаковые входы → одинаковый выход

    ⚠️ Safety:
    - Dry-run mode для тестирования без выполнения
    - Limits по умолчанию: max_actions_per_hour=10, max_concurrent=2
    - Cooldown tracking для предотвращения флаппинга
    - Приоритетное разрешение конфликтов (critical > high > medium > low)
    """

    def __init__(
        self,
        policy_config_path: Path,
        state_dir: Optional[Path] = None,
        dry_run: bool = False,
        seed: Optional[int] = None,
    ):
        """
        Инициализация Decision Engine.

        Args:
            policy_config_path: Путь к YAML конфигу политик
            state_dir: Директория для хранения состояния (cooldowns, rate-limits)
            dry_run: Режим имитации (не меняет состояние)
            seed: Seed для детерминизма (для тестов)
        """
        self.policy_engine = PolicyEngine(policy_config_path, dry_run=dry_run)
        self.state_dir = state_dir or Path("data/homeostasis/state")
        self.dry_run = dry_run
        self.seed = seed

        # Metrics от E3
        self.h_coherence_metric = HCoherenceMetric()
        self.h_stability_metric = HStabilityMetric()

        # State tracking
        self.cooldowns: Dict[str, CooldownEntry] = {}
        self.rate_limits: Dict[str, RateLimitWindow] = {}
        self.execution_history: List[ActionDecision] = []

        # Global limits из конфига PolicyEngine
        self.global_limits = self.policy_engine.global_limits
        self.max_actions_per_hour = self.global_limits.get("max_actions_per_hour", 10)
        self.max_concurrent = self.global_limits.get("max_concurrent", 2)
        self.default_cooldown_minutes = self.global_limits.get("default_cooldown_minutes", 15)

        # Load state если не dry-run
        if not dry_run:
            self._load_state()

    def _load_state(self):
        """Загрузка состояния cooldowns и rate-limits из файла."""
        state_file = self.state_dir / "decision_state.json"
        if not state_file.exists():
            return

        with state_file.open("r", encoding="utf-8") as f:
            state = json.load(f)

        # Restore cooldowns
        for key, entry in state.get("cooldowns", {}).items():
            self.cooldowns[key] = CooldownEntry(
                action_type=entry["action_type"],
                action_params=entry["action_params"],
                last_execution=datetime.fromisoformat(entry["last_execution"]),
                cooldown_until=datetime.fromisoformat(entry["cooldown_until"]),
            )

        # Restore rate-limits
        for key, window in state.get("rate_limits", {}).items():
            self.rate_limits[key] = RateLimitWindow(
                window_start=datetime.fromisoformat(window["window_start"]),
                window_duration=window["window_duration"],
                max_actions=window["max_actions"],
                executed_count=window["executed_count"],
            )

    def _save_state(self):
        """Сохранение состояния cooldowns и rate-limits в файл."""
        if self.dry_run:
            return

        self.state_dir.mkdir(parents=True, exist_ok=True)
        state_file = self.state_dir / "decision_state.json"

        state = {
            "cooldowns": {
                key: {
                    "action_type": entry.action_type,
                    "action_params": entry.action_params,
                    "last_execution": entry.last_execution.isoformat(),
                    "cooldown_until": entry.cooldown_until.isoformat(),
                }
                for key, entry in self.cooldowns.items()
            },
            "rate_limits": {
                key: {
                    "window_start": window.window_start.isoformat(),
                    "window_duration": window.window_duration,
                    "max_actions": window.max_actions,
                    "executed_count": window.executed_count,
                }
                for key, window in self.rate_limits.items()
            },
        }

        with state_file.open("w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def collect_metrics(self) -> Dict[str, float]:
        """
        Собрать текущие метрики от E3.

        Returns:
            Dict с метриками для оценки политик

        Notes:
            В реальной системе будет читать из Prometheus/памяти.
            Здесь — заглушка для тестирования.
        """
        # NOTE: В production версии — читать из app.state.metrics или Prometheus
        # Сейчас возвращаем пустой dict (метрики будут переданы извне)
        return {}

    def _generate_run_id(self, timestamp: datetime) -> str:
        """Генерация уникального run_id для прогона."""
        date_str = timestamp.strftime("%Y%m%d_%H%M%S")
        return f"{date_str}_homeostasis"

    def _generate_decision_id(self, policy_name: str, action: Action, timestamp: datetime) -> str:
        """Генерация уникального decision_id для решения (для WAL)."""
        # Хеш от policy_name + action_type + params + timestamp
        content = f"{policy_name}_{action.action_type}_{json.dumps(action.params, sort_keys=True)}_{timestamp.isoformat()}"
        hash_hex = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"{action.action_type}_{hash_hex}"

    def _get_cooldown_key(self, action: Action) -> str:
        """Генерация ключа для cooldown tracking."""
        # Ключ = action_type + sorted params (для уникальности)
        params_str = json.dumps(action.params, sort_keys=True)
        return f"{action.action_type}_{params_str}"

    def _is_in_cooldown(self, action: Action, now: datetime) -> bool:
        """Проверка, находится ли действие в cooldown."""
        key = self._get_cooldown_key(action)
        if key not in self.cooldowns:
            return False

        entry = self.cooldowns[key]
        return now < entry.cooldown_until

    def _update_cooldown(self, action: Action, now: datetime):
        """Обновление cooldown для действия."""
        key = self._get_cooldown_key(action)
        cooldown_minutes = action.cooldown_minutes or self.default_cooldown_minutes

        self.cooldowns[key] = CooldownEntry(
            action_type=action.action_type,
            action_params=action.params,
            last_execution=now,
            cooldown_until=now + timedelta(minutes=cooldown_minutes),
        )

    def _check_rate_limit(self, now: datetime) -> bool:
        """
        Проверка rate-limit (не превышен ли лимит действий в час).

        Returns:
            True если можно выполнять действия, False если лимит исчерпан
        """
        window_key = "global_hourly"

        # Создать окно если не существует или истекло
        if window_key not in self.rate_limits:
            self.rate_limits[window_key] = RateLimitWindow(
                window_start=now,
                window_duration=60,  # 60 минут
                max_actions=self.max_actions_per_hour,
                executed_count=0,
            )

        window = self.rate_limits[window_key]

        # Сбросить окно если истекло
        if now >= window.window_start + timedelta(minutes=window.window_duration):
            window.window_start = now
            window.executed_count = 0

        # Проверить лимит
        return window.executed_count < window.max_actions

    def _increment_rate_limit(self):
        """Инкремент счётчика rate-limit."""
        window_key = "global_hourly"
        if window_key in self.rate_limits:
            self.rate_limits[window_key].executed_count += 1

    def _resolve_conflicts(self, triggered_policies: List[PolicyEvaluationResult]) -> List[PolicyEvaluationResult]:
        """
        Разрешение конфликтов между политиками.

        Args:
            triggered_policies: Список сработавших политик

        Returns:
            Отфильтрованный список политик без конфликтов

        Notes:
            - Приоритет: critical > high > medium > low
            - Если несколько политик одного приоритета — берём первую (детерминизм)
            - Если политики касаются одного ресурса — берём высший приоритет
        """
        # Сортировка по приоритету (critical → low)
        sorted_policies = sorted(
            triggered_policies,
            key=lambda p: p.policy.priority.compare(Priority.CRITICAL)
        )

        # Отслеживание занятых ресурсов
        occupied_resources: Set[str] = set()
        resolved: List[PolicyEvaluationResult] = []

        for policy_result in sorted_policies:
            action = policy_result.policy.action
            resource_key = self._get_resource_key(action)

            # Если ресурс уже занят — skip (приоритетное разрешение)
            if resource_key in occupied_resources:
                continue

            resolved.append(policy_result)
            occupied_resources.add(resource_key)

        return resolved

    def _get_resource_key(self, action: Action) -> str:
        """
        Определение ключа ресурса для конфликтов.

        Notes:
            - rebuild_shard → "shard:{level}"
            - reembed_batch → "embeddings:{level}"
            - tune_search_params → "search_params"
            - quarantine_docs → "quarantine"
            - regenerate_manifest → "manifest"
        """
        action_type = action.action_type
        params = action.params

        if action_type == "rebuild_shard":
            level = params.get("level", "unknown")
            return f"shard:{level}"
        elif action_type == "reembed_batch":
            level = params.get("level", "unknown")
            return f"embeddings:{level}"
        elif action_type == "tune_search_params":
            return "search_params"
        elif action_type == "quarantine_docs":
            return "quarantine"
        elif action_type == "regenerate_manifest":
            return "manifest"
        else:
            return f"action:{action_type}"

    def make_decisions(
        self,
        metrics: Dict[str, float],
        timestamp: Optional[datetime] = None,
        max_decisions: Optional[int] = None,
    ) -> List[ActionDecision]:
        """
        Принять решения на основе метрик.

        Args:
            metrics: Dict с метриками (от E3 или тестов)
            timestamp: Временная метка (для детерминизма в тестах)
            max_decisions: Ограничение на количество решений (default: max_concurrent)

        Returns:
            Список решений о действиях

        Notes:
            - Оценка политик через PolicyEngine
            - Фильтрация по cooldown
            - Фильтрация по rate-limit
            - Разрешение конфликтов по приоритету
            - Ограничение по max_concurrent

        Example:
            >>> metrics = {
            ...     "h_coherence_sent_to_para": 0.75,
            ...     "h_coherence_para_to_doc": 0.82,
            ...     "h_stability_drift": 0.05,
            ...     "search_latency_p95_ms": 85,
            ... }
            >>> decisions = engine.make_decisions(metrics)
            >>> for d in decisions:
            ...     print(f"{d.policy_name}: {d.action.action_type}")
        """
        now = timestamp or datetime.now(timezone.utc)
        max_decisions = max_decisions or self.max_concurrent

        # 1. Оценка политик
        triggered_policies = self.policy_engine.evaluate_policies(metrics)

        if not triggered_policies:
            return []

        # 2. Фильтрация по cooldown
        non_cooldown_policies = [
            p for p in triggered_policies
            if not self._is_in_cooldown(p.policy.action, now)
        ]

        # 3. Разрешение конфликтов по приоритету
        resolved_policies = self._resolve_conflicts(non_cooldown_policies)

        # 4. Проверка rate-limit
        if not self._check_rate_limit(now):
            # Rate-limit исчерпан — возвращаем пустой список
            return []

        # 5. Ограничение по max_concurrent
        selected_policies = resolved_policies[:max_decisions]

        # 6. Генерация решений
        run_id = self._generate_run_id(now)
        decisions: List[ActionDecision] = []

        for policy_result in selected_policies:
            policy = policy_result.policy
            action = policy.action

            decision = ActionDecision(
                action=action,
                policy_name=policy.name,
                priority=policy.priority,
                reason=policy_result.reason,
                scheduled_at=now,
                run_id=run_id,
                decision_id=self._generate_decision_id(policy.name, action, now),
            )

            decisions.append(decision)

            # Обновить cooldown и rate-limit
            self._update_cooldown(action, now)
            self._increment_rate_limit()

        # 7. Сохранение состояния
        self._save_state()

        # 8. Запись в историю
        self.execution_history.extend(decisions)

        return decisions

    def get_execution_history(
        self,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[ActionDecision]:
        """
        Получить историю выполненных решений.

        Args:
            since: Фильтр по времени (только решения после этой даты)
            limit: Ограничение на количество записей

        Returns:
            Список решений
        """
        history = self.execution_history

        if since:
            history = [d for d in history if d.scheduled_at >= since]

        if limit:
            history = history[-limit:]

        return history

    def clear_cooldowns(self):
        """Очистка всех cooldown (для тестирования)."""
        self.cooldowns.clear()
        self._save_state()

    def reset_rate_limits(self):
        """Сброс rate-limits (для тестирования)."""
        self.rate_limits.clear()
        self._save_state()
