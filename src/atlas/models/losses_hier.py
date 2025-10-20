# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna
#
# Atlas - Semantic Space Control Panel
# Интерпретируемое семантическое пространство

"""
Hierarchical losses for v0.2+
Regularization techniques for disentangled hierarchical semantic spaces
"""

from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


def ortho_loss(W: torch.Tensor) -> torch.Tensor:
    """
    Orthogonality regularization loss.

    Encourages columns of projection matrix to be orthogonal.
    Loss = ||W^T W - I||_F (Frobenius norm)

    Args:
        W: (out_features, in_features) weight matrix

    Returns:
        Scalar loss (0 when W is orthogonal)

    Example:
        >>> W = torch.randn(5, 100)
        >>> loss = ortho_loss(W)
        >>> loss.item() > 0
        True
    """
    # Gram matrix: W^T W
    gram = W.t() @ W

    # Identity matrix
    I = torch.eye(W.size(1), device=W.device, dtype=W.dtype)

    # Frobenius norm of (Gram - I)
    loss = torch.norm(gram - I, p="fro")

    return loss


def l1_sparsity(x: torch.Tensor, reduction: str = "mean") -> torch.Tensor:
    """
    L1 sparsity regularization.

    Encourages activations/weights to be sparse (many zeros).
    Loss = mean(|x|) or sum(|x|)

    Args:
        x: Input tensor (any shape)
        reduction: 'mean' or 'sum'

    Returns:
        Scalar sparsity loss

    Example:
        >>> x = torch.randn(5, 100)
        >>> loss = l1_sparsity(x)
        >>> loss.item() > 0
        True
    """
    abs_x = torch.abs(x)

    if reduction == "mean":
        return torch.mean(abs_x)
    elif reduction == "sum":
        return torch.sum(abs_x)
    else:
        raise ValueError(f"reduction must be 'mean' or 'sum', got {reduction}")


def router_entropy(
    logits: torch.Tensor, temperature: float = 1.0, eps: float = 1e-9
) -> torch.Tensor:
    """
    Router entropy regularization.

    Encourages router (which selects which child nodes to expand)
    to have high entropy (uniform distribution over choices).

    Loss = -mean(sum(p * log(p))) where p = softmax(logits / tau)

    Args:
        logits: (B, K) unnormalized routing scores
        temperature: Softmax temperature (higher = softer distribution)
        eps: Small constant for numerical stability

    Returns:
        Scalar entropy loss (negative entropy)

    Example:
        >>> logits = torch.randn(32, 4)  # 32 samples, 4 routes
        >>> loss = router_entropy(logits)
        >>> loss.item() > 0  # High entropy is desirable
        True
    """
    # Softmax with temperature
    p = F.softmax(logits / temperature, dim=-1)

    # Entropy: -sum(p * log(p))
    entropy = -torch.sum(p * torch.log(p + eps), dim=-1)

    # Return negative entropy as loss (we want to maximize it)
    # So minimizing -entropy = maximizing entropy
    loss = -torch.mean(entropy)

    return loss


def cosine_loss(pred: torch.Tensor, target: torch.Tensor, reduction: str = "mean") -> torch.Tensor:
    """
    Cosine similarity loss (1 - cosine_sim).

    Encourages predicted and target vectors to be aligned.

    Args:
        pred: (B, D) predicted vectors
        target: (B, D) target vectors
        reduction: 'mean' or 'sum'

    Returns:
        Scalar loss
    """
    # Normalize
    pred_norm = F.normalize(pred, dim=-1, p=2)
    target_norm = F.normalize(target, dim=-1, p=2)

    # Cosine similarity: sum(u * v) for normalized u, v
    cos_sim = torch.sum(pred_norm * target_norm, dim=-1)

    # Loss: 1 - cos_sim (ranges 0..2, 0 when aligned)
    loss = 1.0 - cos_sim

    if reduction == "mean":
        return torch.mean(loss)
    elif reduction == "sum":
        return torch.sum(loss)
    else:
        raise ValueError(f"reduction must be 'mean' or 'sum', got {reduction}")


def hierarchical_regularization(
    projection_matrices: list,
    router_logits: Optional[torch.Tensor] = None,
    activations: Optional[torch.Tensor] = None,
    lambda_ortho: float = 0.1,
    lambda_sparsity: float = 0.01,
    lambda_entropy: float = 0.01,
) -> torch.Tensor:
    """
    Combined hierarchical regularization.

    Args:
        projection_matrices: List of (out, in) weight matrices
        router_logits: (B, K) routing logits
        activations: (B, ...) activation tensors
        lambda_ortho: Weight for orthogonality loss
        lambda_sparsity: Weight for sparsity loss
        lambda_entropy: Weight for entropy loss

    Returns:
        Scalar combined loss
    """
    total_loss = 0.0

    # Orthogonality loss on all projection matrices
    if projection_matrices:
        ortho_terms = [ortho_loss(W) for W in projection_matrices]
        total_loss += lambda_ortho * torch.stack(ortho_terms).mean()

    # Sparsity loss on activations
    if activations is not None:
        total_loss += lambda_sparsity * l1_sparsity(activations)

    # Entropy loss on router
    if router_logits is not None:
        total_loss += lambda_entropy * router_entropy(router_logits)

    return total_loss


# Constants for typical λ values
DEFAULT_ORTHO_LAMBDA = 0.1  # Enforce orthogonality moderately
DEFAULT_SPARSITY_LAMBDA = 0.01  # Light sparsity
DEFAULT_ENTROPY_LAMBDA = 0.01  # Encourage routing exploration
