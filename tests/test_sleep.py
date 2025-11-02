# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Tests for Atlas Sleep & Consolidation (E4.6)

Проверяет:
- Consolidation sequence (defrag → compression → threshold recalibration)
- Pre/post snapshots
- Audit logging
- Metrics updates
- Dry-run mode
- Threshold double-confirmation
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from atlas.homeostasis.sleep import SleepManager, ConsolidationResult, create_sleep_manager


class TestSleepManager:
    """Тесты для SleepManager."""

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_snapshot_manager(self) -> MagicMock:
        """Mock SnapshotManager."""
        mock = MagicMock()
        mock.create_snapshot.return_value = {
            "snapshot_id": "20251028_120000_000000",
            "created_at": 1698489600.0,
        }
        return mock

    @pytest.fixture
    def mock_audit_logger(self) -> MagicMock:
        """Mock AuditLogger."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def mock_metrics(self) -> MagicMock:
        """Mock HomeostasisMetrics."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def sleep_manager(
        self,
        temp_dir: Path,
        mock_snapshot_manager: MagicMock,
        mock_audit_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> SleepManager:
        """Create SleepManager with mocks."""
        return SleepManager(
            data_dir=temp_dir,
            snapshot_manager=mock_snapshot_manager,
            audit_logger=mock_audit_logger,
            metrics=mock_metrics,
        )

    def test_init(self, sleep_manager: SleepManager, temp_dir: Path) -> None:
        """Тест инициализации."""
        assert sleep_manager.data_dir == temp_dir
        assert sleep_manager.snapshot_manager is not None
        assert sleep_manager.audit_logger is not None
        assert sleep_manager.metrics is not None
        assert sleep_manager.defrag_threshold == 0.3
        assert sleep_manager.compression_age_days == 7
        assert sleep_manager.threshold_confidence == 0.95

    def test_consolidation_dry_run(self, sleep_manager: SleepManager) -> None:
        """Тест dry-run consolidation."""
        result = sleep_manager.run_consolidation(run_id="test-dry-001", dry_run=True)

        assert isinstance(result, ConsolidationResult)
        assert result.run_id == "test-dry-001"
        assert result.success is True
        assert result.duration_seconds > 0

        # Dry-run should not create snapshots
        assert not any("snapshot" in action for action in result.actions_performed)

        # Should still calculate stats
        assert "fragmentation_before" in result.defrag_stats
        assert "compressed_count" in result.compression_stats
        assert result.compression_stats["compressed_count"] == 0  # Dry-run

    def test_consolidation_full_run(
        self,
        sleep_manager: SleepManager,
        mock_snapshot_manager: MagicMock,
        mock_audit_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Тест полного consolidation run."""
        result = sleep_manager.run_consolidation(run_id="test-full-001", dry_run=False)

        assert result.success is True
        assert len(result.actions_performed) > 0

        # Should create pre/post snapshots
        assert mock_snapshot_manager.create_snapshot.call_count == 2
        calls = mock_snapshot_manager.create_snapshot.call_args_list
        assert "pre_consolidation" in calls[0][1]["reason"]
        assert "post_consolidation" in calls[1][1]["reason"]

        # Should log to audit
        assert mock_audit_logger.log_consolidation_completed.called

        # Should update metrics
        assert mock_metrics.update_consolidation_duration.called
        assert mock_metrics.increment_consolidation_count.called

    def test_defragmentation(self, sleep_manager: SleepManager) -> None:
        """Тест дефрагментации."""
        stats = sleep_manager._run_defragmentation(dry_run=False)

        assert stats["performed"] is True
        assert stats["fragmentation_before"] > sleep_manager.defrag_threshold
        assert stats["fragmentation_after"] < stats["fragmentation_before"]
        assert stats["bytes_reclaimed"] > 0

    def test_defragmentation_below_threshold(self, sleep_manager: SleepManager) -> None:
        """Тест пропуска дефрагментации при низкой фрагментации."""
        # Override threshold to skip defrag
        sleep_manager.defrag_threshold = 0.9

        stats = sleep_manager._run_defragmentation(dry_run=False)

        assert stats["performed"] is False
        assert stats["reason"] == "below_threshold"

    def test_vector_compression(self, sleep_manager: SleepManager) -> None:
        """Тест сжатия векторов."""
        stats = sleep_manager._run_vector_compression(dry_run=False)

        assert stats["candidates"] > 0
        assert stats["compressed_count"] == stats["candidates"]
        assert stats["bytes_saved"] > 0
        assert stats["quality_loss"] < 0.01  # Max 1% quality loss

    def test_vector_compression_dry_run(self, sleep_manager: SleepManager) -> None:
        """Тест dry-run сжатия векторов."""
        stats = sleep_manager._run_vector_compression(dry_run=True)

        assert stats["candidates"] > 0
        assert stats["compressed_count"] == 0  # Dry-run: no compression
        assert stats["bytes_saved"] > 0  # Potential savings calculated

    def test_threshold_recalibration(self, sleep_manager: SleepManager) -> None:
        """Тест перекалибровки порогов."""
        changes = sleep_manager._run_threshold_recalibration(dry_run=False)

        assert "changes_proposed" in changes
        assert "changes_applied" in changes
        assert "confidence" in changes

        # Stub should propose at least one change
        assert len(changes["changes_proposed"]) > 0

        # But not apply without manual approval
        assert len(changes["changes_applied"]) == 0

    def test_threshold_recalibration_dry_run(self, sleep_manager: SleepManager) -> None:
        """Тест dry-run перекалибровки порогов."""
        changes = sleep_manager._run_threshold_recalibration(dry_run=True)

        # Dry-run should propose but not apply
        assert len(changes["changes_applied"]) == 0

    def test_skip_threshold_recalibration(self, sleep_manager: SleepManager) -> None:
        """Тест пропуска перекалибровки порогов."""
        result = sleep_manager.run_consolidation(
            run_id="test-skip-001",
            dry_run=False,
            skip_threshold_recalibration=True,
        )

        # Should not perform threshold recalibration
        assert "threshold_recalibration" not in result.actions_performed
        assert len(result.threshold_changes) == 0

    def test_consolidation_without_dependencies(self, temp_dir: Path) -> None:
        """Тест consolidation без зависимостей (graceful degradation)."""
        manager = SleepManager(
            data_dir=temp_dir,
            snapshot_manager=None,
            audit_logger=None,
            metrics=None,
        )

        result = manager.run_consolidation(run_id="test-nodeps-001", dry_run=False)

        # Should still succeed without snapshots/audit/metrics
        assert result.success is True
        assert "pre_snapshot" not in str(result.actions_performed)
        assert "post_snapshot" not in str(result.actions_performed)

    def test_create_sleep_manager_factory(self, temp_dir: Path) -> None:
        """Тест фабрики create_sleep_manager."""
        manager = create_sleep_manager(data_dir=temp_dir)

        assert isinstance(manager, SleepManager)
        assert manager.data_dir == temp_dir
        assert manager.snapshot_manager is None
        assert manager.audit_logger is None
        assert manager.metrics is None

    def test_consolidation_result_dataclass(self, sleep_manager: SleepManager) -> None:
        """Тест ConsolidationResult dataclass."""
        result = sleep_manager.run_consolidation(run_id="test-result-001")

        # Verify all required fields present
        assert hasattr(result, "run_id")
        assert hasattr(result, "started_at")
        assert hasattr(result, "finished_at")
        assert hasattr(result, "duration_seconds")
        assert hasattr(result, "actions_performed")
        assert hasattr(result, "defrag_stats")
        assert hasattr(result, "compression_stats")
        assert hasattr(result, "threshold_changes")
        assert hasattr(result, "success")
        assert hasattr(result, "errors")

        # Verify types
        assert isinstance(result.actions_performed, list)
        assert isinstance(result.defrag_stats, dict)
        assert isinstance(result.compression_stats, dict)
        assert isinstance(result.threshold_changes, dict)
        assert isinstance(result.success, bool)
        assert isinstance(result.errors, list)
