# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Reconstruction quality benchmarks for Atlas Semantic Space.

Measures quality of encode-decode roundtrips:
- Vector stability (encoding consistency)
- Semantic preservation (decode quality)
- Hierarchical reconstruction fidelity
- Distance preservation
"""

import pytest
import numpy as np
from .conftest import skip_if_no_benchmark


@skip_if_no_benchmark
class TestEncodingConsistency:
    """Benchmark encoding consistency and stability."""

    def test_encoding_determinism(self, benchmark, encoder):
        """Benchmark that encoding is deterministic."""
        text = "Собака"
        
        def check_determinism():
            v1 = encoder.encode_text(text)
            v2 = encoder.encode_text(text)
            return np.allclose(v1, v2)
        
        result = benchmark(check_determinism)
        assert result == True

    def test_batch_vs_individual_consistency(self, benchmark, encoder):
        """Benchmark consistency between batch and individual encoding."""
        texts = ["Собака", "Любовь", "Машина"]
        
        def check_consistency():
            # Batch encoding
            batch_vectors = encoder.encode_text(texts)
            
            # Individual encoding
            individual_vectors = np.array([encoder.encode_text(t) for t in texts])
            
            # Should be very close
            return np.allclose(batch_vectors, individual_vectors, rtol=1e-5)
        
        result = benchmark(check_consistency)
        assert result == True

    def test_vector_normalization_stability(self, benchmark, encoder, sample_texts):
        """Benchmark that encoded vectors stay within expected range."""
        def check_normalization():
            vectors = encoder.encode_text(sample_texts)
            # All values should be in [-1, 1]
            return np.all(np.abs(vectors) <= 1.0)
        
        result = benchmark(check_normalization)
        assert result == True


@skip_if_no_benchmark
class TestSemanticPreservation:
    """Benchmark semantic meaning preservation through encoding."""

    def test_roundtrip_produces_output(self, benchmark, encoder, decoder):
        """Benchmark that roundtrip always produces valid output."""
        text = "Собака"
        
        def roundtrip():
            vector = encoder.encode_text(text)
            decoded = decoder.decode(vector)
            return len(decoded) > 0
        
        result = benchmark(roundtrip)
        assert result == True

    def test_similar_texts_similar_vectors(self, benchmark, encoder):
        """Benchmark that similar texts produce similar vectors."""
        # Similar concepts
        text1 = "dog"
        text2 = "puppy"
        
        def check_similarity():
            v1 = encoder.encode_text(text1)
            v2 = encoder.encode_text(text2)
            # Cosine similarity
            cos_sim = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
            return cos_sim
        
        similarity = benchmark(check_similarity)
        # Similar words should have positive similarity
        assert similarity > 0.0

    def test_different_texts_different_vectors(self, benchmark, encoder):
        """Benchmark that different texts produce distinguishable vectors."""
        text1 = "love"
        text2 = "machine"
        
        def check_difference():
            v1 = encoder.encode_text(text1)
            v2 = encoder.encode_text(text2)
            # Euclidean distance
            distance = np.linalg.norm(v1 - v2)
            return distance
        
        distance = benchmark(check_difference)
        # Different concepts should have measurable distance
        assert distance > 0.1

    def test_zero_vector_handling(self, benchmark, decoder):
        """Benchmark decoding of zero/neutral vector."""
        vector = np.zeros(5)
        
        result = benchmark(decoder.decode, vector)
        assert isinstance(result, str)
        assert len(result) > 0


@skip_if_no_benchmark
class TestHierarchicalReconstruction:
    """Benchmark hierarchical encoding/decoding reconstruction quality."""

    def test_tree_structure_validity(self, benchmark, hierarchical_encoder):
        """Benchmark that encoded trees have valid structure."""
        text = "Machine learning"
        
        def check_tree():
            tree = hierarchical_encoder.encode_hierarchical(text, max_depth=1)
            # Check root exists
            if tree is None:
                return False
            # Check values are valid
            if len(tree.value) != 5:
                return False
            # Check no NaN/Inf
            if np.any(np.isnan(tree.value)) or np.any(np.isinf(tree.value)):
                return False
            # Check children count if they exist
            if tree.children is not None and len(tree.children) not in [0, 5]:
                return False
            return True
        
        result = benchmark(check_tree)
        assert result == True

    def test_flatten_preserves_dimensions(self, benchmark, hierarchical_encoder):
        """Benchmark that tree flattening preserves 5D structure."""
        text = "Собака"
        
        def check_flatten():
            tree = hierarchical_encoder.encode_hierarchical(text, max_depth=0)
            flat = hierarchical_encoder.flatten_tree(tree)
            return flat.shape == (5,) and np.all(np.abs(flat) <= 1.0)
        
        result = benchmark(check_flatten)
        assert result == True

    def test_path_manipulation_preserves_structure(
        self, benchmark, hierarchical_encoder, hierarchical_decoder
    ):
        """Benchmark that path manipulation preserves tree structure."""
        text = "Собака"
        
        def check_manipulation():
            tree = hierarchical_encoder.encode_hierarchical(text, max_depth=1)
            new_value = [0.5, 0.5, 0.5, 0.5, 0.5]
            modified = hierarchical_decoder.manipulate_path(tree, "root", new_value)
            
            # Check structure preserved
            if modified is None or len(modified.value) != 5:
                return False
            # Check modification applied
            if not np.allclose(modified.value, new_value, rtol=1e-5):
                return False
            # Original should be unchanged
            if np.allclose(tree.value, new_value, rtol=1e-5):
                return False
            return True
        
        result = benchmark(check_manipulation)
        assert result == True

    def test_hierarchical_roundtrip_quality(
        self, benchmark, hierarchical_encoder, hierarchical_decoder
    ):
        """Benchmark hierarchical encode-decode quality."""
        text = "Natural language processing"
        
        def roundtrip():
            tree = hierarchical_encoder.encode_hierarchical(text, max_depth=1)
            result = hierarchical_decoder.decode_hierarchical(
                tree, top_k=3, with_reasoning=True
            )
            # Check output quality
            if 'text' not in result or len(result['text']) == 0:
                return False
            if 'reasoning' not in result or len(result['reasoning']) == 0:
                return False
            return True
        
        result = benchmark(roundtrip)
        assert result == True


@skip_if_no_benchmark
class TestDistancePreservation:
    """Benchmark that semantic distances are preserved in vector space."""

    def test_distance_metric_consistency(self, benchmark, encoder):
        """Benchmark consistency of distance metrics."""
        texts = ["love", "hate", "joy", "sadness"]
        
        def check_distances():
            vectors = encoder.encode_text(texts)
            
            # Calculate all pairwise distances
            distances = []
            for i in range(len(vectors)):
                for j in range(i + 1, len(vectors)):
                    dist = np.linalg.norm(vectors[i] - vectors[j])
                    distances.append(dist)
            
            # All distances should be positive and finite
            return all(d > 0 and np.isfinite(d) for d in distances)
        
        result = benchmark(check_distances)
        assert result == True

    def test_triangle_inequality(self, benchmark, encoder):
        """Benchmark that triangle inequality holds in semantic space."""
        texts = ["dog", "cat", "animal"]
        
        def check_triangle():
            vectors = encoder.encode_text(texts)
            v1, v2, v3 = vectors
            
            # Triangle inequality: d(v1,v3) <= d(v1,v2) + d(v2,v3)
            d13 = np.linalg.norm(v1 - v3)
            d12 = np.linalg.norm(v1 - v2)
            d23 = np.linalg.norm(v2 - v3)
            
            return d13 <= d12 + d23 + 1e-6  # small epsilon for numerical stability
        
        result = benchmark(check_triangle)
        assert result == True

    def test_symmetry(self, benchmark, encoder):
        """Benchmark that distance is symmetric."""
        text1 = "machine"
        text2 = "learning"
        
        def check_symmetry():
            v1 = encoder.encode_text(text1)
            v2 = encoder.encode_text(text2)
            
            d12 = np.linalg.norm(v1 - v2)
            d21 = np.linalg.norm(v2 - v1)
            
            return np.isclose(d12, d21, rtol=1e-5)
        
        result = benchmark(check_symmetry)
        assert result == True
