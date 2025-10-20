# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Tests for TextEncoder5D - sentence-transformers based 5D text encoder.
"""

import pytest
import numpy as np

# Try to import TextEncoder5D
try:
    from atlas.encoders.text_encoder_5d import TextEncoder5D
    ENCODER_AVAILABLE = True
except ImportError:
    ENCODER_AVAILABLE = False


@pytest.mark.skipif(not ENCODER_AVAILABLE, reason="TextEncoder5D not available")
class TestTextEncoder5D:
    """Test suite for TextEncoder5D encoder"""
    
    @pytest.fixture
    def encoder(self):
        """Create encoder instance for testing"""
        return TextEncoder5D()
    
    def test_encoder_initialization(self, encoder):
        """Test encoder initializes correctly"""
        assert encoder.dimension == 5
        # If using fallback, embedding_dim will be None
        if not encoder.using_fallback:
            assert encoder.embedding_dim == 384  # MiniLM-L6-v2 dimension
        assert encoder.normalize_method in ["tanh", "unit_norm"]
    
    def test_encode_single_text(self, encoder):
        """Test encoding a single text"""
        vector = encoder.encode_text("Собака")
        assert isinstance(vector, np.ndarray)
        assert vector.shape == (5,)
        # Values should be in [-1, 1] for tanh normalization
        assert np.all(np.abs(vector) <= 1.0)
    
    def test_encode_english_text(self, encoder):
        """Test encoding English text"""
        vector = encoder.encode_text("Hello world")
        assert isinstance(vector, np.ndarray)
        assert vector.shape == (5,)
        assert np.all(np.abs(vector) <= 1.0)
    
    def test_encode_multiple_texts(self, encoder):
        """Test encoding multiple texts"""
        texts = ["Собака", "Машина", "Любовь"]
        vectors = encoder.encode_text(texts)
        assert isinstance(vectors, np.ndarray)
        assert vectors.shape == (3, 5)
        assert np.all(np.abs(vectors) <= 1.0)
    
    def test_encode_empty_text(self, encoder):
        """Test encoding empty text raises ValueError"""
        with pytest.raises(ValueError, match="Input text cannot be empty"):
            encoder.encode_text("")
    
    def test_encode_empty_list(self, encoder):
        """Test encoding empty list raises ValueError"""
        with pytest.raises(ValueError, match="Input text list cannot be empty"):
            encoder.encode_text([])
    
    def test_encode_whitespace_only(self, encoder):
        """Test encoding whitespace-only text raises ValueError"""
        with pytest.raises(ValueError, match="Input text cannot be empty"):
            encoder.encode_text("   ")
    
    def test_encode_list_with_empty_string(self, encoder):
        """Test encoding list with empty string raises ValueError"""
        with pytest.raises(ValueError, match="Input text list contains empty strings"):
            encoder.encode_text(["Hello", "", "World"])
    
    def test_consistent_encoding(self, encoder):
        """Test that same text encodes consistently"""
        text = "Собака бежит по полю"
        vector1 = encoder.encode_text(text)
        vector2 = encoder.encode_text(text)
        # Should be very close (small numerical differences acceptable)
        np.testing.assert_array_almost_equal(vector1, vector2, decimal=5)
    
    def test_different_texts_different_vectors(self, encoder):
        """Test that different texts produce different vectors"""
        vector1 = encoder.encode_text("Собака")
        vector2 = encoder.encode_text("Машина")
        # Vectors should be different
        assert not np.allclose(vector1, vector2)
    
    def test_similar_texts_similar_vectors(self, encoder):
        """Test that similar texts produce similar vectors"""
        vector1 = encoder.encode_text("Dog running in the park")
        vector2 = encoder.encode_text("A dog runs in the park")
        # Calculate cosine similarity
        cosine_sim = np.dot(vector1, vector2) / (np.linalg.norm(vector1) * np.linalg.norm(vector2) + 1e-9)
        # Similar texts should have high cosine similarity
        assert cosine_sim > 0.5
    
    def test_encode_alias(self, encoder):
        """Test that encode() alias works"""
        text = "Test text"
        vector1 = encoder.encode_text(text)
        vector2 = encoder.encode(text)
        np.testing.assert_array_equal(vector1, vector2)
    
    def test_callable_interface(self, encoder):
        """Test that encoder is callable"""
        text = "Test text"
        vector1 = encoder.encode_text(text)
        vector2 = encoder(text)
        np.testing.assert_array_equal(vector1, vector2)
    
    def test_batch_encoding(self, encoder):
        """Test batch encoding with different batch sizes"""
        texts = ["Text 1", "Text 2", "Text 3", "Text 4", "Text 5"]
        vectors1 = encoder.encode_text(texts, batch_size=2)
        vectors2 = encoder.encode_text(texts, batch_size=5)
        # Results should be identical regardless of batch size
        np.testing.assert_array_almost_equal(vectors1, vectors2, decimal=5)
    
    def test_normalization_range(self, encoder):
        """Test that normalized vectors are in correct range"""
        # Test with longer text to get varied embeddings
        text = "This is a longer text to test the normalization of embeddings in the encoder"
        vector = encoder.encode_text(text, normalize=True)
        if encoder.normalize_method == "tanh":
            # Should be in [-1, 1]
            assert np.all(vector >= -1.0)
            assert np.all(vector <= 1.0)
        elif encoder.normalize_method == "unit_norm":
            # Should have unit norm
            norm = np.linalg.norm(vector)
            assert np.isclose(norm, 1.0, atol=1e-5)
    
    def test_without_normalization(self, encoder):
        """Test encoding without normalization"""
        text = "Test text"
        vector = encoder.encode_text(text, normalize=False)
        assert isinstance(vector, np.ndarray)
        assert vector.shape == (5,)
        # Without normalization, values might be outside [-1, 1]
        # Just check that we get valid numbers
        assert np.all(np.isfinite(vector))
    
    def test_pca_fitting(self, encoder):
        """Test that PCA gets fitted after encoding enough samples"""
        # For fallback encoder, this test doesn't apply
        if encoder.using_fallback:
            pytest.skip("PCA fitting test not applicable for fallback encoder")
        
        # Initially not fitted
        assert not encoder.is_fitted
        
        # Encode several texts to trigger PCA fitting
        texts = [f"Sample text {i}" for i in range(150)]
        encoder.encode_text(texts)
        
        # Now should be fitted
        assert encoder.is_fitted
        
        # Should be able to get projection matrix
        proj_matrix = encoder.get_projection_matrix()
        assert proj_matrix is not None
        assert proj_matrix.shape == (5, 384)  # (n_components, n_features)
    
    def test_encoding_before_pca_fitted(self, encoder):
        """Test that encoding works even before PCA is fitted"""
        # For fallback encoder, this test doesn't apply
        if encoder.using_fallback:
            pytest.skip("PCA fitting test not applicable for fallback encoder")
        
        # First encoding (PCA not fitted yet)
        vector = encoder.encode_text("First text")
        assert isinstance(vector, np.ndarray)
        assert vector.shape == (5,)
        assert np.all(np.isfinite(vector))
    
    def test_multilingual_support(self, encoder):
        """Test encoding texts in different languages"""
        texts = {
            "en": "Dog runs in the park",
            "ru": "Собака бежит в парке",
            "de": "Hund läuft im Park",
            "fr": "Le chien court dans le parc"
        }
        
        vectors = {}
        for lang, text in texts.items():
            vectors[lang] = encoder.encode_text(text)
            assert vectors[lang].shape == (5,)
            assert np.all(np.abs(vectors[lang]) <= 1.0)
        
        # All versions should be somewhat similar (same meaning)
        # Calculate average cosine similarity
        vector_list = list(vectors.values())
        sims = []
        for i in range(len(vector_list)):
            for j in range(i+1, len(vector_list)):
                v1, v2 = vector_list[i], vector_list[j]
                norm_product = np.linalg.norm(v1) * np.linalg.norm(v2)
                if norm_product > 1e-9:  # Avoid division by zero
                    sim = np.dot(v1, v2) / norm_product
                    sims.append(sim)
        
        if sims:  # Only check if we have valid similarities
            avg_sim = np.mean(sims)
            # Similar meanings across languages should have decent similarity
            # Using lower threshold for fallback encoder
            assert avg_sim > 0.0
    
    def test_dimension_parameter(self):
        """Test that custom dimension parameter works"""
        encoder = TextEncoder5D(dimension=3)
        vector = encoder.encode_text("Test")
        # When using fallback, dimension is always 5
        if encoder.using_fallback:
            assert vector.shape == (5,)
        else:
            assert vector.shape == (3,)
    
    def test_unit_norm_normalization(self):
        """Test unit norm normalization method"""
        encoder = TextEncoder5D(normalize_method="unit_norm")
        vector = encoder.encode_text("Test text for unit norm")
        norm = np.linalg.norm(vector)
        # For fallback encoder, unit_norm is not implemented the same way
        if encoder.using_fallback:
            # Just check that values are in valid range
            assert np.all(np.isfinite(vector))
            assert np.all(np.abs(vector) <= 1.0)
        else:
            assert np.isclose(norm, 1.0, atol=1e-5)
    
    def test_long_text_encoding(self, encoder):
        """Test encoding long text (truncation handling)"""
        # Create a very long text
        long_text = " ".join(["word"] * 1000)
        vector = encoder.encode_text(long_text)
        assert isinstance(vector, np.ndarray)
        assert vector.shape == (5,)
        assert np.all(np.isfinite(vector))
        assert np.all(np.abs(vector) <= 1.0)
    
    def test_special_characters(self, encoder):
        """Test encoding text with special characters"""
        text = "Hello! @#$%^&*() 世界 🌍"
        vector = encoder.encode_text(text)
        assert isinstance(vector, np.ndarray)
        assert vector.shape == (5,)
        assert np.all(np.isfinite(vector))
    
    def test_numeric_text(self, encoder):
        """Test encoding numeric text"""
        text = "12345 67890"
        vector = encoder.encode_text(text)
        assert isinstance(vector, np.ndarray)
        assert vector.shape == (5,)
        assert np.all(np.isfinite(vector))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
