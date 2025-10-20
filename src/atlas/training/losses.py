# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna
#
# Atlas - Semantic Space Control Panel
# Интерпретируемое семантическое пространство

"""
Loss functions for hierarchical semantic space training (v0.2+)

Includes specialized losses for:
- Axis orthogonality: Encourages semantic dimensions to be independent
- L1 sparsity: Promotes sparse representations
- Router entropy: Balances routing decisions in hierarchical models
"""

from typing import Optional
import torch
import torch.nn.functional as F


def orthogonality_loss(
    axes: torch.Tensor, reduction: str = "mean"
) -> torch.Tensor:
    """
    Orthogonality loss to encourage independent semantic dimensions.

    Penalizes non-orthogonal axes by minimizing off-diagonal elements
    of the Gram matrix (axes^T @ axes). When axes are orthonormal,
    the Gram matrix is the identity matrix.

    Formula:
        loss = sum(|G_ij|) for i != j, where G = axes^T @ axes

    Args:
        axes: (D, D) matrix where rows are axis vectors (e.g., 5x5 for 5D space)
              or (B, D, D) batch of axis matrices
        reduction: 'mean', 'sum', or 'none'

    Returns:
        Scalar orthogonality loss (or per-batch if reduction='none')

    Example:
        >>> # 5D semantic space with 5 axis vectors
        >>> axes = torch.randn(5, 5)
        >>> loss = orthogonality_loss(axes)
        >>> loss.item()  # Should be > 0 for non-orthogonal axes
        1.234

    Notes:
        - Perfect orthogonality: loss = 0
        - Can be combined with normalization constraint (unit norm axes)
        - Useful for maintaining interpretable, independent dimensions
    """
    if axes.dim() == 2:
        # Single matrix: (D, D)
        axes = axes.unsqueeze(0)  # (1, D, D)
    
    # Compute Gram matrix: G = axes @ axes^T
    # Shape: (B, D, D)
    gram = torch.bmm(axes, axes.transpose(-2, -1))
    
    # Extract off-diagonal elements
    # Create mask for off-diagonal elements
    batch_size, dim, _ = gram.shape
    mask = ~torch.eye(dim, dtype=torch.bool, device=gram.device)
    mask = mask.unsqueeze(0).expand(batch_size, -1, -1)
    
    # Sum absolute values of off-diagonal elements
    off_diagonal = torch.abs(gram[mask])
    
    if reduction == "mean":
        # Average over all off-diagonal elements
        return torch.mean(off_diagonal)
    elif reduction == "sum":
        return torch.sum(off_diagonal)
    elif reduction == "none":
        # Return per-batch losses
        off_diag_per_batch = off_diagonal.reshape(batch_size, -1)
        return torch.sum(off_diag_per_batch, dim=-1)
    else:
        raise ValueError(f"reduction must be 'mean', 'sum', or 'none', got {reduction}")


def l1_sparsity_loss(
    vectors: torch.Tensor, reduction: str = "mean"
) -> torch.Tensor:
    """
    L1 sparsity loss to encourage sparse representations.

    Promotes sparsity by penalizing the L1 norm (sum of absolute values).
    Sparse representations are desirable for interpretability and
    efficient storage.

    Formula:
        loss = sum(|x_i|) for all elements in vectors

    Args:
        vectors: (B, D) batch of vectors, or (B, ..., D) arbitrary shape
        reduction: 'mean', 'sum', or 'none'

    Returns:
        Scalar sparsity loss (or per-sample if reduction='none')

    Example:
        >>> # Batch of 32 5D semantic vectors
        >>> vectors = torch.randn(32, 5)
        >>> loss = l1_sparsity_loss(vectors)
        >>> loss.item()  # Lower is sparser
        42.5

    Notes:
        - Zero loss means all elements are zero (maximally sparse)
        - Can be weighted to balance with other losses
        - Often combined with reconstruction loss:
          total_loss = reconstruct_loss + lambda_sparse * l1_sparsity_loss
    """
    # Compute L1 norm per sample
    # Sum over all dimensions except batch dimension
    if vectors.dim() == 1:
        # Single vector
        l1_norm = torch.abs(vectors).sum()
        if reduction == "none":
            return l1_norm.unsqueeze(0)
        return l1_norm
    
    # Batch of vectors
    l1_norm = torch.abs(vectors).sum(dim=tuple(range(1, vectors.dim())))
    
    if reduction == "mean":
        return torch.mean(l1_norm)
    elif reduction == "sum":
        return torch.sum(l1_norm)
    elif reduction == "none":
        return l1_norm
    else:
        raise ValueError(f"reduction must be 'mean', 'sum', or 'none', got {reduction}")


def router_entropy_loss(
    router_probs: torch.Tensor, 
    reduction: str = "mean",
    min_entropy: bool = False
) -> torch.Tensor:
    """
    Router entropy loss for balancing routing decisions in hierarchical models.

    Encourages balanced routing across all branches (experts/dimensions).
    By default, maximizes entropy (uniform distribution). Can also
    minimize entropy (peaked distribution) if min_entropy=True.

    Formula (maximize entropy):
        loss = -sum(p_i * log(p_i))  # Negative entropy (minimize negative = maximize)
        
    Formula (minimize entropy):
        loss = -sum(p_i * log(p_i))  # Entropy itself

    Args:
        router_probs: (B, K) router probabilities for K branches (should sum to 1)
                     or (B, ..., K) arbitrary shape with K in last dimension
        reduction: 'mean', 'sum', or 'none'
        min_entropy: If True, minimize entropy (peaked). If False (default), maximize entropy (uniform)

    Returns:
        Scalar entropy loss (or per-sample if reduction='none')

    Example:
        >>> # Batch of 32 samples, routing to 5 dimensions
        >>> router_probs = F.softmax(torch.randn(32, 5), dim=-1)
        >>> loss = router_entropy_loss(router_probs)
        >>> loss.item()  # Negative entropy (maximizing entropy)
        -1.456

        >>> # For minimizing entropy (peaked routing)
        >>> loss = router_entropy_loss(router_probs, min_entropy=True)
        >>> loss.item()  # Positive entropy (minimizing entropy)
        1.456

    Notes:
        - Maximum entropy for K branches: log(K) (uniform distribution)
        - Minimum entropy: 0 (one-hot distribution)
        - router_probs should sum to 1 along last dimension
        - Useful for load balancing in mixture-of-experts or hierarchical routing
    """
    # Ensure probabilities are in valid range
    eps = 1e-10
    router_probs = torch.clamp(router_probs, min=eps, max=1.0)
    
    # Compute entropy: -sum(p * log(p))
    log_probs = torch.log(router_probs)
    entropy = -torch.sum(router_probs * log_probs, dim=-1)
    
    # If maximizing entropy, we minimize negative entropy
    if not min_entropy:
        entropy = -entropy
    
    if reduction == "mean":
        return torch.mean(entropy)
    elif reduction == "sum":
        return torch.sum(entropy)
    elif reduction == "none":
        return entropy
    else:
        raise ValueError(f"reduction must be 'mean', 'sum', or 'none', got {reduction}")


# Configuration constants
LOSS_CONFIG = {
    "orthogonality": {
        "default_weight": 0.1,
        "description": "Weight for orthogonality loss in combined training",
    },
    "l1_sparsity": {
        "default_weight": 0.01,
        "description": "Weight for L1 sparsity loss in combined training",
    },
    "router_entropy": {
        "default_weight": 0.05,
        "description": "Weight for router entropy loss in combined training",
        "target_entropy": None,  # Can be set to log(K) for uniform target
    },
}


# TODO: Implement in v0.2.1+
"""
ADVANCED LOSS FUNCTIONS (v0.2.1+):

1. Contrastive loss:
   - Encourage similar concepts to be close, dissimilar to be far
   - InfoNCE or triplet loss variants

2. Diversity loss:
   - Encourage different dimensions to capture different aspects
   - Based on mutual information or correlation

3. Consistency loss:
   - Encourage consistency across different augmentations
   - Similar to SimCLR/BYOL approaches

4. Hierarchical consistency:
   - Parent and child nodes should be semantically related
   - Encourage smooth transitions in hierarchical tree

5. Adversarial regularization:
   - Use adversarial training to improve robustness
   - Domain adaptation for cross-lingual/cross-domain

6. Reconstruction loss variants:
   - Perceptual loss using pre-trained models
   - Feature matching loss
"""
