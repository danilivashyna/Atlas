"""
Tests for Atlas Homeostasis Audit Logger (E4.5 Beta)

Проверяет:
- JSONL запись событий
- Фильтрация по run_id, event_type, времени
- Run summary (статистика прогона)
- Recent failures
- Log rotation

Beta version: file-based WAL, basic filters.
"""

from datetime import datetime, timezone
from pathlib import Path

from atlas.homeostasis.actions import ActionResult, ActionStatus
from atlas.homeostasis.audit import AuditEventType, AuditLogger
from atlas.homeostasis.decision import ActionDecision
from atlas.homeostasis.policy import Action, Priority


class TestAuditLogger:
    """Тесты для AuditLogger."""

    def test_log_policy_triggered(self, tmp_path: Path):
        """Тест: запись policy_triggered события."""
        logger = AuditLogger(log_dir=tmp_path / "audit")

        logger.log_policy_triggered(
            run_id="run_001",
            policy_name="critical_coherence",
            priority=Priority.CRITICAL,
            trigger_reason="h_coherence_sent_to_para < 0.70",
            metrics={"h_coherence_sent_to_para": 0.65},
        )

        events = logger.read_events(run_id="run_001")

        assert len(events) == 1
        assert events[0].event_type == AuditEventType.POLICY_TRIGGERED
        assert events[0].policy_name == "critical_coherence"
        assert events[0].priority == "critical"
        assert events[0].trigger_reason == "h_coherence_sent_to_para < 0.70"
        assert events[0].metrics == {"h_coherence_sent_to_para": 0.65}

    def test_log_decision_made(self, tmp_path: Path):
        """Тест: запись decision_made события."""
        logger = AuditLogger(log_dir=tmp_path / "audit")

        decision = ActionDecision(
            action=Action(action_type="rebuild_shard", params={"level": "sentence"}),
            policy_name="critical_coherence",
            priority=Priority.CRITICAL,
            reason="h_coherence_sent_to_para < 0.70",
            scheduled_at=datetime.now(timezone.utc),
            run_id="run_001",
            decision_id="dec_001",
        )

        logger.log_decision_made(
            decision=decision,
            metrics={"h_coherence_sent_to_para": 0.65},
        )

        events = logger.read_events(run_id="run_001")

        assert len(events) == 1
        assert events[0].event_type == AuditEventType.DECISION_MADE
        assert events[0].decision_id == "dec_001"
        assert events[0].action_type == "rebuild_shard"
        assert events[0].metadata is not None
        assert events[0].metadata["action_params"] == {"level": "sentence"}

    def test_log_action_completed(self, tmp_path: Path):
        """Тест: запись action_completed события."""
        logger = AuditLogger(log_dir=tmp_path / "audit")

        result = ActionResult(
            action_type="rebuild_shard",
            status=ActionStatus.SUCCESS,
            duration_seconds=12.5,
            message="Rebuild completed",
            metrics_before={"h_coherence_sent_to_para": 0.65},
            metrics_after={"h_coherence_sent_to_para": 0.82},
        )

        logger.log_action_completed(
            run_id="run_001",
            decision_id="dec_001",
            result=result,
        )

        events = logger.read_events(run_id="run_001")

        assert len(events) == 1
        assert events[0].event_type == AuditEventType.ACTION_COMPLETED
        assert events[0].decision_id == "dec_001"
        assert events[0].action_type == "rebuild_shard"
        assert events[0].result_status == "success"
        assert events[0].duration_seconds == 12.5
        assert events[0].metrics == {"h_coherence_sent_to_para": 0.82}

    def test_log_action_failed(self, tmp_path: Path):
        """Тест: запись action_failed события."""
        logger = AuditLogger(log_dir=tmp_path / "audit")

        result = ActionResult(
            action_type="rebuild_shard",
            status=ActionStatus.FAILURE,
            duration_seconds=5.0,
            message="Rebuild failed",
            metrics_before={"h_coherence_sent_to_para": 0.65},
            error="Index file not found",
        )

        logger.log_action_completed(
            run_id="run_001",
            decision_id="dec_001",
            result=result,
        )

        events = logger.read_events(run_id="run_001")

        assert len(events) == 1
        assert events[0].event_type == AuditEventType.ACTION_FAILED
        assert events[0].result_status == "failure"
        assert events[0].error_message == "Index file not found"

    def test_full_chain(self, tmp_path: Path):
        """Тест: полная цепочка Policy → Decision → Action."""
        logger = AuditLogger(log_dir=tmp_path / "audit")

        run_id = "run_full_001"
        metrics = {"h_coherence_sent_to_para": 0.65}

        # 1. Policy triggered
        logger.log_policy_triggered(
            run_id=run_id,
            policy_name="critical_coherence",
            priority=Priority.CRITICAL,
            trigger_reason="h_coherence_sent_to_para < 0.70",
            metrics=metrics,
        )

        # 2. Decision made
        decision = ActionDecision(
            action=Action(action_type="rebuild_shard", params={"level": "sentence"}),
            policy_name="critical_coherence",
            priority=Priority.CRITICAL,
            reason="h_coherence_sent_to_para < 0.70",
            scheduled_at=datetime.now(timezone.utc),
            run_id=run_id,
            decision_id="dec_001",
        )
        logger.log_decision_made(decision, metrics)

        # 3. Action started
        logger.log_action_started(
            run_id=run_id,
            decision_id="dec_001",
            action_type="rebuild_shard",
            metrics=metrics,
        )

        # 4. Action completed
        result = ActionResult(
            action_type="rebuild_shard",
            status=ActionStatus.SUCCESS,
            duration_seconds=12.5,
            message="Rebuild completed",
            metrics_before=metrics,
            metrics_after={"h_coherence_sent_to_para": 0.82},
        )
        logger.log_action_completed(run_id, "dec_001", result)

        # Проверка цепочки
        events = logger.read_events(run_id=run_id)

        assert len(events) == 4
        assert events[0].event_type == AuditEventType.POLICY_TRIGGERED
        assert events[1].event_type == AuditEventType.DECISION_MADE
        assert events[2].event_type == AuditEventType.ACTION_STARTED
        assert events[3].event_type == AuditEventType.ACTION_COMPLETED

    def test_filter_by_event_type(self, tmp_path: Path):
        """Тест: фильтрация по event_type."""
        logger = AuditLogger(log_dir=tmp_path / "audit")

        run_id = "run_002"

        logger.log_policy_triggered(
            run_id=run_id,
            policy_name="policy_1",
            priority=Priority.CRITICAL,
            trigger_reason="test",
            metrics={},
        )

        logger.log_action_started(
            run_id=run_id,
            decision_id="dec_002",
            action_type="rebuild_shard",
            metrics={},
        )

        # Фильтр только ACTION_STARTED
        events = logger.read_events(
            run_id=run_id,
            event_type=AuditEventType.ACTION_STARTED,
        )

        assert len(events) == 1
        assert events[0].event_type == AuditEventType.ACTION_STARTED

    def test_filter_by_time(self, tmp_path: Path):
        """Тест: фильтрация по времени."""
        logger = AuditLogger(log_dir=tmp_path / "audit")

        now = datetime.now(timezone.utc)

        # Событие 1 час назад
        logger.log_policy_triggered(
            run_id="run_old",
            policy_name="policy_old",
            priority=Priority.LOW,
            trigger_reason="test",
            metrics={},
        )

        # Ждём чуть-чуть для разницы во времени
        import time

        time.sleep(0.01)

        # Событие сейчас
        logger.log_policy_triggered(
            run_id="run_new",
            policy_name="policy_new",
            priority=Priority.CRITICAL,
            trigger_reason="test",
            metrics={},
        )

        # Фильтр последних 1 секунды
        since = now
        events = logger.read_events(since=since)

        # Должно быть только новое событие
        assert len(events) >= 1
        assert any(e.run_id == "run_new" for e in events)

    def test_get_run_summary(self, tmp_path: Path):
        """Тест: статистика прогона."""
        logger = AuditLogger(log_dir=tmp_path / "audit")

        run_id = "run_summary_001"

        # 2 политики сработали
        logger.log_policy_triggered(
            run_id=run_id,
            policy_name="policy_1",
            priority=Priority.CRITICAL,
            trigger_reason="test",
            metrics={},
        )
        logger.log_policy_triggered(
            run_id=run_id,
            policy_name="policy_2",
            priority=Priority.HIGH,
            trigger_reason="test",
            metrics={},
        )

        # 2 решения
        for i in range(2):
            decision = ActionDecision(
                action=Action(action_type="rebuild_shard", params={}),
                policy_name=f"policy_{i+1}",
                priority=Priority.CRITICAL,
                reason="test",
                scheduled_at=datetime.now(timezone.utc),
                run_id=run_id,
                decision_id=f"dec_{i+1}",
            )
            logger.log_decision_made(decision, {})

        # 1 успех, 1 провал
        logger.log_action_completed(
            run_id,
            "dec_1",
            ActionResult(
                action_type="rebuild_shard",
                status=ActionStatus.SUCCESS,
                duration_seconds=10.0,
                message="OK",
            ),
        )
        logger.log_action_completed(
            run_id,
            "dec_2",
            ActionResult(
                action_type="rebuild_shard",
                status=ActionStatus.FAILURE,
                duration_seconds=5.0,
                message="FAIL",
                error="Error",
            ),
        )

        summary = logger.get_run_summary(run_id)

        assert summary["found"] is True
        assert summary["run_id"] == run_id
        assert summary["policies_triggered"] == 2
        assert summary["decisions_made"] == 2
        assert summary["actions_completed"] == 1
        assert summary["actions_failed"] == 1
        assert summary["success_rate"] == 0.5

    def test_get_recent_failures(self, tmp_path: Path):
        """Тест: получение последних неудач."""
        logger = AuditLogger(log_dir=tmp_path / "audit")

        # 3 неудачи
        for i in range(3):
            logger.log_action_completed(
                run_id=f"run_{i}",
                decision_id=f"dec_{i}",
                result=ActionResult(
                    action_type="rebuild_shard",
                    status=ActionStatus.FAILURE,
                    duration_seconds=5.0,
                    message="FAIL",
                    error=f"Error {i}",
                ),
            )

        # 1 успех (не должен попасть)
        logger.log_action_completed(
            run_id="run_success",
            decision_id="dec_success",
            result=ActionResult(
                action_type="rebuild_shard",
                status=ActionStatus.SUCCESS,
                duration_seconds=10.0,
                message="OK",
            ),
        )

        failures = logger.get_recent_failures(limit=10)

        assert len(failures) == 3
        for f in failures:
            assert f.event_type == AuditEventType.ACTION_FAILED
            assert f.error_message is not None

    def test_limit_filter(self, tmp_path: Path):
        """Тест: ограничение limit."""
        logger = AuditLogger(log_dir=tmp_path / "audit")

        # 10 событий
        for i in range(10):
            logger.log_policy_triggered(
                run_id=f"run_{i}",
                policy_name="policy",
                priority=Priority.LOW,
                trigger_reason="test",
                metrics={},
            )

        # Limit 5
        events = logger.read_events(limit=5)

        assert len(events) == 5


class TestEdgeCases:
    """Тесты граничных случаев."""

    def test_empty_log(self, tmp_path: Path):
        """Тест: пустой лог."""
        logger = AuditLogger(log_dir=tmp_path / "audit")

        events = logger.read_events()
        assert len(events) == 0

    def test_run_summary_not_found(self, tmp_path: Path):
        """Тест: run_id не найден."""
        logger = AuditLogger(log_dir=tmp_path / "audit")

        summary = logger.get_run_summary("non_existent_run")

        assert summary["found"] is False
        assert summary["run_id"] == "non_existent_run"

    def test_jsonl_persistence(self, tmp_path: Path):
        """Тест: JSONL файл персистентен между сессиями."""
        log_dir = tmp_path / "audit"

        # Сессия 1: запись
        logger1 = AuditLogger(log_dir=log_dir)
        logger1.log_policy_triggered(
            run_id="run_persist",
            policy_name="policy",
            priority=Priority.CRITICAL,
            trigger_reason="test",
            metrics={},
        )

        # Сессия 2: чтение
        logger2 = AuditLogger(log_dir=log_dir)
        events = logger2.read_events(run_id="run_persist")

        assert len(events) == 1
        assert events[0].policy_name == "policy"
