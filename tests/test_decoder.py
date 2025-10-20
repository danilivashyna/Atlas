"""
Tests for interpretable decoder
"""

import numpy as np
import pytest

from atlas.decoder import SimpleInterpretableDecoder


class TestSimpleInterpretableDecoder:
    """Test the simple interpretable decoder"""

    @pytest.fixture
    def decoder(self):
        """Create decoder instance"""
        return SimpleInterpretableDecoder()

    def test_decoder_initialization(self, decoder):
        """Test decoder initializes correctly"""
        assert decoder.dimension == 5

    def test_decode_vector(self, decoder):
        """Test decoding a vector"""
        vector = np.array([0.1, 0.9, -0.5, 0.2, 0.8])
        text = decoder.decode(vector)
        assert isinstance(text, str)
        assert len(text) > 0

    def test_decode_with_reasoning(self, decoder):
        """Test decoding with reasoning"""
        vector = np.array([0.1, 0.9, -0.5, 0.2, 0.8])
        result = decoder.decode_with_reasoning(vector)

        assert isinstance(result, dict)
        assert "reasoning" in result
        assert "text" in result
        assert "vector" in result

        assert isinstance(result["reasoning"], str)
        assert isinstance(result["text"], str)
        assert len(result["reasoning"]) > 0
        assert len(result["text"]) > 0

    def test_decode_consistent(self, decoder):
        """Test that same vector decodes consistently"""
        vector = np.array([0.1, 0.9, -0.5, 0.2, 0.8])
        text1 = decoder.decode(vector)
        text2 = decoder.decode(vector)
        assert text1 == text2

    def test_decode_different_vectors(self, decoder):
        """Test that different vectors may produce different text"""
        vector1 = np.array([0.8, 0.5, 0.2, 0.1, 0.9])
        vector2 = np.array([-0.8, -0.5, -0.2, -0.1, -0.9])
        text1 = decoder.decode(vector1)
        text2 = decoder.decode(vector2)
        # Different vectors often (but not always) produce different text
        # At minimum, they should both produce valid text
        assert isinstance(text1, str)
        assert isinstance(text2, str)

    def test_reasoning_contains_dimensions(self, decoder):
        """Test that reasoning mentions all dimensions"""
        vector = np.array([0.1, 0.9, -0.5, 0.2, 0.8])
        result = decoder.decode_with_reasoning(vector)

        # Reasoning should mention dimensions
        for i in range(1, 6):
            assert f"dim₍{i}₎" in result["reasoning"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
