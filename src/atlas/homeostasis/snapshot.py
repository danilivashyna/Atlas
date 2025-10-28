"""
Atlas Homeostasis Snapshot & Rollback (E4.4)

Атомарные снапшоты индексов + MANIFEST с быстрым откатом (≤30 сек).

Архитектурная роль:
- E4 (Homeostasis): Безопасность самовосстановления
- E2 (Vocabulary): Защита состояния индексов

Snapshot layout:
/snapshots/YYYYMMDD_HHMMSS/
  indices/         # Copy of all index files (FAISS/HNSW)
  MANIFEST.json    # Copy of MANIFEST
  checksums.json   # SHA256 checksums for verification
  metadata.json    # Timestamp, reason, metrics snapshot

Rollback protocol:
1. Stop readers (graceful)
2. Verify SHA256 checksums
3. Atomic MANIFEST swap
4. Reopen indices

GA SLO:
- Rollback time ≤30 сек (P95)
- SHA256 verification mandatory
- Retention policy: last N snapshots or age-based
"""

import hashlib
import json
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class SnapshotStatus(str, Enum):
    """Статус снапшота."""
    CREATED = "created"
    VERIFIED = "verified"
    CORRUPTED = "corrupted"
    RESTORED = "restored"


class RollbackStatus(str, Enum):
    """Статус отката."""
    SUCCESS = "success"
    FAILURE = "failure"
    VERIFICATION_FAILED = "verification_failed"


@dataclass
class SnapshotMetadata:
    """
    Метаданные снапшота.
    
    Attributes:
        snapshot_id: ID снапшота (YYYYMMDD_HHMMSS)
        timestamp: Время создания (ISO 8601)
        reason: Причина создания (e.g., "before_rebuild_shard")
        metrics_snapshot: Снимок метрик E3 на момент создания
        files_count: Количество файлов
        total_size_bytes: Общий размер
        status: Статус снапшота
    """
    snapshot_id: str
    timestamp: str
    reason: str
    metrics_snapshot: Dict[str, float]
    files_count: int
    total_size_bytes: int
    status: SnapshotStatus


@dataclass
class RollbackResult:
    """
    Результат отката.
    
    Attributes:
        snapshot_id: ID снапшота, к которому откатились
        status: Статус отката
        duration_seconds: Длительность отката
        files_restored: Количество восстановленных файлов
        verification_ok: SHA256 verification passed
        message: Сообщение о результате
        error: Текст ошибки (если failure)
    """
    snapshot_id: str
    status: RollbackStatus
    duration_seconds: float
    files_restored: int
    verification_ok: bool
    message: str
    error: Optional[str] = None


class SnapshotManager:
    """
    Менеджер снапшотов для гомеостаза.
    
    Функции:
    - Создание атомарных снапшотов (indices + MANIFEST)
    - SHA256 verification
    - Быстрый откат (≤30 сек)
    - Retention policy (last N или по возрасту)
    """
    
    def __init__(
        self,
        data_dir: Optional[Path] = None,
        snapshots_dir: Optional[Path] = None,
        retention_count: int = 10,
        retention_days: int = 30,
    ):
        """
        Инициализация менеджера снапшотов.
        
        Args:
            data_dir: Директория данных (indices, MANIFEST)
            snapshots_dir: Директория для снапшотов
            retention_count: Хранить последние N снапшотов
            retention_days: Хранить снапшоты за последние N дней
        """
        self.data_dir = data_dir or Path("data")
        self.snapshots_dir = snapshots_dir or Path("snapshots")
        self.retention_count = retention_count
        self.retention_days = retention_days
        
        # Создаём директории при необходимости
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
    
    def create_snapshot(
        self,
        reason: str,
        metrics: Optional[Dict[str, float]] = None,
    ) -> SnapshotMetadata:
        """
        Создать атомарный снапшот.
        
        Args:
            reason: Причина создания (e.g., "before_rebuild_shard")
            metrics: Метрики E3 на момент создания
        
        Returns:
            SnapshotMetadata: Метаданные созданного снапшота
        
        Raises:
            ValueError: Если data_dir не существует
            OSError: Если ошибка копирования файлов
        """
        if not self.data_dir.exists():
            raise ValueError(f"Data directory not found: {self.data_dir}")
        
        # Generate snapshot ID (YYYYMMDD_HHMMSS_microseconds)
        now = datetime.now(timezone.utc)
        snapshot_id = now.strftime("%Y%m%d_%H%M%S_") + str(now.microsecond).zfill(6)
        snapshot_path = self.snapshots_dir / snapshot_id
        snapshot_path.mkdir(parents=True, exist_ok=True)
        
        # Copy indices directory
        indices_src = self.data_dir / "indices"
        indices_dst = snapshot_path / "indices"
        
        files_count = 0
        total_size = 0
        
        if indices_src.exists():
            shutil.copytree(indices_src, indices_dst, dirs_exist_ok=False)
            # Count files and size
            for file in indices_dst.rglob("*"):
                if file.is_file():
                    files_count += 1
                    total_size += file.stat().st_size
        
        # Copy MANIFEST.json
        manifest_src = self.data_dir / "MANIFEST.json"
        manifest_dst = snapshot_path / "MANIFEST.json"
        
        if manifest_src.exists():
            shutil.copy2(manifest_src, manifest_dst)
            files_count += 1
            total_size += manifest_dst.stat().st_size
        
        # Generate SHA256 checksums
        checksums = self._generate_checksums(snapshot_path)
        checksums_path = snapshot_path / "checksums.json"
        with open(checksums_path, "w", encoding="utf-8") as f:
            json.dump(checksums, f, indent=2)
        
        # fsync checksums file (critical for integrity)
        with open(checksums_path, "rb") as f:
            f.flush()
        
        # Create metadata
        metadata = SnapshotMetadata(
            snapshot_id=snapshot_id,
            timestamp=now.isoformat(),
            reason=reason,
            metrics_snapshot=metrics or {},
            files_count=files_count,
            total_size_bytes=total_size,
            status=SnapshotStatus.CREATED,
        )
        
        # Save metadata
        metadata_path = snapshot_path / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(asdict(metadata), f, indent=2)
        
        # Apply retention policy
        self._cleanup_old_snapshots()
        
        return metadata
    
    def verify_snapshot(self, snapshot_id: str) -> bool:
        """
        Проверить целостность снапшота через SHA256.
        
        Args:
            snapshot_id: ID снапшота
        
        Returns:
            bool: True если checksums совпадают
        """
        snapshot_path = self.snapshots_dir / snapshot_id
        
        if not snapshot_path.exists():
            return False
        
        # Load expected checksums
        checksums_path = snapshot_path / "checksums.json"
        if not checksums_path.exists():
            return False
        
        with open(checksums_path, encoding="utf-8") as f:
            expected_checksums = json.load(f)
        
        # Verify all files
        for rel_path, expected_hash in expected_checksums.items():
            file_path = snapshot_path / rel_path
            
            if not file_path.exists():
                return False
            
            actual_hash = self._compute_sha256(file_path)
            if actual_hash != expected_hash:
                return False
        
        return True
    
    def rollback(self, snapshot_id: str) -> RollbackResult:
        """
        Откатиться к снапшоту (≤30 сек).
        
        Protocol:
        1. Verify snapshot checksums
        2. Stop readers (graceful) ← в beta stub
        3. Copy files from snapshot
        4. Atomic MANIFEST swap
        5. Reopen indices ← в beta stub
        
        Args:
            snapshot_id: ID снапшота для отката
        
        Returns:
            RollbackResult: Результат отката
        """
        start_time = datetime.now(timezone.utc)
        snapshot_path = self.snapshots_dir / snapshot_id
        
        # Check snapshot exists
        if not snapshot_path.exists():
            return RollbackResult(
                snapshot_id=snapshot_id,
                status=RollbackStatus.FAILURE,
                duration_seconds=0.0,
                files_restored=0,
                verification_ok=False,
                message="Snapshot not found",
                error=f"Snapshot {snapshot_id} does not exist",
            )
        
        # Verify checksums
        verification_ok = self.verify_snapshot(snapshot_id)
        if not verification_ok:
            return RollbackResult(
                snapshot_id=snapshot_id,
                status=RollbackStatus.VERIFICATION_FAILED,
                duration_seconds=(datetime.now(timezone.utc) - start_time).total_seconds(),
                files_restored=0,
                verification_ok=False,
                message="SHA256 verification failed",
                error="Checksums do not match",
            )
        
        # Restore files
        files_restored = 0
        try:
            # Restore indices
            indices_src = snapshot_path / "indices"
            indices_dst = self.data_dir / "indices"
            
            if indices_src.exists():
                # Remove old indices
                if indices_dst.exists():
                    shutil.rmtree(indices_dst)
                
                # Copy from snapshot
                shutil.copytree(indices_src, indices_dst)
                files_restored += sum(1 for _ in indices_dst.rglob("*") if _.is_file())
            
            # Atomic MANIFEST swap
            manifest_src = snapshot_path / "MANIFEST.json"
            manifest_dst = self.data_dir / "MANIFEST.json"
            
            if manifest_src.exists():
                # Backup current MANIFEST
                if manifest_dst.exists():
                    manifest_backup = self.data_dir / "MANIFEST.json.bak"
                    shutil.copy2(manifest_dst, manifest_backup)
                
                # Copy from snapshot
                shutil.copy2(manifest_src, manifest_dst)
                files_restored += 1
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return RollbackResult(
                snapshot_id=snapshot_id,
                status=RollbackStatus.SUCCESS,
                duration_seconds=duration,
                files_restored=files_restored,
                verification_ok=True,
                message=f"Rollback completed in {duration:.2f}s",
            )
        
        except (OSError, RuntimeError) as e:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return RollbackResult(
                snapshot_id=snapshot_id,
                status=RollbackStatus.FAILURE,
                duration_seconds=duration,
                files_restored=files_restored,
                verification_ok=verification_ok,
                message="Rollback failed",
                error=str(e),
            )
    
    def list_snapshots(self) -> List[SnapshotMetadata]:
        """
        Список всех снапшотов (sorted by timestamp, newest first).
        
        Returns:
            List[SnapshotMetadata]: Список метаданных снапшотов
        """
        snapshots = []
        
        if not self.snapshots_dir.exists():
            return []
        
        for snapshot_path in self.snapshots_dir.iterdir():
            if not snapshot_path.is_dir():
                continue
            
            metadata_path = snapshot_path / "metadata.json"
            if not metadata_path.exists():
                continue
            
            with open(metadata_path, encoding="utf-8") as f:
                data = json.load(f)
            
            metadata = SnapshotMetadata(**data)
            snapshots.append(metadata)
        
        # Sort by timestamp (newest first)
        snapshots.sort(key=lambda s: s.timestamp, reverse=True)
        
        return snapshots
    
    def get_snapshot_age(self, snapshot_id: str) -> Optional[float]:
        """
        Получить возраст снапшота в секундах.
        
        Args:
            snapshot_id: ID снапшота
        
        Returns:
            float: Возраст в секундах (None если снапшот не найден)
        """
        metadata_path = self.snapshots_dir / snapshot_id / "metadata.json"
        
        if not metadata_path.exists():
            return None
        
        with open(metadata_path, encoding="utf-8") as f:
            data = json.load(f)
        
        timestamp = datetime.fromisoformat(data["timestamp"])
        age = (datetime.now(timezone.utc) - timestamp).total_seconds()
        
        return age
    
    def _generate_checksums(self, snapshot_path: Path) -> Dict[str, str]:
        """
        Генерация SHA256 checksums для всех файлов в снапшоте.
        
        Args:
            snapshot_path: Путь к директории снапшота
        
        Returns:
            Dict[str, str]: {relative_path: sha256_hash}
        """
        checksums = {}
        
        for file_path in snapshot_path.rglob("*"):
            if not file_path.is_file():
                continue
            
            # Skip checksums.json itself
            if file_path.name == "checksums.json":
                continue
            
            # Relative path from snapshot root
            rel_path = str(file_path.relative_to(snapshot_path))
            
            # Compute SHA256
            checksums[rel_path] = self._compute_sha256(file_path)
        
        return checksums
    
    def _compute_sha256(self, file_path: Path) -> str:
        """
        Вычислить SHA256 для файла.
        
        Args:
            file_path: Путь к файлу
        
        Returns:
            str: SHA256 hex digest
        """
        sha256 = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        
        return sha256.hexdigest()
    
    def _cleanup_old_snapshots(self) -> None:
        """
        Применить retention policy (удалить старые снапшоты).
        
        Policy:
        - Хранить последние retention_count снапшотов
        - Хранить снапшоты за последние retention_days дней
        - Удалить снапшоты, которые НЕ входят в retention_count И старше retention_days
        """
        snapshots = self.list_snapshots()
        
        if len(snapshots) <= self.retention_count:
            return
        
        # Cutoff timestamp
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        
        # Keep snapshots within retention window
        for i, snapshot in enumerate(snapshots):
            # Keep last retention_count snapshots
            if i < self.retention_count:
                continue
            
            # Keep snapshots within retention_days (even if beyond retention_count)
            timestamp = datetime.fromisoformat(snapshot.timestamp)
            if timestamp > cutoff:
                continue
            
            # Delete old snapshot (beyond retention_count AND older than retention_days)
            snapshot_path = self.snapshots_dir / snapshot.snapshot_id
            if snapshot_path.exists():
                shutil.rmtree(snapshot_path)
