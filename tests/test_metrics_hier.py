# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Unit tests for hierarchical metrics with synthetic vectors.
Tests H-Coherence, H-Stability, and H-Diversity metrics.
"""

import pytest
import numpy as np
from atlas.metrics import (
    h_coherence,
    h_stability,
    h_diversity,
    interpretability_metrics_summary,
    CoherenceResult,
    StabilityResult,
    DiversityResult,
)


class TestHCoherence:
    """Test H-Coherence metric"""

    def test_coherence_perfect_similar_vectors(self):
        """Test coherence with perfectly similar vectors"""
        # All vectors point in the same direction
        vectors = np.array(
            [
                [1.0, 0.0],
                [1.0, 0.0],
                [1.0, 0.0],
            ]
        )
        result = h_coherence(vectors)

        assert isinstance(result, CoherenceResult)
        assert result.score == 1.0
        assert result.status == "implemented"
        assert result.method == "cosine"

    def test_coherence_highly_coherent_vectors(self):
        """Test coherence with highly coherent vectors"""
        # Vectors in similar direction with small variations
        vectors = np.array(
            [
                [0.9, 0.1],
                [0.8, 0.2],
                [0.85, 0.15],
            ]
        )
        result = h_coherence(vectors)

        assert result.score > 0.85
        assert result.status == "implemented"

    def test_coherence_orthogonal_vectors(self):
        """Test coherence with orthogonal vectors (low coherence)"""
        # Perpendicular vectors
        vectors = np.array(
            [
                [1.0, 0.0],
                [0.0, 1.0],
            ]
        )
        result = h_coherence(vectors)

        # Orthogonal vectors should have score around 0.5 (90 degrees)
        assert 0.4 < result.score < 0.6

    def test_coherence_opposite_vectors(self):
        """Test coherence with opposite vectors (minimum coherence)"""
        # Opposite directions
        vectors = np.array(
            [
                [1.0, 0.0],
                [-1.0, 0.0],
            ]
        )
        result = h_coherence(vectors)

        # Opposite vectors should have low coherence
        assert result.score < 0.2

    def test_coherence_random_vectors(self):
        """Test coherence with random vectors"""
        np.random.seed(42)
        vectors = np.random.randn(10, 5)
        result = h_coherence(vectors)

        # Random vectors should have moderate coherence
        assert 0.0 <= result.score <= 1.0
        assert "n_samples" in result.details

    def test_coherence_dict_input(self):
        """Test coherence with dictionary input (multiple dimensions)"""
        vectors_dict = {
            "dim0": np.array([[0.9, 0.1], [0.8, 0.2], [0.85, 0.15]]),
            "dim1": np.array([[0.1, 0.9], [0.2, 0.8], [0.15, 0.85]]),
        }
        result = h_coherence(vectors_dict)

        assert result.score > 0.8
        assert "dimension_scores" in result.details
        assert "dim0" in result.details["dimension_scores"]
        assert "dim1" in result.details["dimension_scores"]

    def test_coherence_insufficient_samples(self):
        """Test coherence with insufficient samples"""
        vectors = np.array([[1.0, 0.0]])  # Only 1 vector
        result = h_coherence(vectors, min_samples=2)

        assert result.score == 0.0
        assert "error" in result.details

    def test_coherence_empty_dict(self):
        """Test coherence with empty dictionary"""
        result = h_coherence({})

        assert result.score == 0.0
        assert "error" in result.details

    def test_coherence_list_input(self):
        """Test coherence with list input (converted to array)"""
        vectors_list = [[1.0, 0.0], [0.9, 0.1], [0.8, 0.2]]
        result = h_coherence(vectors_list)

        assert result.score > 0.85
        assert result.status == "implemented"


class TestHStability:
    """Test H-Stability metric"""

    def test_stability_perfect_agreement(self):
        """Test stability with perfect agreement"""
        labels1 = [0, 1, 0, 2, 1, 2]
        labels2 = [0, 1, 0, 2, 1, 2]
        result = h_stability(labels1, labels2, method="ari")

        assert isinstance(result, StabilityResult)
        assert result.score == 1.0
        assert result.status == "implemented"

    def test_stability_nmi_perfect_agreement(self):
        """Test stability with NMI and perfect agreement"""
        labels1 = [0, 1, 0, 2, 1, 2]
        labels2 = [0, 1, 0, 2, 1, 2]
        result = h_stability(labels1, labels2, method="nmi")

        assert result.score == 1.0
        assert result.method == "nmi"

    def test_stability_complete_disagreement(self):
        """Test stability with complete disagreement"""
        labels1 = [0, 0, 0, 0, 0]
        labels2 = [0, 1, 2, 3, 4]
        result = h_stability(labels1, labels2, method="ari")

        # Should have low stability (near 0.5 after normalization)
        assert result.score < 0.6

    def test_stability_partial_agreement(self):
        """Test stability with partial agreement"""
        labels1 = [0, 0, 1, 1, 2, 2]
        labels2 = [0, 0, 1, 2, 2, 2]  # One sample differs
        result = h_stability(labels1, labels2, method="ari")

        # Should have high but not perfect stability
        assert 0.6 < result.score < 1.0

    def test_stability_numpy_arrays(self):
        """Test stability with numpy array input"""
        labels1 = np.array([0, 1, 0, 2, 1, 2])
        labels2 = np.array([0, 1, 0, 2, 1, 2])
        result = h_stability(labels1, labels2)

        assert result.score == 1.0

    def test_stability_dict_input(self):
        """Test stability with dictionary input"""
        run1 = {"texts": ["a", "b", "c"], "assignments": [0, 1, 0]}
        run2 = {"texts": ["a", "b", "c"], "assignments": [0, 1, 0]}
        result = h_stability(run1, run2)

        assert result.score == 1.0
        assert result.details["n_samples"] == 3

    def test_stability_empty_labels(self):
        """Test stability with empty labels"""
        result = h_stability([], [])

        assert result.score == 0.0
        assert "error" in result.details

    def test_stability_length_mismatch(self):
        """Test stability with mismatched lengths"""
        labels1 = [0, 1, 0]
        labels2 = [0, 1, 0, 2]
        result = h_stability(labels1, labels2)

        assert result.score == 0.0
        assert "Length mismatch" in result.details["error"]

    def test_stability_different_cluster_counts(self):
        """Test stability with different numbers of clusters"""
        labels1 = [0, 0, 1, 1, 2, 2]  # 3 clusters
        labels2 = [0, 0, 0, 1, 1, 1]  # 2 clusters
        result = h_stability(labels1, labels2)

        # Should still compute a stability score
        assert 0.0 <= result.score <= 1.0
        assert result.details["n_clusters_run1"] == 3
        assert result.details["n_clusters_run2"] == 2

    def test_stability_invalid_method(self):
        """Test stability with invalid method"""
        labels1 = [0, 1, 0]
        labels2 = [0, 1, 0]
        result = h_stability(labels1, labels2, method="invalid")

        assert result.score == 0.0
        assert "error" in result.details


class TestHDiversity:
    """Test H-Diversity metric"""

    def test_diversity_orthogonal_vectors(self):
        """Test diversity with orthogonal vectors (high diversity)"""
        # Perpendicular vectors - maximum diversity
        vectors = np.array(
            [
                [1.0, 0.0],
                [0.0, 1.0],
            ]
        )
        result = h_diversity(vectors)

        assert isinstance(result, DiversityResult)
        assert result.score > 0.45  # Close to 0.5 for orthogonal
        assert result.status == "implemented"

    def test_diversity_parallel_vectors(self):
        """Test diversity with parallel vectors (low diversity)"""
        # Parallel vectors - minimum diversity
        vectors = np.array(
            [
                [1.0, 0.0],
                [0.9, 0.0],
            ]
        )
        result = h_diversity(vectors)

        assert result.score < 0.1

    def test_diversity_opposite_vectors(self):
        """Test diversity with opposite vectors (maximum diversity)"""
        # Opposite vectors
        vectors = np.array(
            [
                [1.0, 0.0],
                [-1.0, 0.0],
            ]
        )
        result = h_diversity(vectors)

        # Opposite vectors should have maximum diversity
        assert result.score > 0.9

    def test_diversity_multiple_dimensions(self):
        """Test diversity with multiple well-separated clusters"""
        # 3 clusters in 3D space
        vectors = np.array(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ]
        )
        result = h_diversity(vectors)

        # Orthogonal clusters should have high diversity
        assert result.score > 0.45
        assert result.details["n_groups"] == 3

    def test_diversity_dict_input(self):
        """Test diversity with dictionary input"""
        vectors_dict = {
            "cluster_a": np.array([1.0, 0.0]),
            "cluster_b": np.array([0.0, 1.0]),
        }
        result = h_diversity(vectors_dict)

        assert result.score > 0.45
        assert "dimension_names" in result.details
        assert "cluster_a" in result.details["dimension_names"]

    def test_diversity_dict_with_2d_arrays(self):
        """Test diversity with dict containing 2D arrays (multiple samples per group)"""
        vectors_dict = {
            "cluster_a": np.array([[1.0, 0.0], [0.9, 0.1]]),  # Mean: [0.95, 0.05]
            "cluster_b": np.array([[0.0, 1.0], [0.1, 0.9]]),  # Mean: [0.05, 0.95]
        }
        result = h_diversity(vectors_dict)

        assert result.score > 0.4  # Should be diverse

    def test_diversity_single_group(self):
        """Test diversity with single group (insufficient)"""
        vectors = np.array([[1.0, 0.0]])
        result = h_diversity(vectors)

        assert result.score == 0.0
        assert "error" in result.details

    def test_diversity_empty_dict(self):
        """Test diversity with empty dictionary"""
        result = h_diversity({})

        assert result.score == 0.0
        assert "error" in result.details

    def test_diversity_list_input(self):
        """Test diversity with list input"""
        vectors_list = [[1.0, 0.0], [0.0, 1.0]]
        result = h_diversity(vectors_list)

        assert result.score > 0.4


class TestInterpretabilityMetricsSummary:
    """Test interpretability metrics summary"""

    def test_summary_all_metrics(self):
        """Test summary with all three metrics"""
        coherence = CoherenceResult(score=0.85, method="cosine", status="implemented")
        stability = StabilityResult(score=0.80, method="ari", status="implemented")
        diversity = DiversityResult(score=0.75, method="cosine_distance", status="implemented")

        summary = interpretability_metrics_summary(coherence, stability, diversity)

        assert summary["coherence"] == 0.85
        assert summary["stability"] == 0.80
        assert summary["diversity"] == 0.75
        assert summary["overall_interpretability"] == 0.8  # (0.85 + 0.80 + 0.75) / 3
        assert summary["status"] == "implemented"

    def test_summary_partial_metrics(self):
        """Test summary with only some metrics"""
        coherence = CoherenceResult(score=0.90, method="cosine", status="implemented")
        stability = StabilityResult(score=0.80, method="ari", status="implemented")

        summary = interpretability_metrics_summary(coherence, stability)

        assert summary["coherence"] == 0.90
        assert summary["stability"] == 0.80
        assert summary["diversity"] is None
        assert summary["overall_interpretability"] == 0.85  # (0.90 + 0.80) / 2

    def test_summary_no_metrics(self):
        """Test summary with no metrics"""
        summary = interpretability_metrics_summary()

        assert summary["coherence"] is None
        assert summary["stability"] is None
        assert summary["diversity"] is None
        assert "overall_interpretability" not in summary


class TestIntegrationScenarios:
    """Integration tests with realistic scenarios"""

    def test_scenario_good_interpretability(self):
        """Test scenario: Well-structured hierarchical space with good interpretability"""
        # Create coherent dimensions
        dim1_vectors = np.array([[0.9, 0.1], [0.85, 0.15], [0.8, 0.2]])
        dim2_vectors = np.array([[0.1, 0.9], [0.15, 0.85], [0.2, 0.8]])

        coherence = h_coherence({"dim1": dim1_vectors, "dim2": dim2_vectors})

        # Create stable clusters
        labels1 = [0, 0, 1, 1, 2, 2]
        labels2 = [0, 0, 1, 1, 2, 2]
        stability = h_stability(labels1, labels2)

        # Create diverse representatives
        representatives = np.array(
            [
                [1.0, 0.0],
                [0.0, 1.0],
            ]
        )
        diversity = h_diversity(representatives)

        # All metrics should be high
        assert coherence.score > 0.8
        assert stability.score > 0.9
        assert diversity.score > 0.4

        summary = interpretability_metrics_summary(coherence, stability, diversity)
        assert summary["overall_interpretability"] > 0.7

    def test_scenario_poor_interpretability(self):
        """Test scenario: Poorly structured space with low interpretability"""
        # Create incoherent dimensions (random)
        np.random.seed(42)
        dim1_vectors = np.random.randn(5, 10)

        coherence = h_coherence(dim1_vectors)

        # Create unstable clusters
        labels1 = [0, 0, 1, 1, 2, 2]
        labels2 = [1, 2, 0, 2, 1, 0]  # Completely different
        stability = h_stability(labels1, labels2)

        # Create similar representatives (low diversity)
        representatives = np.array(
            [
                [1.0, 0.0],
                [0.95, 0.05],
            ]
        )
        diversity = h_diversity(representatives)

        # Coherence should be moderate (random has some structure)
        # Stability should be low
        assert stability.score < 0.7
        # Diversity should be low
        assert diversity.score < 0.2

    def test_scenario_multidimensional_hierarchy(self):
        """Test scenario: Multi-level hierarchy with 5 dimensions"""
        # Create 5 coherent dimensions
        vectors_dict = {}
        for i in range(5):
            base = np.zeros(5)
            base[i] = 1.0
            vectors = []
            for _ in range(3):
                noise = np.random.randn(5) * 0.1
                vectors.append(base + noise)
            vectors_dict[f"dim{i}"] = np.array(vectors)

        coherence = h_coherence(vectors_dict)

        # Create representatives for diversity
        representatives = np.eye(5)  # 5 orthogonal vectors
        diversity = h_diversity(representatives)

        # Should have high coherence and diversity
        assert coherence.score > 0.7
        assert diversity.score > 0.4
        assert coherence.details["n_dimensions"] == 5


class TestBackwardCompatibility:
    """Test backward compatibility with stub functions"""

    def test_h_coherence_stub_compatibility(self):
        """Test that h_coherence_stub still works"""
        from atlas.metrics import h_coherence_stub

        terms = {"dim0": ["dog", "cat", "mouse"], "dim1": ["love", "joy", "happy"]}
        result = h_coherence_stub(terms)

        assert isinstance(result, CoherenceResult)
        assert 0.0 <= result.score <= 1.0
        assert "compatibility" in result.method

    def test_h_stability_stub_compatibility(self):
        """Test that h_stability_stub still works"""
        from atlas.metrics import h_stability_stub

        run1 = {"texts": ["a", "b", "c"], "assignments": [0, 1, 0]}
        run2 = {"texts": ["a", "b", "c"], "assignments": [0, 1, 0]}
        result = h_stability_stub(run1, run2)

        assert isinstance(result, StabilityResult)
        assert result.score == 1.0
        assert "compatibility" in result.method


# Optional: pytest-benchmark integration
# To run benchmarks: pip install pytest-benchmark && pytest tests/test_metrics_hier.py --benchmark-only
try:
    import pytest_benchmark

    HAS_BENCHMARK = True
except ImportError:
    HAS_BENCHMARK = False


if HAS_BENCHMARK:

    class TestPerformanceBenchmarks:
        """Performance benchmarks for metrics (optional, requires pytest-benchmark)"""

        def test_benchmark_h_coherence_small(self, benchmark):
            """Benchmark H-Coherence with small vectors"""
            vectors = np.random.randn(10, 5)
            result = benchmark(h_coherence, vectors)
            assert result.score >= 0.0

        def test_benchmark_h_coherence_medium(self, benchmark):
            """Benchmark H-Coherence with medium vectors"""
            vectors = np.random.randn(100, 50)
            result = benchmark(h_coherence, vectors)
            assert result.score >= 0.0

        def test_benchmark_h_stability_small(self, benchmark):
            """Benchmark H-Stability with small labels"""
            labels1 = np.random.randint(0, 5, 100)
            labels2 = np.random.randint(0, 5, 100)
            result = benchmark(h_stability, labels1, labels2)
            assert result.score >= 0.0

        def test_benchmark_h_diversity_small(self, benchmark):
            """Benchmark H-Diversity with small representatives"""
            representatives = np.random.randn(5, 10)
            result = benchmark(h_diversity, representatives)
            assert result.score >= 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
