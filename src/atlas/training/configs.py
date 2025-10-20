# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna
#
# Atlas - Semantic Space Control Panel
# Интерпретируемое семантическое пространство

"""
Configuration dataclasses for distillation training (v0.2+).

Provides structured configuration for teacher-student distillation,
including curriculum learning and checkpoint management.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class DistillationConfig:
    """
    Configuration for knowledge distillation from teacher to student.
    
    Attributes:
        teacher_checkpoint: Path to teacher model checkpoint (.pt or .pth)
        teacher_dim: Dimensionality of teacher embeddings (e.g., 1536 for OpenAI)
        student_dim: Dimensionality of student embeddings (e.g., 5 for hierarchical)
        tau: Temperature for distillation (higher = softer targets)
        alpha: Weight for distillation loss vs reconstruction loss [0, 1]
        loss_type: Type of distillation loss ('cosine' or 'kl')
        device: Device to run on ('cpu', 'cuda', 'auto')
        curriculum: Enable curriculum learning
        curriculum_stages: Number of curriculum stages
        curriculum_tau_schedule: Temperature schedule for curriculum (start, end)
    
    Example:
        >>> config = DistillationConfig(
        ...     teacher_checkpoint="models/teacher_1536d.pt",
        ...     teacher_dim=1536,
        ...     student_dim=5,
        ...     tau=2.0,
        ...     alpha=0.7
        ... )
    """
    
    # Model architecture
    teacher_checkpoint: Optional[str] = None
    teacher_dim: int = 1536
    student_dim: int = 5
    
    # Loss configuration
    tau: float = 1.0
    alpha: float = 0.5
    loss_type: str = "cosine"  # 'cosine' or 'kl'
    
    # Hardware
    device: str = "cpu"
    
    # Curriculum learning
    curriculum: bool = False
    curriculum_stages: int = 3
    curriculum_tau_schedule: tuple = (3.0, 0.5)  # (start_tau, end_tau)
    
    # Additional training params
    batch_size: int = 32
    learning_rate: float = 1e-4
    max_epochs: int = 100
    
    # Checkpoint saving
    save_dir: str = "checkpoints"
    save_every: int = 10  # Save every N epochs
    
    # Validation
    validation_split: float = 0.1
    early_stopping_patience: int = 5
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if not 0 <= self.alpha <= 1:
            raise ValueError(f"alpha must be in [0, 1], got {self.alpha}")
        
        if self.tau <= 0:
            raise ValueError(f"tau must be positive, got {self.tau}")
        
        if self.loss_type not in ["cosine", "kl"]:
            raise ValueError(f"loss_type must be 'cosine' or 'kl', got {self.loss_type}")
        
        if self.device not in ["cpu", "cuda", "auto"]:
            raise ValueError(f"device must be 'cpu', 'cuda', or 'auto', got {self.device}")
        
        if self.curriculum:
            if self.curriculum_stages < 1:
                raise ValueError(f"curriculum_stages must be >= 1, got {self.curriculum_stages}")
            
            start_tau, end_tau = self.curriculum_tau_schedule
            if start_tau <= end_tau:
                raise ValueError(
                    f"curriculum_tau_schedule start ({start_tau}) "
                    f"must be > end ({end_tau})"
                )
    
    def get_tau_for_stage(self, stage: int) -> float:
        """
        Get temperature for a specific curriculum stage.
        
        Args:
            stage: Current curriculum stage (0-indexed)
        
        Returns:
            Temperature value for this stage
        """
        if not self.curriculum:
            return self.tau
        
        start_tau, end_tau = self.curriculum_tau_schedule
        progress = stage / max(1, self.curriculum_stages - 1)
        return start_tau - (start_tau - end_tau) * progress
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "teacher_checkpoint": self.teacher_checkpoint,
            "teacher_dim": self.teacher_dim,
            "student_dim": self.student_dim,
            "tau": self.tau,
            "alpha": self.alpha,
            "loss_type": self.loss_type,
            "device": self.device,
            "curriculum": self.curriculum,
            "curriculum_stages": self.curriculum_stages,
            "curriculum_tau_schedule": self.curriculum_tau_schedule,
            "batch_size": self.batch_size,
            "learning_rate": self.learning_rate,
            "max_epochs": self.max_epochs,
            "save_dir": self.save_dir,
            "save_every": self.save_every,
            "validation_split": self.validation_split,
            "early_stopping_patience": self.early_stopping_patience,
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "DistillationConfig":
        """Create config from dictionary."""
        return cls(**config_dict)


# Default configurations for common scenarios
DEFAULT_OPENAI_CONFIG = DistillationConfig(
    teacher_dim=1536,
    student_dim=5,
    tau=1.0,
    alpha=0.5,
    loss_type="cosine",
    device="cpu",
)

CURRICULUM_CONFIG = DistillationConfig(
    teacher_dim=1536,
    student_dim=5,
    tau=2.0,  # Will be overridden by curriculum schedule
    alpha=0.7,
    loss_type="cosine",
    device="cpu",
    curriculum=True,
    curriculum_stages=5,
    curriculum_tau_schedule=(4.0, 0.5),
)

FAST_CONFIG = DistillationConfig(
    teacher_dim=1536,
    student_dim=5,
    tau=0.5,
    alpha=0.5,
    loss_type="cosine",
    device="cpu",
    batch_size=64,
    max_epochs=20,
)
