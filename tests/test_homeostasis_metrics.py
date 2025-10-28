# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Tests for Atlas Homeostasis Metrics (E4.8)

Проверяет:
- Initialization (with/without prometheus_client)
- Record decision
- Record action duration
- Update success ratio and snapshot age
- Metrics text export (stub mode)

Note: Uses global singleton to avoid Prometheus registry conflicts.
"""

from atlas.metrics.homeostasis import (
    get_homeostasis_metrics,
    PROMETHEUS_AVAILABLE,
)


class TestHomeostasisMetrics:
    """Тесты для HomeostasisMetrics."""
    
    def test_global_instance(self) -> None:
        """Глобальный instance (singleton)."""
        metrics1 = get_homeostasis_metrics()
        metrics2 = get_homeostasis_metrics()
        
        # Should return same instance
        assert metrics1 is metrics2
    
    def test_record_decision(self) -> None:
        """Запись решения."""
        metrics = get_homeostasis_metrics()
        
        # Should not raise (stub or real)
        metrics.record_decision(
            policy="test_policy",
            action_type="rebuild_shard",
            status="approved",
        )
    
    def test_record_action_duration(self) -> None:
        """Запись длительности действия."""
        metrics = get_homeostasis_metrics()
        
        # Should not raise
        metrics.record_action_duration(
            action_type="rebuild_shard",
            duration_seconds=5.2,
        )
    
    def test_update_success_ratio(self) -> None:
        """Обновление success ratio."""
        metrics = get_homeostasis_metrics()
        
        # Should not raise
        metrics.update_repair_success_ratio(0.95)
    
    def test_update_snapshot_age(self) -> None:
        """Обновление возраста снапшота."""
        metrics = get_homeostasis_metrics()
        
        # Should not raise
        metrics.update_snapshot_age(3600.0)
    
    def test_get_metrics_text(self) -> None:
        """Получение метрик в text формате."""
        metrics = get_homeostasis_metrics()
        
        text = metrics.get_metrics_text()
        
        # Should return string
        assert isinstance(text, str)
        
        if not PROMETHEUS_AVAILABLE:
            assert "Prometheus client not installed" in text
    
    def test_init_stub_mode(self) -> None:
        """Проверка stub mode."""
        metrics = get_homeostasis_metrics()
        
        if not PROMETHEUS_AVAILABLE:
            assert metrics.decision_count_total is None
            assert metrics.action_duration_seconds is None
            assert metrics.repair_success_ratio is None
            assert metrics.snapshot_age_seconds is None
