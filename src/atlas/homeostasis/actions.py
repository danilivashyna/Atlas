"""
Atlas Homeostasis Action Adapters (Beta)

Выполняет действия, рекомендованные DecisionEngine.
Beta-версия: заглушки с правильными интерфейсами.
Полная интеграция с E2 builders отложена до FAB.

Архитектурная роль:
- E4.2 (Decision Engine): Решения → E4.3 (Action Adapters) → результаты
- E2 (Vocabulary): (Future) Реальная перестройка индексов

⚠️ Beta constraints:
- Заглушки вместо реальных действий
- Pre-checks + result tracking
- Dry-run support
- Логирование всех операций
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from atlas.homeostasis.policy import Action


class ActionStatus(str, Enum):
    """Статус выполнения действия."""
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"
    DRY_RUN = "dry_run"


@dataclass
class ActionResult:
    """
    Результат выполнения действия.
    
    Attributes:
        action_type: Тип действия
        status: Статус выполнения
        duration_seconds: Длительность выполнения
        message: Сообщение о результате
        metrics_before: Метрики до выполнения
        metrics_after: Метрики после выполнения (если success)
        error: Текст ошибки (если failure)
    """
    action_type: str
    status: ActionStatus
    duration_seconds: float
    message: str
    metrics_before: Optional[Dict[str, float]] = None
    metrics_after: Optional[Dict[str, float]] = None
    error: Optional[str] = None


class ActionAdapter:
    """
    Базовый адаптер для действий гомеостаза.
    
    Beta-версия: заглушки с логированием.
    Полная имплементация в FAB.
    """
    
    def __init__(
        self,
        data_dir: Optional[Path] = None,
        dry_run: bool = False,
    ):
        """
        Инициализация адаптера.
        
        Args:
            data_dir: Директория данных (indices, MANIFEST)
            dry_run: Режим имитации (не выполнять действия)
        """
        self.data_dir = data_dir or Path("data")
        self.dry_run = dry_run
        self.execution_log: List[ActionResult] = []
    
    def execute(self, action: Action, metrics: Dict[str, float]) -> ActionResult:
        """
        Выполнить действие.
        
        Args:
            action: Действие из DecisionEngine
            metrics: Текущие метрики (для pre-checks)
        
        Returns:
            ActionResult с результатом выполнения
        
        Notes:
            - Pre-check перед выполнением
            - Dry-run если self.dry_run=True
            - Логирование результата
        """
        start_time = datetime.now(timezone.utc)
        
        # Pre-check
        precheck_ok, precheck_msg = self._pre_check(action, metrics)
        if not precheck_ok:
            result = ActionResult(
                action_type=action.action_type,
                status=ActionStatus.SKIPPED,
                duration_seconds=0.0,
                message=f"Pre-check failed: {precheck_msg}",
                metrics_before=metrics,
            )
            self.execution_log.append(result)
            return result
        
        # Dry-run mode
        if self.dry_run:
            result = ActionResult(
                action_type=action.action_type,
                status=ActionStatus.DRY_RUN,
                duration_seconds=0.0,
                message=f"Dry-run: would execute {action.action_type}",
                metrics_before=metrics,
            )
            self.execution_log.append(result)
            return result
        
        # Dispatch к специфическому обработчику
        try:
            if action.action_type == "rebuild_shard":
                result = self._rebuild_shard(action, metrics, start_time)
            elif action.action_type == "reembed_batch":
                result = self._reembed_batch(action, metrics, start_time)
            elif action.action_type == "tune_search_params":
                result = self._tune_search_params(action, metrics, start_time)
            elif action.action_type == "quarantine_docs":
                result = self._quarantine_docs(action, metrics, start_time)
            elif action.action_type == "regenerate_manifest":
                result = self._regenerate_manifest(action, metrics, start_time)
            else:
                raise ValueError(f"Unknown action type: {action.action_type}")
        except (ValueError, OSError, RuntimeError) as e:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            result = ActionResult(
                action_type=action.action_type,
                status=ActionStatus.FAILURE,
                duration_seconds=duration,
                message=f"Action failed: {action.action_type}",
                metrics_before=metrics,
                error=str(e),
            )
        
        self.execution_log.append(result)
        return result
    
    def _pre_check(self, action: Action, _metrics: Dict[str, float]) -> tuple[bool, str]:
        """
        Pre-check перед выполнением действия.
        
        Returns:
            (ok, message) — True если можно выполнять
        """
        # Проверка наличия данных
        if not self.data_dir.exists():
            return False, f"Data directory not found: {self.data_dir}"
        
        # Проверка специфичных условий для каждого типа
        if action.action_type == "rebuild_shard":
            level = action.params.get("level")
            if not level:
                return False, "Missing parameter: level"
            if level not in ["sentence", "paragraph", "document"]:
                return False, f"Invalid level: {level}"
        
        elif action.action_type == "reembed_batch":
            batch_size = action.params.get("batch_size", 100)
            if batch_size <= 0:
                return False, f"Invalid batch_size: {batch_size}"
        
        elif action.action_type == "tune_search_params":
            # Проверка наличия параметров для тюнинга
            if not action.params:
                return False, "Missing search parameters"
        
        return True, "OK"
    
    def _rebuild_shard(
        self,
        action: Action,
        metrics: Dict[str, float],
        start_time: datetime,
    ) -> ActionResult:
        """
        Rebuild shard (beta stub).
        
        Notes:
            Beta: заглушка, возвращает success.
            FAB: интеграция с HNSWIndexBuilder/FAISSIndexBuilder.
        """
        level = action.params.get("level", "unknown")
        
        # Beta stub: simulate success
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        return ActionResult(
            action_type="rebuild_shard",
            status=ActionStatus.SUCCESS,
            duration_seconds=duration,
            message=f"Beta stub: rebuild_shard for {level} completed",
            metrics_before=metrics,
            metrics_after=metrics,  # Beta: no real changes
        )
    
    def _reembed_batch(
        self,
        action: Action,
        metrics: Dict[str, float],
        start_time: datetime,
    ) -> ActionResult:
        """
        Re-embed batch of documents (beta stub).
        
        Notes:
            Beta: заглушка, возвращает success.
            FAB: интеграция с encoder.
        """
        batch_size = action.params.get("batch_size", 100)
        
        # Beta stub: simulate success
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        return ActionResult(
            action_type="reembed_batch",
            status=ActionStatus.SUCCESS,
            duration_seconds=duration,
            message=f"Beta stub: reembed_batch ({batch_size} docs) completed",
            metrics_before=metrics,
            metrics_after=metrics,  # Beta: no real changes
        )
    
    def _tune_search_params(
        self,
        action: Action,
        metrics: Dict[str, float],
        start_time: datetime,
    ) -> ActionResult:
        """
        Tune search parameters (beta stub).
        
        Notes:
            Beta: заглушка, возвращает success.
            FAB: реальная настройка ef_search, nprobe.
        """
        params = action.params
        
        # Beta stub: simulate success
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        return ActionResult(
            action_type="tune_search_params",
            status=ActionStatus.SUCCESS,
            duration_seconds=duration,
            message=f"Beta stub: tune_search_params ({params}) completed",
            metrics_before=metrics,
            metrics_after=metrics,  # Beta: no real changes
        )
    
    def _quarantine_docs(
        self,
        action: Action,
        metrics: Dict[str, float],
        start_time: datetime,
    ) -> ActionResult:
        """
        Quarantine problematic documents (beta stub).
        
        Notes:
            Beta: заглушка, возвращает success.
            FAB: реальное исключение из индексов.
        """
        doc_ids = action.params.get("doc_ids", [])
        
        # Beta stub: simulate success
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        return ActionResult(
            action_type="quarantine_docs",
            status=ActionStatus.SUCCESS,
            duration_seconds=duration,
            message=f"Beta stub: quarantine_docs ({len(doc_ids)} docs) completed",
            metrics_before=metrics,
            metrics_after=metrics,  # Beta: no real changes
        )
    
    def _regenerate_manifest(
        self,
        _action: Action,
        metrics: Dict[str, float],
        start_time: datetime,
    ) -> ActionResult:
        """
        Regenerate MANIFEST (beta stub).
        
        Notes:
            Beta: заглушка, возвращает success.
            FAB: интеграция с MANIFESTGenerator.
        """
        # Beta stub: simulate success
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        return ActionResult(
            action_type="regenerate_manifest",
            status=ActionStatus.SUCCESS,
            duration_seconds=duration,
            message="Beta stub: regenerate_manifest completed",
            metrics_before=metrics,
            metrics_after=metrics,  # Beta: no real changes
        )
    
    def get_execution_log(self, limit: Optional[int] = None) -> List[ActionResult]:
        """
        Получить лог выполненных действий.
        
        Args:
            limit: Ограничение на количество записей
        
        Returns:
            Список ActionResult
        """
        if limit:
            return self.execution_log[-limit:]
        return self.execution_log
    
    def clear_log(self):
        """Очистка лога (для тестов)."""
        self.execution_log.clear()
