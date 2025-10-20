# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna
#
# Atlas - Semantic Space Control Panel
# Интерпретируемое семантическое пространство

"""
Knowledge distillation for hierarchical semantic spaces (v0.2+)
Teacher→Student distillation: 1536D embeddings → 5D hierarchical
"""

from typing import Optional

import torch
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

    # Cosine similarity: dot product of normalized vectors
    cos_sim = torch.sum(student_norm * teacher_norm, dim=-1)  # (B,)

    # Loss: 1 - cosine_sim
    # When perfectly aligned (cos_sim=1), loss=0
    # When anti-aligned (cos_sim=-1), loss=2
    loss = 1.0 - cos_sim

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
