"""
Tests for Atlas Homeostasis Snapshot & Rollback (E4.4)

Проверяет:
- Создание атомарных снапшотов
- SHA256 verification
- Rollback (≤30s)
- Retention policy
- Edge cases
"""

import time
from pathlib import Path

import pytest

from atlas.homeostasis.snapshot import (
    RollbackStatus,
    SnapshotManager,
    SnapshotStatus,
)


class TestSnapshotManager:
    """Тесты для SnapshotManager."""
    
    def test_create_snapshot(self, tmp_path: Path) -> None:
        """Создание снапшота."""
        # Setup
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        
        # Create dummy indices
        indices_dir = data_dir / "indices"
        indices_dir.mkdir()
        (indices_dir / "shard_0.faiss").write_text("faiss data")
        (indices_dir / "shard_1.hnsw").write_text("hnsw data")
        
        # Create dummy MANIFEST
        manifest_path = data_dir / "MANIFEST.json"
        manifest_path.write_text('{"version": "0.2"}')
        
        snapshots_dir = tmp_path / "snapshots"
        manager = SnapshotManager(
            data_dir=data_dir,
            snapshots_dir=snapshots_dir,
        )
        
        # Act
        metadata = manager.create_snapshot(
            reason="test_snapshot",
            metrics={"h_coherence": 0.85, "h_stability": 0.05},
        )
        
        # Assert
        assert metadata.reason == "test_snapshot"
        assert metadata.status == SnapshotStatus.CREATED
        assert metadata.files_count == 3  # 2 indices + 1 MANIFEST
        assert metadata.total_size_bytes > 0
        assert metadata.metrics_snapshot == {"h_coherence": 0.85, "h_stability": 0.05}
        
        # Verify files copied
        snapshot_path = snapshots_dir / metadata.snapshot_id
        assert (snapshot_path / "indices" / "shard_0.faiss").exists()
        assert (snapshot_path / "indices" / "shard_1.hnsw").exists()
        assert (snapshot_path / "MANIFEST.json").exists()
        assert (snapshot_path / "checksums.json").exists()
        assert (snapshot_path / "metadata.json").exists()
    
    def test_verify_snapshot_success(self, tmp_path: Path) -> None:
        """Проверка целостности снапшота (success)."""
        # Setup
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "indices").mkdir()
        (data_dir / "indices" / "test.faiss").write_text("test data")
        (data_dir / "MANIFEST.json").write_text('{"version": "0.2"}')
        
        manager = SnapshotManager(data_dir=data_dir, snapshots_dir=tmp_path / "snapshots")
        metadata = manager.create_snapshot(reason="test")
        
        # Act
        result = manager.verify_snapshot(metadata.snapshot_id)
        
        # Assert
        assert result is True
    
    def test_verify_snapshot_corrupted(self, tmp_path: Path) -> None:
        """Проверка целостности снапшота (corrupted)."""
        # Setup
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "indices").mkdir()
        (data_dir / "indices" / "test.faiss").write_text("test data")
        (data_dir / "MANIFEST.json").write_text('{"version": "0.2"}')
        
        manager = SnapshotManager(data_dir=data_dir, snapshots_dir=tmp_path / "snapshots")
        metadata = manager.create_snapshot(reason="test")
        
        # Corrupt a file
        snapshot_path = tmp_path / "snapshots" / metadata.snapshot_id
        corrupted_file = snapshot_path / "indices" / "test.faiss"
        corrupted_file.write_text("CORRUPTED DATA")
        
        # Act
        result = manager.verify_snapshot(metadata.snapshot_id)
        
        # Assert
        assert result is False
    
    def test_rollback_success(self, tmp_path: Path) -> None:
        """Откат к снапшоту (success)."""
        # Setup
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "indices").mkdir()
        (data_dir / "indices" / "test.faiss").write_text("original data")
        (data_dir / "MANIFEST.json").write_text('{"version": "0.2"}')
        
        manager = SnapshotManager(data_dir=data_dir, snapshots_dir=tmp_path / "snapshots")
        
        # Create snapshot
        metadata = manager.create_snapshot(reason="before_modification")
        
        # Modify data
        (data_dir / "indices" / "test.faiss").write_text("MODIFIED DATA")
        (data_dir / "MANIFEST.json").write_text('{"version": "0.3"}')
        
        # Act
        result = manager.rollback(metadata.snapshot_id)
        
        # Assert
        assert result.status == RollbackStatus.SUCCESS
        assert result.duration_seconds <= 30.0  # ≤30s SLO
        assert result.verification_ok is True
        assert result.files_restored == 2  # 1 index + 1 MANIFEST
        
        # Verify data restored
        assert (data_dir / "indices" / "test.faiss").read_text() == "original data"
        assert (data_dir / "MANIFEST.json").read_text() == '{"version": "0.2"}'
    
    def test_rollback_verification_failed(self, tmp_path: Path) -> None:
        """Откат к снапшоту (verification failed)."""
        # Setup
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "indices").mkdir()
        (data_dir / "indices" / "test.faiss").write_text("test data")
        (data_dir / "MANIFEST.json").write_text('{"version": "0.2"}')
        
        manager = SnapshotManager(data_dir=data_dir, snapshots_dir=tmp_path / "snapshots")
        metadata = manager.create_snapshot(reason="test")
        
        # Corrupt snapshot
        snapshot_path = tmp_path / "snapshots" / metadata.snapshot_id
        (snapshot_path / "indices" / "test.faiss").write_text("CORRUPTED")
        
        # Act
        result = manager.rollback(metadata.snapshot_id)
        
        # Assert
        assert result.status == RollbackStatus.VERIFICATION_FAILED
        assert result.verification_ok is False
        assert result.files_restored == 0
    
    def test_rollback_snapshot_not_found(self, tmp_path: Path) -> None:
        """Откат к несуществующему снапшоту."""
        manager = SnapshotManager(
            data_dir=tmp_path / "data",
            snapshots_dir=tmp_path / "snapshots",
        )
        
        # Act
        result = manager.rollback("nonexistent_snapshot")
        
        # Assert
        assert result.status == RollbackStatus.FAILURE
        assert "not found" in result.message.lower()
        assert result.files_restored == 0
    
    def test_list_snapshots(self, tmp_path: Path) -> None:
        """Список снапшотов (sorted by timestamp)."""
        # Setup
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "indices").mkdir()
        (data_dir / "indices" / "test.faiss").write_text("test")
        (data_dir / "MANIFEST.json").write_text('{}')
        
        manager = SnapshotManager(data_dir=data_dir, snapshots_dir=tmp_path / "snapshots")
        
        # Create multiple snapshots
        metadata1 = manager.create_snapshot(reason="snapshot_1")
        time.sleep(0.1)  # Ensure different timestamps
        metadata2 = manager.create_snapshot(reason="snapshot_2")
        time.sleep(0.1)
        metadata3 = manager.create_snapshot(reason="snapshot_3")
        
        # Act
        snapshots = manager.list_snapshots()
        
        # Assert
        assert len(snapshots) == 3
        # Newest first
        assert snapshots[0].snapshot_id == metadata3.snapshot_id
        assert snapshots[1].snapshot_id == metadata2.snapshot_id
        assert snapshots[2].snapshot_id == metadata1.snapshot_id
    
    def test_get_snapshot_age(self, tmp_path: Path) -> None:
        """Получение возраста снапшота."""
        # Setup
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "indices").mkdir()
        (data_dir / "indices" / "test.faiss").write_text("test")
        (data_dir / "MANIFEST.json").write_text('{}')
        
        manager = SnapshotManager(data_dir=data_dir, snapshots_dir=tmp_path / "snapshots")
        metadata = manager.create_snapshot(reason="test")
        
        time.sleep(1.0)
        
        # Act
        age = manager.get_snapshot_age(metadata.snapshot_id)
        
        # Assert
        assert age is not None
        assert age >= 1.0  # At least 1 second old
    
    def test_retention_policy_count(self, tmp_path: Path) -> None:
        """Retention policy (по количеству)."""
        # Setup
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "indices").mkdir()
        (data_dir / "indices" / "test.faiss").write_text("test")
        (data_dir / "MANIFEST.json").write_text('{}')
        
        manager = SnapshotManager(
            data_dir=data_dir,
            snapshots_dir=tmp_path / "snapshots",
            retention_count=3,  # Keep only last 3
            retention_days=0,  # All snapshots older than 0 days (delete beyond retention_count)
        )
        
        # Create 5 snapshots
        for i in range(5):
            manager.create_snapshot(reason=f"snapshot_{i}")
            time.sleep(0.01)  # Ensure different timestamps
        
        # Act
        snapshots = manager.list_snapshots()
        
        # Assert - should keep only last 3
        assert len(snapshots) == 3
    
    def test_snapshot_with_no_indices(self, tmp_path: Path) -> None:
        """Создание снапшота без indices (только MANIFEST)."""
        # Setup
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "MANIFEST.json").write_text('{"version": "0.2"}')
        
        manager = SnapshotManager(data_dir=data_dir, snapshots_dir=tmp_path / "snapshots")
        
        # Act
        metadata = manager.create_snapshot(reason="manifest_only")
        
        # Assert
        assert metadata.files_count == 1  # Only MANIFEST
        snapshot_path = tmp_path / "snapshots" / metadata.snapshot_id
        assert (snapshot_path / "MANIFEST.json").exists()
        assert not (snapshot_path / "indices").exists()


class TestEdgeCases:
    """Edge cases для Snapshot & Rollback."""
    
    def test_create_snapshot_no_data_dir(self, tmp_path: Path) -> None:
        """Создание снапшота если data_dir не существует."""
        manager = SnapshotManager(
            data_dir=tmp_path / "nonexistent",
            snapshots_dir=tmp_path / "snapshots",
        )
        
        with pytest.raises(ValueError, match="Data directory not found"):
            manager.create_snapshot(reason="test")
    
    def test_verify_snapshot_not_found(self, tmp_path: Path) -> None:
        """Проверка несуществующего снапшота."""
        manager = SnapshotManager(
            data_dir=tmp_path / "data",
            snapshots_dir=tmp_path / "snapshots",
        )
        
        result = manager.verify_snapshot("nonexistent_snapshot")
        
        assert result is False
    
    def test_get_snapshot_age_not_found(self, tmp_path: Path) -> None:
        """Возраст несуществующего снапшота."""
        manager = SnapshotManager(
            data_dir=tmp_path / "data",
            snapshots_dir=tmp_path / "snapshots",
        )
        
        age = manager.get_snapshot_age("nonexistent_snapshot")
        
        assert age is None
    
    def test_rollback_preserves_manifest_backup(self, tmp_path: Path) -> None:
        """Rollback создаёт backup текущего MANIFEST."""
        # Setup
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "indices").mkdir()
        (data_dir / "indices" / "test.faiss").write_text("original")
        (data_dir / "MANIFEST.json").write_text('{"version": "0.2"}')
        
        manager = SnapshotManager(data_dir=data_dir, snapshots_dir=tmp_path / "snapshots")
        metadata = manager.create_snapshot(reason="test")
        
        # Modify MANIFEST
        (data_dir / "MANIFEST.json").write_text('{"version": "0.3"}')
        
        # Act
        manager.rollback(metadata.snapshot_id)
        
        # Assert - backup should exist
        backup_path = data_dir / "MANIFEST.json.bak"
        assert backup_path.exists()
        assert backup_path.read_text() == '{"version": "0.3"}'
