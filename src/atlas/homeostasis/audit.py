"""
Atlas Homeostasis Audit Logger & WAL (Beta)

Write-Ahead Log для идемпотентности и прозрачности.
JSONL формат: одна строка = одна операция.

Архитектурная роль:
- E4.2 (Decision): Решения → E4.5 (Audit) ← E4.3 (Actions): Результаты
- Замыкание цикла: Observe → Decide → Act → Reflect (Audit) → Observe

⚠️ Beta constraints:
- JSONL файл (не PostgreSQL)
- Базовая фильтрация по времени/статусу
- Полная версия (с DB) отложена до FAB
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from atlas.homeostasis.actions import ActionResult, ActionStatus
from atlas.homeostasis.decision import ActionDecision
from atlas.homeostasis.policy import Priority


class AuditEventType(str, Enum):
    """Тип события в аудите."""
    POLICY_TRIGGERED = "policy_triggered"
    DECISION_MADE = "decision_made"
    ACTION_STARTED = "action_started"
    ACTION_COMPLETED = "action_completed"
    ACTION_FAILED = "action_failed"
    ACTION_SKIPPED = "action_skipped"


@dataclass
class AuditEvent:
    """
    Событие в аудите.
    
    Attributes:
        run_id: ID прогона (связывает цепочку событий)
        event_type: Тип события
        timestamp: Время события
        policy_name: Имя политики (если применимо)
        decision_id: ID решения (если применимо)
        action_type: Тип действия (если применимо)
        priority: Приоритет (если применимо)
        trigger_reason: Причина срабатывания
        metrics: Метрики на момент события
        result_status: Статус результата (если action_completed/failed)
        duration_seconds: Длительность (если action_completed/failed)
        error_message: Сообщение об ошибке (если failed)
        metadata: Дополнительная информация
    """
    run_id: str
    event_type: AuditEventType
    timestamp: datetime
    policy_name: Optional[str] = None
    decision_id: Optional[str] = None
    action_type: Optional[str] = None
    priority: Optional[str] = None
    trigger_reason: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None
    result_status: Optional[str] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AuditLogger:
    """
    Audit Logger для homeostasis loop.
    
    JSONL формат (одна строка = одно событие):
    - Reason → Policy triggered
    - Policy → Decision made
    - Decision → Action started
    - Action → Action completed/failed/skipped
    
    Beta-версия: файловый WAL, простые фильтры.
    """
    
    def __init__(
        self,
        log_dir: Optional[Path] = None,
        max_file_size_mb: int = 100,
    ):
        """
        Инициализация Audit Logger.
        
        Args:
            log_dir: Директория для WAL файлов
            max_file_size_mb: Максимальный размер файла (для ротации)
        """
        self.log_dir = log_dir or Path("data/homeostasis/audit")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        
        # Текущий WAL файл
        self.current_log_file = self._get_current_log_file()
    
    def _get_current_log_file(self) -> Path:
        """Получить текущий WAL файл (или создать новый)."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = self.log_dir / f"audit_{today}.jsonl"
        
        # Проверка размера файла для ротации
        if log_file.exists() and log_file.stat().st_size > self.max_file_size_bytes:
            # Ротация: переименовать в _N.jsonl
            counter = 1
            while True:
                rotated_file = self.log_dir / f"audit_{today}_{counter}.jsonl"
                if not rotated_file.exists():
                    log_file.rename(rotated_file)
                    break
                counter += 1
        
        return log_file
    
    def _write_event(self, event: AuditEvent):
        """Записать событие в WAL."""
        # Конвертация dataclass → dict
        event_dict = asdict(event)
        
        # Конвертация datetime → ISO string
        event_dict["timestamp"] = event.timestamp.isoformat()
        
        # Конвертация enum → string
        if isinstance(event.event_type, AuditEventType):
            event_dict["event_type"] = event.event_type.value
        
        # Запись в файл (append mode)
        with self.current_log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event_dict, ensure_ascii=False) + "\n")
    
    def log_policy_triggered(
        self,
        run_id: str,
        policy_name: str,
        priority: Priority,
        trigger_reason: str,
        metrics: Dict[str, float],
    ):
        """
        Записать срабатывание политики.
        
        Args:
            run_id: ID прогона
            policy_name: Имя политики
            priority: Приоритет
            trigger_reason: Причина срабатывания
            metrics: Метрики на момент события
        """
        event = AuditEvent(
            run_id=run_id,
            event_type=AuditEventType.POLICY_TRIGGERED,
            timestamp=datetime.now(timezone.utc),
            policy_name=policy_name,
            priority=priority.value,
            trigger_reason=trigger_reason,
            metrics=metrics,
        )
        self._write_event(event)
    
    def log_decision_made(
        self,
        decision: ActionDecision,
        metrics: Dict[str, float],
    ):
        """
        Записать принятие решения.
        
        Args:
            decision: Решение от DecisionEngine
            metrics: Метрики на момент решения
        """
        event = AuditEvent(
            run_id=decision.run_id,
            event_type=AuditEventType.DECISION_MADE,
            timestamp=decision.scheduled_at,
            policy_name=decision.policy_name,
            decision_id=decision.decision_id,
            action_type=decision.action.action_type,
            priority=decision.priority.value,
            trigger_reason=decision.reason,
            metrics=metrics,
            metadata={"action_params": decision.action.params},
        )
        self._write_event(event)
    
    def log_action_started(
        self,
        run_id: str,
        decision_id: str,
        action_type: str,
        metrics: Dict[str, float],
    ):
        """
        Записать начало выполнения действия.
        
        Args:
            run_id: ID прогона
            decision_id: ID решения
            action_type: Тип действия
            metrics: Метрики перед выполнением
        """
        event = AuditEvent(
            run_id=run_id,
            event_type=AuditEventType.ACTION_STARTED,
            timestamp=datetime.now(timezone.utc),
            decision_id=decision_id,
            action_type=action_type,
            metrics=metrics,
        )
        self._write_event(event)
    
    def log_action_completed(
        self,
        run_id: str,
        decision_id: str,
        result: ActionResult,
    ):
        """
        Записать успешное завершение действия.
        
        Args:
            run_id: ID прогона
            decision_id: ID решения
            result: Результат выполнения
        """
        event_type = {
            ActionStatus.SUCCESS: AuditEventType.ACTION_COMPLETED,
            ActionStatus.FAILURE: AuditEventType.ACTION_FAILED,
            ActionStatus.SKIPPED: AuditEventType.ACTION_SKIPPED,
            ActionStatus.DRY_RUN: AuditEventType.ACTION_SKIPPED,
        }.get(result.status, AuditEventType.ACTION_COMPLETED)
        
        event = AuditEvent(
            run_id=run_id,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            decision_id=decision_id,
            action_type=result.action_type,
            result_status=result.status.value,
            duration_seconds=result.duration_seconds,
            metrics=result.metrics_after,
            error_message=result.error,
            metadata={
                "message": result.message,
                "metrics_before": result.metrics_before,
            },
        )
        self._write_event(event)
    
    def read_events(
        self,
        run_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[AuditEvent]:
        """
        Прочитать события из WAL.
        
        Args:
            run_id: Фильтр по run_id
            event_type: Фильтр по типу события
            since: Фильтр по времени (от)
            until: Фильтр по времени (до)
            limit: Ограничение на количество событий
        
        Returns:
            Список событий
        """
        events: List[AuditEvent] = []
        
        # Читаем все JSONL файлы в директории
        for log_file in sorted(self.log_dir.glob("audit_*.jsonl")):
            with log_file.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        event_dict = json.loads(line.strip())
                        
                        # Парсинг timestamp
                        timestamp = datetime.fromisoformat(event_dict["timestamp"])
                        
                        # Фильтры
                        if since and timestamp < since:
                            continue
                        if until and timestamp > until:
                            continue
                        if run_id and event_dict.get("run_id") != run_id:
                            continue
                        if event_type and event_dict.get("event_type") != event_type.value:
                            continue
                        
                        # Конвертация dict → AuditEvent
                        event = AuditEvent(
                            run_id=event_dict["run_id"],
                            event_type=AuditEventType(event_dict["event_type"]),
                            timestamp=timestamp,
                            policy_name=event_dict.get("policy_name"),
                            decision_id=event_dict.get("decision_id"),
                            action_type=event_dict.get("action_type"),
                            priority=event_dict.get("priority"),
                            trigger_reason=event_dict.get("trigger_reason"),
                            metrics=event_dict.get("metrics"),
                            result_status=event_dict.get("result_status"),
                            duration_seconds=event_dict.get("duration_seconds"),
                            error_message=event_dict.get("error_message"),
                            metadata=event_dict.get("metadata"),
                        )
                        
                        events.append(event)
                        
                        # Limit
                        if limit and len(events) >= limit:
                            return events
                    
                    except (json.JSONDecodeError, KeyError, ValueError):
                        # Skip malformed lines
                        continue
        
        return events
    
    def get_run_summary(self, run_id: str) -> Dict[str, Any]:
        """
        Получить сводку по прогону.
        
        Args:
            run_id: ID прогона
        
        Returns:
            Dict со статистикой прогона
        """
        events = self.read_events(run_id=run_id)
        
        if not events:
            return {"run_id": run_id, "found": False}
        
        policies_triggered = [e for e in events if e.event_type == AuditEventType.POLICY_TRIGGERED]
        decisions_made = [e for e in events if e.event_type == AuditEventType.DECISION_MADE]
        actions_completed = [e for e in events if e.event_type == AuditEventType.ACTION_COMPLETED]
        actions_failed = [e for e in events if e.event_type == AuditEventType.ACTION_FAILED]
        actions_skipped = [e for e in events if e.event_type == AuditEventType.ACTION_SKIPPED]
        
        return {
            "run_id": run_id,
            "found": True,
            "start_time": events[0].timestamp.isoformat() if events else None,
            "end_time": events[-1].timestamp.isoformat() if events else None,
            "total_events": len(events),
            "policies_triggered": len(policies_triggered),
            "decisions_made": len(decisions_made),
            "actions_completed": len(actions_completed),
            "actions_failed": len(actions_failed),
            "actions_skipped": len(actions_skipped),
            "success_rate": len(actions_completed) / len(decisions_made) if decisions_made else 0.0,
        }
    
    def get_recent_failures(self, limit: int = 10) -> List[AuditEvent]:
        """
        Получить последние неудачные действия.
        
        Args:
            limit: Ограничение на количество
        
        Returns:
            Список событий ACTION_FAILED
        """
        return self.read_events(
            event_type=AuditEventType.ACTION_FAILED,
            limit=limit,
        )
    
    def clear_old_logs(self, days: int = 30):
        """
        Очистить старые логи.
        
        Args:
            days: Удалить логи старше N дней
        """
        cutoff = datetime.now(timezone.utc).timestamp() - (days * 24 * 60 * 60)
        
        for log_file in self.log_dir.glob("audit_*.jsonl"):
            if log_file.stat().st_mtime < cutoff:
                log_file.unlink()
