"""
Tests for training loss functions
"""

import pytest
import torch
import math

from atlas.training.losses import (
    orthogonality_loss,
    l1_sparsity_loss,
    router_entropy_loss,
)


class TestOrthogonalityLoss:
    """Test orthogonality loss function"""

    def test_perfect_orthogonal_axes(self):
        """Test that perfect orthogonal axes have zero loss"""
        # Identity matrix is orthogonal
        axes = torch.eye(5)
        loss = orthogonality_loss(axes)
        assert torch.abs(loss) < 1e-6, "Orthogonal axes should have near-zero loss"

    def test_non_orthogonal_axes(self):
        """Test that non-orthogonal axes have positive loss"""
        # All ones matrix is maximally non-orthogonal
        axes = torch.ones(5, 5)
        loss = orthogonality_loss(axes)
        assert loss > 0, "Non-orthogonal axes should have positive loss"

    def test_batch_processing(self):
        """Test batch processing of multiple axis matrices"""
        # Batch of 3 matrices
        batch_axes = torch.stack([torch.eye(5), torch.ones(5, 5), torch.randn(5, 5)])
        loss = orthogonality_loss(batch_axes)
        assert loss.shape == torch.Size([]), "Should return scalar loss"
        assert loss >= 0, "Loss should be non-negative"

    def test_reduction_mean(self):
        """Test mean reduction"""
        axes = torch.randn(5, 5)
        loss = orthogonality_loss(axes, reduction="mean")
        assert loss.shape == torch.Size([]), "Mean reduction should return scalar"

    def test_reduction_sum(self):
        """Test sum reduction"""
        axes = torch.randn(5, 5)
        loss = orthogonality_loss(axes, reduction="sum")
        assert loss.shape == torch.Size([]), "Sum reduction should return scalar"

    def test_reduction_none(self):
        """Test no reduction (per-batch)"""
        batch_axes = torch.randn(3, 5, 5)
        loss = orthogonality_loss(batch_axes, reduction="none")
        assert loss.shape == torch.Size(
            [3]
        ), "No reduction should return per-batch loss"

    def test_invalid_reduction(self):
        """Test invalid reduction raises error"""
        axes = torch.randn(5, 5)
        with pytest.raises(ValueError):
            orthogonality_loss(axes, reduction="invalid")

    def test_gradient_flow(self):
        """Test that gradients flow through the loss"""
        axes = torch.randn(5, 5, requires_grad=True)
        loss = orthogonality_loss(axes)
        loss.backward()
        assert axes.grad is not None, "Gradients should be computed"
        assert not torch.all(axes.grad == 0), "Gradients should be non-zero"

    def test_normalized_axes(self):
        """Test with normalized axes"""
        # Random axes normalized to unit norm
        axes = torch.randn(5, 5)
        axes = torch.nn.functional.normalize(axes, dim=1, p=2)
        loss = orthogonality_loss(axes)
        assert loss >= 0, "Loss should be non-negative for normalized axes"


class TestL1SparsityLoss:
    """Test L1 sparsity loss function"""

    def test_zero_vector(self):
        """Test that zero vector has zero loss"""
        vectors = torch.zeros(32, 5)
        loss = l1_sparsity_loss(vectors)
        assert torch.abs(loss) < 1e-6, "Zero vector should have zero loss"

    def test_positive_loss(self):
        """Test that non-zero vectors have positive loss"""
        vectors = torch.randn(32, 5)
        loss = l1_sparsity_loss(vectors)
        assert loss > 0, "Non-zero vectors should have positive loss"

    def test_single_vector(self):
        """Test with single vector"""
        vector = torch.tensor([1.0, -2.0, 3.0, -4.0, 5.0])
        loss = l1_sparsity_loss(vector)
        # L1 norm: |1| + |-2| + |3| + |-4| + |5| = 15
        expected = 15.0
        assert torch.abs(loss - expected) < 1e-6, f"Expected {expected}, got {loss}"

    def test_batch_vectors(self):
        """Test with batch of vectors"""
        vectors = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
        loss = l1_sparsity_loss(vectors, reduction="mean")
        # Sample 1: |1| + |2| = 3, Sample 2: |3| + |4| = 7, Mean: (3 + 7) / 2 = 5
        expected = 5.0
        assert torch.abs(loss - expected) < 1e-6, f"Expected {expected}, got {loss}"

    def test_reduction_mean(self):
        """Test mean reduction"""
        vectors = torch.randn(32, 5)
        loss = l1_sparsity_loss(vectors, reduction="mean")
        assert loss.shape == torch.Size([]), "Mean reduction should return scalar"

    def test_reduction_sum(self):
        """Test sum reduction"""
        vectors = torch.randn(32, 5)
        loss = l1_sparsity_loss(vectors, reduction="sum")
        assert loss.shape == torch.Size([]), "Sum reduction should return scalar"

    def test_reduction_none(self):
        """Test no reduction (per-sample)"""
        vectors = torch.randn(32, 5)
        loss = l1_sparsity_loss(vectors, reduction="none")
        assert loss.shape == torch.Size(
            [32]
        ), "No reduction should return per-sample loss"

    def test_invalid_reduction(self):
        """Test invalid reduction raises error"""
        vectors = torch.randn(32, 5)
        with pytest.raises(ValueError):
            l1_sparsity_loss(vectors, reduction="invalid")

    def test_gradient_flow(self):
        """Test that gradients flow through the loss"""
        vectors = torch.randn(32, 5, requires_grad=True)
        loss = l1_sparsity_loss(vectors)
        loss.backward()
        assert vectors.grad is not None, "Gradients should be computed"

    def test_multidimensional_input(self):
        """Test with multidimensional input"""
        # 3D tensor: (batch, height, width)
        vectors = torch.randn(8, 10, 5)
        loss = l1_sparsity_loss(vectors)
        assert loss >= 0, "Loss should be non-negative"

    def test_absolute_values(self):
        """Test that negative values are correctly handled"""
        vectors = torch.tensor([[-1.0, -2.0, -3.0]])
        loss = l1_sparsity_loss(vectors)
        expected = 6.0  # |-1| + |-2| + |-3| = 6
        assert torch.abs(loss - expected) < 1e-6, f"Expected {expected}, got {loss}"


class TestRouterEntropyLoss:
    """Test router entropy loss function"""

    def test_uniform_distribution_max_entropy(self):
        """Test that uniform distribution has maximum entropy"""
        # Uniform distribution over 5 branches
        router_probs = torch.ones(32, 5) / 5.0
        loss = router_entropy_loss(router_probs, min_entropy=False)
        # Maximum entropy for 5 branches: log(5) ≈ 1.609
        # We minimize negative entropy, so loss should be negative
        assert (
            loss < 0
        ), "Uniform distribution should have negative loss (maximizing entropy)"

    def test_peaked_distribution_low_entropy(self):
        """Test that peaked distribution has low entropy"""
        # One-hot distribution (peaked)
        router_probs = torch.zeros(32, 5)
        router_probs[:, 0] = 1.0
        loss = router_entropy_loss(router_probs, min_entropy=False)
        # Near-zero entropy, so negative entropy is near zero (less negative)
        assert loss > -0.1, "Peaked distribution should have near-zero negative entropy"

    def test_min_entropy_mode(self):
        """Test minimize entropy mode"""
        # Uniform distribution
        router_probs = torch.ones(32, 5) / 5.0
        loss = router_entropy_loss(router_probs, min_entropy=True)
        # Maximum entropy is positive in min_entropy mode
        assert (
            loss > 0
        ), "Uniform distribution should have positive entropy in min_entropy mode"

    def test_max_entropy_mode(self):
        """Test maximize entropy mode (default)"""
        # Uniform distribution
        router_probs = torch.ones(32, 5) / 5.0
        loss = router_entropy_loss(router_probs, min_entropy=False)
        # We minimize negative entropy, so loss is negative
        assert loss < 0, "Should return negative entropy in max_entropy mode"

    def test_reduction_mean(self):
        """Test mean reduction"""
        router_probs = torch.softmax(torch.randn(32, 5), dim=-1)
        loss = router_entropy_loss(router_probs, reduction="mean")
        assert loss.shape == torch.Size([]), "Mean reduction should return scalar"

    def test_reduction_sum(self):
        """Test sum reduction"""
        router_probs = torch.softmax(torch.randn(32, 5), dim=-1)
        loss = router_entropy_loss(router_probs, reduction="sum")
        assert loss.shape == torch.Size([]), "Sum reduction should return scalar"

    def test_reduction_none(self):
        """Test no reduction (per-sample)"""
        router_probs = torch.softmax(torch.randn(32, 5), dim=-1)
        loss = router_entropy_loss(router_probs, reduction="none")
        assert loss.shape == torch.Size(
            [32]
        ), "No reduction should return per-sample loss"

    def test_invalid_reduction(self):
        """Test invalid reduction raises error"""
        router_probs = torch.softmax(torch.randn(32, 5), dim=-1)
        with pytest.raises(ValueError):
            router_entropy_loss(router_probs, reduction="invalid")

    def test_gradient_flow(self):
        """Test that gradients flow through the loss"""
        logits = torch.randn(32, 5, requires_grad=True)
        router_probs = torch.softmax(logits, dim=-1)
        loss = router_entropy_loss(router_probs)
        loss.backward()
        assert logits.grad is not None, "Gradients should be computed"

    def test_probability_sum(self):
        """Test with probabilities that sum to 1"""
        router_probs = torch.softmax(torch.randn(32, 5), dim=-1)
        # Verify probabilities sum to 1
        assert torch.allclose(
            router_probs.sum(dim=-1), torch.ones(32)
        ), "Probs should sum to 1"
        loss = router_entropy_loss(router_probs)
        assert not torch.isnan(loss), "Loss should not be NaN for valid probabilities"
        assert not torch.isinf(loss), "Loss should not be Inf for valid probabilities"

    def test_numerical_stability(self):
        """Test numerical stability with very small probabilities"""
        # Create probabilities with very small values
        router_probs = torch.softmax(torch.randn(32, 5) * 10, dim=-1)
        loss = router_entropy_loss(router_probs)
        assert not torch.isnan(loss), "Loss should not be NaN"
        assert not torch.isinf(loss), "Loss should not be Inf"

    def test_entropy_bounds(self):
        """Test that entropy is within expected bounds"""
        K = 5  # Number of branches
        router_probs = torch.softmax(torch.randn(32, K), dim=-1)
        loss = router_entropy_loss(router_probs, min_entropy=True)
        # Entropy should be between 0 (peaked) and log(K) (uniform)
        max_entropy = math.log(K)
        assert torch.all(loss >= 0), "Entropy should be non-negative"
        assert torch.all(
            loss <= max_entropy + 0.1
        ), f"Entropy should not exceed log({K})"


class TestLossIntegration:
    """Integration tests combining multiple losses"""

    def test_combined_losses(self):
        """Test combining multiple losses in training scenario"""
        # Simulated batch
        batch_size = 32
        dim = 5

        # Generate synthetic data
        axes = torch.randn(dim, dim, requires_grad=True)
        vectors = torch.randn(batch_size, dim, requires_grad=True)
        router_logits = torch.randn(batch_size, dim, requires_grad=True)
        router_probs = torch.softmax(router_logits, dim=-1)

        # Compute all losses
        loss_ortho = orthogonality_loss(axes)
        loss_sparse = l1_sparsity_loss(vectors)
        loss_entropy = router_entropy_loss(router_probs)

        # Combine losses
        total_loss = 0.1 * loss_ortho + 0.01 * loss_sparse + 0.05 * loss_entropy

        # Verify total loss is differentiable
        total_loss.backward()
        assert axes.grad is not None, "Axes should have gradients"
        assert vectors.grad is not None, "Vectors should have gradients"
        assert router_logits.grad is not None, "Router logits should have gradients"

    def test_loss_weights(self):
        """Test different loss weights"""
        axes = torch.eye(5)
        vectors = torch.zeros(32, 5)
        router_probs = torch.ones(32, 5) / 5.0

        # All losses should be small or zero
        loss_ortho = orthogonality_loss(axes)
        loss_sparse = l1_sparsity_loss(vectors)
        loss_entropy = router_entropy_loss(router_probs, min_entropy=True)

        assert loss_ortho < 1e-5, "Orthogonal axes should have near-zero loss"
        assert loss_sparse < 1e-5, "Zero vectors should have near-zero loss"
        assert loss_entropy > 0, "Uniform distribution should have positive entropy"

    def test_all_losses_positive_contributions(self):
        """Test that all losses contribute positively to total loss"""
        # Create non-ideal conditions
        axes = torch.ones(5, 5)  # Non-orthogonal
        vectors = torch.randn(32, 5)  # Non-sparse
        router_probs = torch.softmax(torch.randn(32, 5), dim=-1)  # Random routing

        loss_ortho = orthogonality_loss(axes)
        loss_sparse = l1_sparsity_loss(vectors)
        loss_entropy = router_entropy_loss(router_probs, min_entropy=True)

        assert loss_ortho > 0, "Non-orthogonal axes should penalize"
        assert loss_sparse > 0, "Non-sparse vectors should penalize"
        assert loss_entropy >= 0, "Entropy should be non-negative"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
