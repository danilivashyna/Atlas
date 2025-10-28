# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Atlas Homeostasis Sleep & Consolidation (E4.6)

Nightly maintenance operations to optimize semantic space:
1. Defragmentation: Compact index files, remove tombstones
2. Vector compression: Reduce precision for stable embeddings
3. Threshold recalibration: Update policy thresholds based on drift metrics
4. Audit report: Summary of all consolidation actions

SleepManager orchestrates the consolidation sequence with double-confirmation
for threshold changes to prevent instability.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ConsolidationResult:
    """Result of a consolidation run."""
    
    run_id: Optional[str]
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    actions_performed: List[str]
    defrag_stats: Dict[str, Any]
    compression_stats: Dict[str, Any]
    threshold_changes: Dict[str, Any]
    success: bool
    errors: List[str]


class SleepManager:
    """
    Manages nightly consolidation operations.
    
    Consolidation sequence:
    1. Pre-snapshot (via SnapshotManager)
    2. Defragmentation (compact indices, remove tombstones)
    3. Vector compression (reduce precision for stable embeddings)
    4. Threshold recalibration (update policies based on drift)
    5. Post-snapshot (for rollback safety)
    6. Audit report (log all actions to WAL)
    
    Args:
        data_dir: Path to Atlas data directory (indices, MANIFEST)
        snapshot_manager: SnapshotManager instance for pre/post snapshots
        audit_logger: AuditLogger instance for WAL
        metrics: HomeostasisMetrics instance for observability
    """
    
    def __init__(
        self,
        data_dir: Path,
        snapshot_manager: Optional[Any] = None,
        audit_logger: Optional[Any] = None,
        metrics: Optional[Any] = None,
    ) -> None:
        """Initialize SleepManager."""
        self.data_dir = Path(data_dir)
        self.snapshot_manager = snapshot_manager
        self.audit_logger = audit_logger
        self.metrics = metrics
        
        # Consolidation parameters
        self.defrag_threshold = 0.3  # Defrag if fragmentation > 30%
        self.compression_age_days = 7  # Compress vectors older than 7 days
        self.threshold_confidence = 0.95  # Require 95% confidence for recalibration
    
    def run_consolidation(
        self,
        run_id: Optional[str] = None,
        dry_run: bool = False,
        skip_threshold_recalibration: bool = False,
    ) -> ConsolidationResult:
        """
        Run full consolidation sequence.
        
        Args:
            run_id: Idempotency key for this consolidation run
            dry_run: If True, simulate without making changes
            skip_threshold_recalibration: If True, skip threshold updates
        
        Returns:
            ConsolidationResult with stats and status
        """
        started_at = datetime.utcnow()
        actions: List[str] = []
        errors: List[str] = []
        
        logger.info(
            "Starting consolidation run_id=%s dry_run=%s", run_id, dry_run
        )
        
        # Step 0: Pre-snapshot
        if not dry_run and self.snapshot_manager:
            try:
                snap = self.snapshot_manager.create_snapshot(
                    reason=f"pre_consolidation_{run_id or 'auto'}"
                )
                actions.append(f"pre_snapshot:{snap['snapshot_id']}")
                logger.info("Pre-snapshot created: %s", snap["snapshot_id"])
            except Exception as e:
                logger.error("Pre-snapshot failed: %s", e)
                errors.append(f"pre_snapshot_error:{e}")
        
        # Step 1: Defragmentation
        defrag_stats = self._run_defragmentation(dry_run=dry_run)
        if defrag_stats["performed"]:
            actions.append("defragmentation")
        
        # Step 2: Vector compression
        compression_stats = self._run_vector_compression(dry_run=dry_run)
        if compression_stats["compressed_count"] > 0:
            actions.append("vector_compression")
        
        # Step 3: Threshold recalibration (double-confirm)
        threshold_changes: Dict[str, Any] = {}
        if not skip_threshold_recalibration:
            threshold_changes = self._run_threshold_recalibration(dry_run=dry_run)
            if len(threshold_changes.get("changes_applied", [])) > 0:
                actions.append("threshold_recalibration")
        
        # Step 4: Post-snapshot
        if not dry_run and self.snapshot_manager:
            try:
                snap = self.snapshot_manager.create_snapshot(
                    reason=f"post_consolidation_{run_id or 'auto'}"
                )
                actions.append(f"post_snapshot:{snap['snapshot_id']}")
                logger.info("Post-snapshot created: %s", snap["snapshot_id"])
            except Exception as e:
                logger.error("Post-snapshot failed: %s", e)
                errors.append(f"post_snapshot_error:{e}")
        
        # Step 5: Audit report
        finished_at = datetime.utcnow()
        duration = (finished_at - started_at).total_seconds()
        
        if self.audit_logger and not dry_run:
            try:
                self.audit_logger.log_consolidation_completed(
                    run_id=run_id,
                    duration=duration,
                    actions=actions,
                    defrag_stats=defrag_stats,
                    compression_stats=compression_stats,
                    threshold_changes=threshold_changes,
                )
            except Exception as e:
                logger.error("Audit logging failed: %s", e)
                errors.append(f"audit_error:{e}")
        
        # Update metrics
        if self.metrics and not dry_run:
            try:
                self.metrics.update_consolidation_duration(duration)
                self.metrics.increment_consolidation_count(
                    status="success" if not errors else "partial"
                )
            except Exception as e:
                logger.error("Metrics update failed: %s", e)
        
        success = len(errors) == 0
        logger.info(
            "Consolidation completed run_id=%s duration=%.2fs success=%s",
            run_id,
            duration,
            success,
        )
        
        return ConsolidationResult(
            run_id=run_id,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration,
            actions_performed=actions,
            defrag_stats=defrag_stats,
            compression_stats=compression_stats,
            threshold_changes=threshold_changes,
            success=success,
            errors=errors,
        )
    
    def _run_defragmentation(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Run index defragmentation.
        
        Compacts index files by removing tombstones and consolidating
        fragmented segments. Only runs if fragmentation > threshold.
        
        Args:
            dry_run: If True, calculate stats without making changes
        
        Returns:
            Dict with defrag stats: fragmentation_before, fragmentation_after,
            bytes_reclaimed, performed
        """
        logger.info("Running defragmentation dry_run=%s", dry_run)
        
        # Stub implementation: real version would analyze indices
        fragmentation_before = 0.35  # 35% fragmented (stub)
        bytes_before = 1024 * 1024 * 100  # 100 MB (stub)
        
        if fragmentation_before < self.defrag_threshold:
            logger.info(
                "Fragmentation %.2f%% below threshold %.2f%%, skipping",
                fragmentation_before * 100,
                self.defrag_threshold * 100,
            )
            return {
                "performed": False,
                "fragmentation_before": fragmentation_before,
                "reason": "below_threshold",
            }
        
        if not dry_run:
            # Real implementation would:
            # 1. Read all index shards
            # 2. Filter out tombstoned entries
            # 3. Rewrite compacted shards
            # 4. Update MANIFEST
            time.sleep(0.1)  # Simulate work
        
        fragmentation_after = 0.05  # 5% after defrag (stub)
        bytes_after = bytes_before * (1 - fragmentation_before + fragmentation_after)
        bytes_reclaimed = bytes_before - bytes_after
        
        return {
            "performed": not dry_run,
            "fragmentation_before": fragmentation_before,
            "fragmentation_after": fragmentation_after,
            "bytes_before": bytes_before,
            "bytes_after": int(bytes_after),
            "bytes_reclaimed": int(bytes_reclaimed),
        }
    
    def _run_vector_compression(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Run vector compression for stable embeddings.
        
        Reduces precision (float32 → float16) for vectors that haven't
        changed in compression_age_days. This saves storage without
        significant quality loss for stable content.
        
        Args:
            dry_run: If True, calculate stats without making changes
        
        Returns:
            Dict with compression stats: candidates, compressed_count,
            bytes_saved, quality_loss
        """
        logger.info("Running vector compression dry_run=%s", dry_run)
        
        # Stub implementation: real version would:
        # 1. Query vectors by last_modified < (now - compression_age_days)
        # 2. Convert float32 → float16 for stable vectors
        # 3. Measure quality loss via dot product drift
        
        candidates = 1500  # Vectors older than threshold (stub)
        
        if not dry_run:
            time.sleep(0.1)  # Simulate work
            compressed_count = candidates
        else:
            compressed_count = 0
        
        bytes_per_vector_before = 5 * 4  # 5 dims × 4 bytes (float32)
        bytes_per_vector_after = 5 * 2  # 5 dims × 2 bytes (float16)
        bytes_saved = candidates * (bytes_per_vector_before - bytes_per_vector_after)
        
        return {
            "candidates": candidates,
            "compressed_count": compressed_count,
            "bytes_saved": bytes_saved,
            "quality_loss": 0.001,  # Avg dot product drift (stub)
        }
    
    def _run_threshold_recalibration(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Recalibrate policy thresholds based on drift metrics.
        
        Analyzes recent h_coherence and h_stability metrics to determine
        if policy thresholds need adjustment. Requires double-confirmation:
        - Statistical confidence > threshold_confidence (95%)
        - Manual approval flag in policy config
        
        Args:
            dry_run: If True, propose changes without applying
        
        Returns:
            Dict with threshold changes: proposed, applied, confidence
        """
        logger.info("Running threshold recalibration dry_run=%s", dry_run)
        
        # Stub implementation: real version would:
        # 1. Query h_coherence/h_stability from last N days
        # 2. Calculate percentiles (P50, P95, P99)
        # 3. Propose threshold updates if drift detected
        # 4. Require manual approval flag before applying
        
        # Simulate analysis
        current_coherence_threshold = 0.85
        observed_p50 = 0.92  # Recent median h_coherence.sp
        observed_p95 = 0.88  # Recent P95
        
        # Propose raising threshold if P95 consistently above current
        proposed_threshold = 0.88 if observed_p95 > current_coherence_threshold else None
        
        changes_proposed = []
        changes_applied = []
        
        if proposed_threshold:
            change = {
                "policy": "coherence_degradation",
                "parameter": "h_coherence.sp_threshold",
                "current": current_coherence_threshold,
                "proposed": proposed_threshold,
                "confidence": 0.96,
                "reason": f"P95={observed_p95:.2f} > current={current_coherence_threshold}",
            }
            changes_proposed.append(change)
            
            # Double-confirm: check manual approval flag
            manual_approval = False  # Stub: read from config
            
            if not dry_run and manual_approval:
                # Apply change (update policy config)
                changes_applied.append(change)
                logger.info(
                    "Threshold updated: %s -> %.2f",
                    change["parameter"],
                    proposed_threshold,
                )
            else:
                logger.warning(
                    "Threshold change requires manual approval: %s",
                    change["parameter"],
                )
        
        return {
            "changes_proposed": changes_proposed,
            "changes_applied": changes_applied,
            "confidence": 0.96 if changes_proposed else 1.0,
        }


def create_sleep_manager(
    data_dir: Path,
    snapshot_manager: Optional[Any] = None,
    audit_logger: Optional[Any] = None,
    metrics: Optional[Any] = None,
) -> SleepManager:
    """
    Create SleepManager instance.
    
    Args:
        data_dir: Path to Atlas data directory
        snapshot_manager: SnapshotManager instance (optional)
        audit_logger: AuditLogger instance (optional)
        metrics: HomeostasisMetrics instance (optional)
    
    Returns:
        SleepManager instance
    """
    return SleepManager(
        data_dir=data_dir,
        snapshot_manager=snapshot_manager,
        audit_logger=audit_logger,
        metrics=metrics,
    )
