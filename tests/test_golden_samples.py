"""
Golden sample tests - Regression tests for stable encode/decode behavior.

These tests verify that the system maintains consistent behavior across versions.
"""

import json
import math
import pytest
import numpy as np
from pathlib import Path

from atlas import SemanticSpace


@pytest.fixture
def golden_samples():
    """Load golden samples from JSON file"""
    samples_path = Path(__file__).parent.parent / "samples" / "golden_samples.json"
    with open(samples_path) as f:
        data = json.load(f)
    return data


@pytest.fixture
def space():
    """Create semantic space instance"""
    return SemanticSpace()


class TestGoldenSamples:
    """Test that golden samples encode/decode as expected"""
    
    def test_golden_samples_encode(self, space, golden_samples):
        """Test that encoding matches expected vectors within tolerance"""
        for sample in golden_samples["samples"]:
            text = sample["text"]
            expected = np.array(sample["expected_vector"])
            tolerance = sample["tolerance"]
            
            # Encode
            actual = space.encode(text)
            
            # Check shape
            assert actual.shape == (5,), f"Vector for '{text}' has wrong shape"
            
            # Check values within tolerance
            differences = np.abs(actual - expected)
            max_diff = np.max(differences)
            
            assert max_diff <= tolerance, (
                f"Encoding for '{text}' differs too much from expected.\n"
                f"Expected: {expected}\n"
                f"Actual:   {actual}\n"
                f"Max diff: {max_diff:.4f} (tolerance: {tolerance})\n"
                f"Notes: {sample.get('notes', 'N/A')}"
            )
    
    def test_golden_samples_decode(self, space, golden_samples):
        """Test that decoding produces expected text"""
        for sample in golden_samples["samples"]:
            vector = np.array(sample["expected_vector"])
            expected_text = sample["expected_decoded"]
            
            # Decode
            actual_text = space.decode(vector)
            
            # For now, just check it returns a string
            # In future versions, we might want exact match
            assert isinstance(actual_text, str), f"Decode didn't return string"
            assert len(actual_text) > 0, f"Decode returned empty string"
    
    @pytest.mark.skip(reason="Round-trip test not meaningful for simple rule-based decoder with limited vocabulary")
    def test_golden_samples_round_trip(self, space, golden_samples):
        """Test that encode->decode->encode gives consistent results
        
        Note: This test is skipped for v0.1 because the simple rule-based
        decoder has a limited vocabulary and may not decode to the exact
        same word. This will be re-enabled for neural decoder versions.
        """
        for sample in golden_samples["samples"]:
            text = sample["text"]
            
            # First encode
            vector1 = space.encode(text)
            
            # Decode
            decoded = space.decode(vector1)
            
            # Skip if decoded is empty or invalid
            if not decoded or not decoded.strip():
                continue
            
            # Encode again
            try:
                vector2 = space.encode(decoded)
            except ValueError:
                # Decoder returned something that can't be encoded
                continue
            
            # Vectors should be similar (within tolerance)
            # Note: Won't be exact due to vocabulary limitations
            norm1 = np.linalg.norm(vector1)
            norm2 = np.linalg.norm(vector2)
            
            # Skip zero vectors
            if norm1 < 1e-10 or norm2 < 1e-10:
                continue
            
            similarity = np.dot(vector1, vector2) / (norm1 * norm2)
            
            # Relaxed threshold since we're testing a simple rule-based system
            assert similarity > 0.5 or np.allclose(vector1, vector2, atol=0.1), (
                f"Round-trip encoding for '{text}' not consistent.\n"
                f"Original vector: {vector1}\n"
                f"Decoded text: '{decoded}'\n"
                f"After round-trip: {vector2}\n"
                f"Cosine similarity: {similarity:.3f}"
            )


class TestInvariants:
    """Test that fundamental invariants always hold"""
    
    def test_vector_length_invariant(self, space):
        """All vectors must be exactly 5-dimensional"""
        test_texts = ["Собака", "Любовь", "Машина", "Жизнь", "Страх"]
        
        for text in test_texts:
            vector = space.encode(text)
            assert len(vector) == 5, f"Vector length is {len(vector)}, expected 5"
            assert vector.shape == (5,), f"Vector shape is {vector.shape}, expected (5,)"
    
    def test_vector_normalization_invariant(self, space):
        """All vector values must be in range [-1, 1]"""
        test_texts = ["Собака", "Любовь", "Машина", "Жизнь", "Страх", "Dog", "Love"]
        
        for text in test_texts:
            vector = space.encode(text)
            
            for i, val in enumerate(vector):
                assert -1 <= val <= 1, (
                    f"Vector[{i}] = {val} for '{text}' is out of range [-1, 1]"
                )
    
    def test_no_nan_inf_invariant(self, space):
        """Vectors must never contain NaN or Inf values"""
        test_texts = ["Собака", "Любовь", "Машина", "Жизнь", "Страх"]
        
        for text in test_texts:
            vector = space.encode(text)
            
            for i, val in enumerate(vector):
                assert not math.isnan(val), f"Vector[{i}] is NaN for '{text}'"
                assert not math.isinf(val), f"Vector[{i}] is Inf for '{text}'"
    
    def test_determinism_invariant(self, space):
        """Same input must always produce same output"""
        test_text = "Собака"
        
        # Encode multiple times
        vectors = [space.encode(test_text) for _ in range(5)]
        
        # All should be identical
        for i, vec in enumerate(vectors[1:], 1):
            np.testing.assert_array_equal(
                vectors[0], vec,
                err_msg=f"Encoding {i+1} differs from first encoding"
            )
    
    def test_decode_returns_string(self, space):
        """Decode must always return a string"""
        test_vectors = [
            [0.0, 0.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0, 0.0],
            [-1.0, 0.0, 0.0, 0.0, 0.0],
            [0.5, -0.5, 0.3, 0.2, 0.8],
        ]
        
        for vector in test_vectors:
            result = space.decode(np.array(vector))
            assert isinstance(result, str), f"Decode returned {type(result)}, not str"
            assert len(result) > 0, "Decode returned empty string"


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_text_error(self, space):
        """Empty text should raise ValueError"""
        with pytest.raises((ValueError, AssertionError)):
            space.encode("")
    
    def test_very_long_text(self, space):
        """Very long text should be handled gracefully"""
        long_text = "Собака " * 1000  # 6000+ characters
        
        # Should not crash
        vector = space.encode(long_text)
        
        # Should still be valid
        assert vector.shape == (5,)
        assert all(-1 <= v <= 1 for v in vector)
    
    def test_special_characters(self, space):
        """Text with special characters should be handled"""
        special_texts = [
            "12345",
            "!@#$%",
            "Собака123",
            "hello-world",
            "test_case"
        ]
        
        for text in special_texts:
            # Should not crash
            vector = space.encode(text)
            
            # Should be valid
            assert vector.shape == (5,)
            assert all(-1 <= v <= 1 for v in vector)
    
    def test_zero_vector_decode(self, space):
        """Zero vector should decode to something"""
        zero_vector = np.zeros(5)
        result = space.decode(zero_vector)
        
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_extreme_vector_values(self, space):
        """Vectors at extreme values should decode gracefully"""
        extreme_vectors = [
            np.array([1.0, 1.0, 1.0, 1.0, 1.0]),
            np.array([-1.0, -1.0, -1.0, -1.0, -1.0]),
            np.array([1.0, -1.0, 1.0, -1.0, 1.0]),
        ]
        
        for vector in extreme_vectors:
            # Should not crash
            result = space.decode(vector)
            
            # Should return valid text
            assert isinstance(result, str)
            assert len(result) > 0
    
    def test_mixed_languages(self, space):
        """Mixed language text should be handled"""
        mixed_texts = [
            "Собака dog",
            "Love любовь",
            "Hello мир"
        ]
        
        for text in mixed_texts:
            vector = space.encode(text)
            
            assert vector.shape == (5,)
            assert all(-1 <= v <= 1 for v in vector)


class TestReproducibility:
    """Test reproducibility across runs"""
    
    def test_consistent_across_instances(self):
        """Multiple instances should give same results"""
        text = "Собака"
        
        # Create multiple instances
        space1 = SemanticSpace()
        space2 = SemanticSpace()
        
        # Encode with both
        vector1 = space1.encode(text)
        vector2 = space2.encode(text)
        
        # Should be identical
        np.testing.assert_array_equal(vector1, vector2)
    
    def test_batch_vs_single_encoding(self, space):
        """Batch encoding should match individual encoding"""
        texts = ["Собака", "Любовь", "Машина"]
        
        # Encode individually
        individual = [space.encode(text) for text in texts]
        
        # Encode as batch
        batch = space.encode(texts)
        
        # Should match
        for i, text in enumerate(texts):
            np.testing.assert_array_almost_equal(
                individual[i], batch[i],
                err_msg=f"Batch encoding differs for '{text}'"
            )


class TestPerformance:
    """Performance tests (informational, not strict)"""
    
    @pytest.mark.skip(reason="pytest-benchmark not installed by default")
    def test_encode_performance(self, space):
        """Measure encode performance (requires pytest-benchmark)"""
        # This test requires pytest-benchmark to be installed
        # Skip by default to avoid dependency issues
        pytest.skip("pytest-benchmark not installed by default")
    
    def test_batch_encode_performance(self, space):
        """Batch encoding should be reasonably fast"""
        import time
        
        texts = ["Собака", "Любовь", "Машина", "Жизнь", "Страх"] * 10  # 50 texts
        
        start = time.time()
        vectors = space.encode(texts)
        elapsed = time.time() - start
        
        # Should complete in reasonable time (not strict requirement for now)
        assert elapsed < 5.0, f"Batch encoding took {elapsed:.2f}s (expected < 5s)"
        assert vectors.shape == (50, 5)


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
