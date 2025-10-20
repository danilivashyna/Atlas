# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna
#
# Atlas - Semantic Space Control Panel
# Интерпретируемое семантическое пространство

"""
Knowledge distillation for hierarchical semantic spaces (v0.2+)
Teacher→Student distillation: 1536D embeddings → 5D hierarchical
"""

from typing import Optional, Dict, Any, Callable
from pathlib import Path
import torch
import torch.nn as nn
import torch.nn.functional as F


def distill_loss(
    student_vec: torch.Tensor, teacher_vec: torch.Tensor, tau: float = 0.1, reduction: str = "mean"
) -> torch.Tensor:
    """
    Knowledge distillation loss using cosine similarity.

    Encourages student (5D) and teacher (1536D) representations
    to be aligned, allowing transfer of knowledge from large models.

    Loss = 1 - cosine_sim(student, teacher)

    Args:
        student_vec: (B, 5) or (B, D_student) semantic vectors
        teacher_vec: (B, 1536) or (B, D_teacher) teacher embeddings
        tau: Temperature for softmax (future: for KL divergence variant)
        reduction: 'mean' or 'sum'

    Returns:
        Scalar distillation loss

    Example:
        >>> student = torch.randn(32, 5)      # Hierarchical 5D
        >>> teacher = torch.randn(32, 1536)   # OpenAI embeddings
        >>> loss = distill_loss(student, teacher)
        >>> loss.item()
        0.45  # Typical value

    Notes:
        - Both vectors should ideally be L2-normalized
        - Can be combined with reconstruction loss:
          total_loss = alpha * distill_loss + (1-alpha) * reconstruct_loss
    """
    # Normalize both vectors
    student_norm = F.normalize(student_vec, dim=-1, p=2)
    teacher_norm = F.normalize(teacher_vec, dim=-1, p=2)

    # For distillation with different dimensions, we need to handle the mismatch
    # Option 1: Project to lower dimension (use first N dimensions)
    # Option 2: Use a learned projection (not implemented here for simplicity)
    # Option 3: Compute feature-level alignment using MSE after normalization
    
    # We'll use Option 3: MSE-based alignment after normalization
    # This measures how well the student's normalized representation
    # aligns with a projection of the teacher's representation
    
    if student_vec.shape[-1] == teacher_vec.shape[-1]:
        # Same dimensions: use cosine similarity
        cos_sim = torch.sum(student_norm * teacher_norm, dim=-1)  # (B,)
        loss = 1.0 - cos_sim
    else:
        # Different dimensions: use MSE after projection
        # Project teacher to student dimension using first components
        min_dim = min(student_vec.shape[-1], teacher_vec.shape[-1])
        
        # Take first min_dim components and compute MSE
        student_proj = student_norm[..., :min_dim]
        teacher_proj = teacher_norm[..., :min_dim]
        
        # MSE loss (per sample)
        loss = torch.mean((student_proj - teacher_proj) ** 2, dim=-1)  # (B,)

    if reduction == "mean":
        return torch.mean(loss)
    elif reduction == "sum":
        return torch.sum(loss)
    else:
        raise ValueError(f"reduction must be 'mean' or 'sum', got {reduction}")


def kl_distill_loss(
    student_logits: torch.Tensor,
    teacher_logits: torch.Tensor,
    tau: float = 1.0,
    reduction: str = "mean",
) -> torch.Tensor:
    """
    KL-divergence based distillation loss (variant for next versions).

    More suited for classification/routing decisions.

    Args:
        student_logits: (B, K) student logits
        teacher_logits: (B, K) teacher logits
        tau: Temperature (tau > 1 makes distributions softer)
        reduction: 'mean' or 'sum'

    Returns:
        Scalar KL loss

    Example:
        >>> student_logits = torch.randn(32, 4)  # Student routing decisions
        >>> teacher_logits = torch.randn(32, 4)  # Teacher routing
        >>> loss = kl_distill_loss(student_logits, teacher_logits, tau=2.0)
        >>> loss.item()
    """
    # Soft targets
    teacher_probs = F.softmax(teacher_logits / tau, dim=-1)

    # Student log probabilities
    student_log_probs = F.log_softmax(student_logits / tau, dim=-1)

    # KL divergence
    loss = F.kl_div(student_log_probs, teacher_probs, reduction=reduction)

    return loss


def combined_distill_loss(
    student_vec: torch.Tensor,
    teacher_vec: torch.Tensor,
    reconstruction_loss: Optional[torch.Tensor] = None,
    alpha: float = 0.5,
    tau: float = 0.1,
) -> torch.Tensor:
    """
    Combined distillation + reconstruction loss.

    Useful when training hierarchical encoder to match teacher embeddings
    while also maintaining reconstruction quality.

    Loss = alpha * distill_loss + (1 - alpha) * reconstruction_loss

    Args:
        student_vec: (B, 5) hierarchical vectors
        teacher_vec: (B, D) teacher embeddings
        reconstruction_loss: Scalar reconstruction loss (e.g., MSE)
        alpha: Weight for distillation loss
        tau: Temperature

    Returns:
        Scalar combined loss
    """
    if not 0 <= alpha <= 1:
        raise ValueError(f"alpha must be in [0, 1], got {alpha}")

    dist_loss = distill_loss(student_vec, teacher_vec, tau=tau)

    if reconstruction_loss is None:
        return dist_loss

    return alpha * dist_loss + (1 - alpha) * reconstruction_loss


def load_teacher_checkpoint(
    checkpoint_path: str,
    device: str = "cpu",
    map_location: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Load teacher model checkpoint from disk.
    
    Args:
        checkpoint_path: Path to checkpoint file (.pt or .pth)
        device: Device to load checkpoint on ('cpu', 'cuda')
        map_location: Optional custom map_location for torch.load
        
    Returns:
        Dictionary containing checkpoint state
        
    Raises:
        FileNotFoundError: If checkpoint doesn't exist
        RuntimeError: If checkpoint is corrupted
        
    Example:
        >>> checkpoint = load_teacher_checkpoint("teacher_1536d.pt")
        >>> teacher_embeddings = checkpoint.get("embeddings")
    """
    checkpoint_path = Path(checkpoint_path)
    
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
    
    # Determine map location
    if map_location is None:
        map_location = device
    
    try:
        checkpoint = torch.load(
            checkpoint_path,
            map_location=map_location,
            weights_only=False  # Allow loading full checkpoints
        )
    except Exception as e:
        raise RuntimeError(f"Failed to load checkpoint: {e}")
    
    return checkpoint


def create_curriculum_schedule(
    start_tau: float,
    end_tau: float,
    num_stages: int,
    schedule_type: str = "linear",
) -> Callable[[int], float]:
    """
    Create a curriculum learning temperature schedule.
    
    Curriculum learning gradually reduces temperature from warmer (softer)
    to cooler (sharper) targets, helping the student learn progressively.
    
    Args:
        start_tau: Initial temperature (higher = softer)
        end_tau: Final temperature (lower = sharper)
        num_stages: Number of curriculum stages
        schedule_type: Type of schedule ('linear', 'exponential', 'cosine')
        
    Returns:
        Function that maps stage number to temperature
        
    Example:
        >>> schedule = create_curriculum_schedule(4.0, 0.5, 5)
        >>> for stage in range(5):
        ...     print(f"Stage {stage}: tau={schedule(stage):.2f}")
        Stage 0: tau=4.00
        Stage 1: tau=3.12
        Stage 2: tau=2.25
        Stage 3: tau=1.38
        Stage 4: tau=0.50
    """
    if start_tau <= end_tau:
        raise ValueError(f"start_tau ({start_tau}) must be > end_tau ({end_tau})")
    
    if num_stages < 1:
        raise ValueError(f"num_stages must be >= 1, got {num_stages}")
    
    def linear_schedule(stage: int) -> float:
        progress = stage / max(1, num_stages - 1)
        return start_tau - (start_tau - end_tau) * progress
    
    def exponential_schedule(stage: int) -> float:
        progress = stage / max(1, num_stages - 1)
        ratio = end_tau / start_tau
        return start_tau * (ratio ** progress)
    
    def cosine_schedule(stage: int) -> float:
        import math
        progress = stage / max(1, num_stages - 1)
        cos_progress = (1 - math.cos(progress * math.pi)) / 2
        return start_tau - (start_tau - end_tau) * cos_progress
    
    if schedule_type == "linear":
        return linear_schedule
    elif schedule_type == "exponential":
        return exponential_schedule
    elif schedule_type == "cosine":
        return cosine_schedule
    else:
        raise ValueError(
            f"schedule_type must be 'linear', 'exponential', or 'cosine', got {schedule_type}"
        )


def curriculum_distill_step(
    student_vec: torch.Tensor,
    teacher_vec: torch.Tensor,
    stage: int,
    tau_schedule: Callable[[int], float],
    alpha: float = 0.5,
    reconstruction_loss: Optional[torch.Tensor] = None,
) -> tuple[torch.Tensor, float]:
    """
    Single curriculum distillation step.
    
    Computes distillation loss with curriculum-adjusted temperature.
    
    Args:
        student_vec: (B, D_student) student embeddings
        teacher_vec: (B, D_teacher) teacher embeddings
        stage: Current curriculum stage (0-indexed)
        tau_schedule: Function mapping stage to temperature
        alpha: Weight for distillation vs reconstruction loss
        reconstruction_loss: Optional reconstruction loss
        
    Returns:
        Tuple of (loss, current_tau)
        
    Example:
        >>> student = torch.randn(32, 5)
        >>> teacher = torch.randn(32, 1536)
        >>> schedule = create_curriculum_schedule(3.0, 0.5, 5)
        >>> loss, tau = curriculum_distill_step(student, teacher, stage=2, tau_schedule=schedule)
    """
    # Get temperature for current stage
    tau = tau_schedule(stage)
    
    # Compute distillation loss with current temperature
    dist_loss = distill_loss(student_vec, teacher_vec, tau=tau)
    
    # Combine with reconstruction loss if provided
    if reconstruction_loss is not None:
        loss = alpha * dist_loss + (1 - alpha) * reconstruction_loss
    else:
        loss = dist_loss
    
    return loss, tau


# Configuration constants
DISTILLATION_CONFIG = {
    "default_tau": 0.1,  # Lower tau = sharper targets
    "default_alpha": 0.5,  # Balance distillation vs reconstruction
    "typical_teacher_dim": 1536,  # OpenAI, most models
    "student_dim": 5,
}

# TODO: Implement in v0.2.1+
"""
ADVANCED DISTILLATION (v0.2.1+):

1. Multi-level distillation:
   - Match intermediate layer activations (hint learning)
   - Apply at each hierarchy level

2. Adaptive temperature:
   - Vary tau based on training progress
   - Warmer (higher) early, cooler (lower) later

3. Feature distillation:
   - Match not just vectors but also spatial relationships
   - Use Gram matrix similarity

4. Attention transfer:
   - From teacher attention maps to student
   - Especially useful for transformers

5. Contrastive distillation:
   - Distill relative relationships between samples
   - SimCLR/BYOL-like approach
"""
