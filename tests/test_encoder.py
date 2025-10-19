"""
Tests for semantic encoder
"""

import pytest
import numpy as np

from atlas.encoder import SimpleSemanticEncoder


class TestSimpleSemanticEncoder:
    """Test the simple semantic encoder"""
    
    @pytest.fixture
    def encoder(self):
        """Create encoder instance"""
        return SimpleSemanticEncoder()
    
    def test_encoder_initialization(self, encoder):
        """Test encoder initializes correctly"""
        assert encoder.dimension == 5
    
    def test_encode_single_text(self, encoder):
        """Test encoding a single text"""
        vector = encoder.encode_text("Собака")
        assert isinstance(vector, np.ndarray)
        assert vector.shape == (5,)
        assert np.all(np.abs(vector) <= 1.0)  # Values should be in [-1, 1]
    
    def test_encode_multiple_texts(self, encoder):
        """Test encoding multiple texts"""
        texts = ["Собака", "Машина", "Любовь"]
        vectors = encoder.encode_text(texts)
        assert isinstance(vectors, np.ndarray)
        assert vectors.shape == (3, 5)
        assert np.all(np.abs(vectors) <= 1.0)
    
    def test_encode_empty_text(self, encoder):
        """Test encoding empty text raises ValueError"""
        import pytest
        with pytest.raises(ValueError, match="Input text cannot be empty"):
            encoder.encode_text("")
    
    def test_consistent_encoding(self, encoder):
        """Test that same text encodes consistently"""
        text = "Собака"
        vector1 = encoder.encode_text(text)
        vector2 = encoder.encode_text(text)
        np.testing.assert_array_equal(vector1, vector2)
    
    def test_different_texts_different_vectors(self, encoder):
        """Test that different texts produce different vectors"""
        vector1 = encoder.encode_text("Собака")
        vector2 = encoder.encode_text("Машина")
        assert not np.allclose(vector1, vector2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
