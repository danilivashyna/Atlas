"""
Tests for Atlas Homeostasis Action Adapters (E4.3 Beta)

Проверяет:
- Pre-checks перед выполнением
- Dry-run mode
- Execution log tracking
- Action dispatch (rebuild_shard, reembed_batch, etc.)
- Error handling

Beta version: stubs only, no real E2 integration.
"""

from pathlib import Path

from atlas.homeostasis.actions import ActionAdapter, ActionStatus
from atlas.homeostasis.policy import Action


class TestActionAdapter:
    """Тесты для ActionAdapter (beta)."""
    
    def test_dry_run_mode(self, tmp_path: Path):
        """Тест: dry-run mode не выполняет действия."""
        adapter = ActionAdapter(data_dir=tmp_path, dry_run=True)
        
        action = Action(
            action_type="rebuild_shard",
            params={"level": "sentence"},
        )
        
        metrics = {"h_coherence_sent_to_para": 0.65}
        
        result = adapter.execute(action, metrics)
        
        assert result.status == ActionStatus.DRY_RUN
        assert result.action_type == "rebuild_shard"
        assert "would execute" in result.message
        assert result.duration_seconds == 0.0
    
    def test_rebuild_shard_success(self, tmp_path: Path):
        """Тест: rebuild_shard возвращает success (beta stub)."""
        adapter = ActionAdapter(data_dir=tmp_path, dry_run=False)
        
        action = Action(
            action_type="rebuild_shard",
            params={"level": "sentence"},
        )
        
        metrics = {"h_coherence_sent_to_para": 0.65}
        
        result = adapter.execute(action, metrics)
        
        assert result.status == ActionStatus.SUCCESS
        assert result.action_type == "rebuild_shard"
        assert "sentence" in result.message
        assert result.metrics_before == metrics
        assert result.error is None
    
    def test_reembed_batch_success(self, tmp_path: Path):
        """Тест: reembed_batch возвращает success (beta stub)."""
        adapter = ActionAdapter(data_dir=tmp_path, dry_run=False)
        
        action = Action(
            action_type="reembed_batch",
            params={"batch_size": 100},
        )
        
        metrics = {"h_coherence_para_to_doc": 0.72}
        
        result = adapter.execute(action, metrics)
        
        assert result.status == ActionStatus.SUCCESS
        assert result.action_type == "reembed_batch"
        assert "100" in result.message
        assert result.error is None
    
    def test_tune_search_params_success(self, tmp_path: Path):
        """Тест: tune_search_params возвращает success (beta stub)."""
        adapter = ActionAdapter(data_dir=tmp_path, dry_run=False)
        
        action = Action(
            action_type="tune_search_params",
            params={"ef_search": 128, "nprobe": 32},
        )
        
        metrics = {"search_latency_p95_ms": 150.0}
        
        result = adapter.execute(action, metrics)
        
        assert result.status == ActionStatus.SUCCESS
        assert result.action_type == "tune_search_params"
        assert result.error is None
    
    def test_quarantine_docs_success(self, tmp_path: Path):
        """Тест: quarantine_docs возвращает success (beta stub)."""
        adapter = ActionAdapter(data_dir=tmp_path, dry_run=False)
        
        action = Action(
            action_type="quarantine_docs",
            params={"doc_ids": ["doc1", "doc2", "doc3"]},
        )
        
        metrics = {"h_stability_drift": 0.12}
        
        result = adapter.execute(action, metrics)
        
        assert result.status == ActionStatus.SUCCESS
        assert result.action_type == "quarantine_docs"
        assert "3" in result.message
        assert result.error is None
    
    def test_regenerate_manifest_success(self, tmp_path: Path):
        """Тест: regenerate_manifest возвращает success (beta stub)."""
        adapter = ActionAdapter(data_dir=tmp_path, dry_run=False)
        
        action = Action(
            action_type="regenerate_manifest",
            params={},
        )
        
        metrics = {"manifest_age_hours": 180.0}
        
        result = adapter.execute(action, metrics)
        
        assert result.status == ActionStatus.SUCCESS
        assert result.action_type == "regenerate_manifest"
        assert result.error is None
    
    def test_pre_check_missing_level(self, tmp_path: Path):
        """Тест: pre-check ловит отсутствие level для rebuild_shard."""
        adapter = ActionAdapter(data_dir=tmp_path, dry_run=False)
        
        action = Action(
            action_type="rebuild_shard",
            params={},  # Missing level!
        )
        
        metrics = {"h_coherence_sent_to_para": 0.65}
        
        result = adapter.execute(action, metrics)
        
        assert result.status == ActionStatus.SKIPPED
        assert "Missing parameter: level" in result.message
    
    def test_pre_check_invalid_level(self, tmp_path: Path):
        """Тест: pre-check ловит невалидный level."""
        adapter = ActionAdapter(data_dir=tmp_path, dry_run=False)
        
        action = Action(
            action_type="rebuild_shard",
            params={"level": "invalid_level"},
        )
        
        metrics = {"h_coherence_sent_to_para": 0.65}
        
        result = adapter.execute(action, metrics)
        
        assert result.status == ActionStatus.SKIPPED
        assert "Invalid level" in result.message
    
    def test_pre_check_invalid_batch_size(self, tmp_path: Path):
        """Тест: pre-check ловит невалидный batch_size."""
        adapter = ActionAdapter(data_dir=tmp_path, dry_run=False)
        
        action = Action(
            action_type="reembed_batch",
            params={"batch_size": -10},  # Invalid!
        )
        
        metrics = {"h_coherence_para_to_doc": 0.72}
        
        result = adapter.execute(action, metrics)
        
        assert result.status == ActionStatus.SKIPPED
        assert "Invalid batch_size" in result.message
    
    def test_pre_check_missing_search_params(self, tmp_path: Path):
        """Тест: pre-check ловит отсутствие search params."""
        adapter = ActionAdapter(data_dir=tmp_path, dry_run=False)
        
        action = Action(
            action_type="tune_search_params",
            params={},  # Empty params!
        )
        
        metrics = {"search_latency_p95_ms": 150.0}
        
        result = adapter.execute(action, metrics)
        
        assert result.status == ActionStatus.SKIPPED
        assert "Missing search parameters" in result.message
    
    def test_execution_log_tracking(self, tmp_path: Path):
        """Тест: execution log отслеживает все действия."""
        adapter = ActionAdapter(data_dir=tmp_path, dry_run=False)
        
        action1 = Action(action_type="rebuild_shard", params={"level": "sentence"})
        action2 = Action(action_type="reembed_batch", params={"batch_size": 50})
        action3 = Action(action_type="regenerate_manifest", params={})
        
        metrics = {"h_coherence_sent_to_para": 0.65}
        
        adapter.execute(action1, metrics)
        adapter.execute(action2, metrics)
        adapter.execute(action3, metrics)
        
        log = adapter.get_execution_log()
        
        assert len(log) == 3
        assert log[0].action_type == "rebuild_shard"
        assert log[1].action_type == "reembed_batch"
        assert log[2].action_type == "regenerate_manifest"
        
        # Тест лимита
        log_limited = adapter.get_execution_log(limit=2)
        assert len(log_limited) == 2
        assert log_limited[0].action_type == "reembed_batch"
        assert log_limited[1].action_type == "regenerate_manifest"
    
    def test_clear_log(self, tmp_path: Path):
        """Тест: clear_log очищает лог."""
        adapter = ActionAdapter(data_dir=tmp_path, dry_run=False)
        
        action = Action(action_type="rebuild_shard", params={"level": "sentence"})
        metrics = {"h_coherence_sent_to_para": 0.65}
        
        adapter.execute(action, metrics)
        assert len(adapter.get_execution_log()) == 1
        
        adapter.clear_log()
        assert len(adapter.get_execution_log()) == 0
    
    def test_unknown_action_type(self, tmp_path: Path):
        """Тест: неизвестный action_type возвращает FAILURE."""
        adapter = ActionAdapter(data_dir=tmp_path, dry_run=False)
        
        action = Action(
            action_type="unknown_action",
            params={},
        )
        
        metrics = {}
        
        result = adapter.execute(action, metrics)
        
        assert result.status == ActionStatus.FAILURE
        assert result.error is not None
        assert "Unknown action type" in result.error


class TestEdgeCases:
    """Тесты граничных случаев."""
    
    def test_data_dir_not_exists(self, tmp_path: Path):
        """Тест: если data_dir не существует — pre-check fails."""
        non_existent = tmp_path / "non_existent"
        adapter = ActionAdapter(data_dir=non_existent, dry_run=False)
        
        action = Action(action_type="rebuild_shard", params={"level": "sentence"})
        metrics = {"h_coherence_sent_to_para": 0.65}
        
        result = adapter.execute(action, metrics)
        
        assert result.status == ActionStatus.SKIPPED
        assert "Data directory not found" in result.message
    
    def test_metrics_preserved_in_result(self, tmp_path: Path):
        """Тест: метрики сохраняются в result."""
        adapter = ActionAdapter(data_dir=tmp_path, dry_run=False)
        
        action = Action(action_type="rebuild_shard", params={"level": "sentence"})
        metrics = {
            "h_coherence_sent_to_para": 0.65,
            "h_coherence_para_to_doc": 0.82,
            "h_stability_drift": 0.05,
        }
        
        result = adapter.execute(action, metrics)
        
        assert result.metrics_before == metrics
        assert result.metrics_after == metrics  # Beta: no changes
    
    def test_duration_tracking(self, tmp_path: Path):
        """Тест: duration_seconds отслеживается."""
        adapter = ActionAdapter(data_dir=tmp_path, dry_run=False)
        
        action = Action(action_type="rebuild_shard", params={"level": "sentence"})
        metrics = {"h_coherence_sent_to_para": 0.65}
        
        result = adapter.execute(action, metrics)
        
        # Duration должен быть > 0 (даже для stub)
        assert result.duration_seconds >= 0.0
