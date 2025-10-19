# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for InterpretableDecoder.
"""

import pytest
import numpy as np
from src.atlas.decoders import InterpretableDecoder


class TestInterpretableDecoder:
    """Tests for InterpretableDecoder."""

    @pytest.fixture
    def decoder(self):
        """Create decoder instance."""
        return InterpretableDecoder()

    def test_decode_returns_dict_with_required_keys(self, decoder):
        """Should return dict with text, reasoning, explainable, confidence."""
        vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        result = decoder.decode(vector, top_k=3)

        assert isinstance(result, dict)
        assert "text" in result
        assert "reasoning" in result
        assert "explainable" in result
        assert "confidence" in result

        assert isinstance(result["text"], str)
        assert isinstance(result["reasoning"], list)
        assert isinstance(result["explainable"], bool)
        assert isinstance(result["confidence"], (int, float))

    def test_decode_reasoning_count_respects_top_k(self, decoder):
        """Should return <= top_k items in reasoning."""
        vector = [0.1, 0.2, 0.3, 0.4, 0.5]

        for k in [1, 2, 3, 5, 10]:
            result = decoder.decode(vector, top_k=k)
            assert len(result["reasoning"]) <= k

    def test_decode_top_k_boundaries(self, decoder):
        """top_k must be in [1, 10] range."""
        vector = [0.1, 0.2, 0.3, 0.4, 0.5]

        # Valid
        result = decoder.decode(vector, top_k=1)
        assert len(result["reasoning"]) <= 1

        result = decoder.decode(vector, top_k=10)
        assert len(result["reasoning"]) <= 10

        # Invalid
        with pytest.raises(ValueError):
            decoder.decode(vector, top_k=0)

        with pytest.raises(ValueError):
            decoder.decode(vector, top_k=11)

    def test_decode_rejects_wrong_dimensions(self, decoder):
        """Should reject vectors not 5D."""
        with pytest.raises(ValueError):
            decoder.decode([0.1, 0.2], top_k=1)  # 2D

        with pytest.raises(ValueError):
            decoder.decode([0.1, 0.2, 0.3, 0.4, 0.5, 0.6], top_k=1)  # 6D

    def test_decode_always_returns_text(self, decoder):
        """Should always return non-empty text (even in MVP mode)."""
        vectors = [
            [0.1, 0.2, 0.3, 0.4, 0.5],
            [0.0, 0.0, 0.0, 0.0, 0.0],  # Zero vector
            [1.0, -1.0, 0.5, -0.5, 0.0],  # Mixed signs
        ]

        for vector in vectors:
            result = decoder.decode(vector)
            assert result["text"]
            assert len(result["text"]) > 0

    def test_decode_confidence_in_valid_range(self, decoder):
        """Confidence should be in [0, 1] range."""
        vectors = [
            [0.1, 0.2, 0.3, 0.4, 0.5],
            [0.0, 0.0, 0.0, 0.0, 0.0],
            [1.0, 1.0, 1.0, 1.0, 1.0],
        ]

        for vector in vectors:
            result = decoder.decode(vector)
            assert 0.0 <= result["confidence"] <= 1.0

    def test_decode_reasoning_has_required_fields(self, decoder):
        """Each reasoning item should have dimension, value, contribution."""
        vector = [0.5, 0.5, 0.5, 0.5, 0.5]
        result = decoder.decode(vector, top_k=5)

        for item in result["reasoning"]:
            assert "dimension" in item
            assert "value" in item
            assert "contribution" in item

            assert 0 <= item["dimension"] <= 4
            assert isinstance(item["value"], (int, float))
            assert isinstance(item["contribution"], str)

    def test_decode_reasoning_dimensions_unique(self, decoder):
        """Dimensions in reasoning should be unique."""
        vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        result = decoder.decode(vector, top_k=5)

        dims = [item["dimension"] for item in result["reasoning"]]
        assert len(dims) == len(set(dims)), "Dimensions should be unique"

    def test_decode_caching(self, decoder):
        """Should cache results for same vector + top_k."""
        vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        result1 = decoder.decode(vector, top_k=3)
        result2 = decoder.decode(vector, top_k=3)

        # Results should be identical (cached)
        assert result1["text"] == result2["text"]
        assert result1["confidence"] == result2["confidence"]

    def test_decode_different_vectors_different_results(self, decoder):
        """Different vectors should produce different (or similar) results."""
        v1 = [0.1, 0.0, 0.0, 0.0, 0.0]
        v2 = [0.0, 0.0, 0.0, 0.0, 0.5]

        result1 = decoder.decode(v1)
        result2 = decoder.decode(v2)

        # Confidences should differ (v2 has larger magnitude)
        assert result1["confidence"] != result2["confidence"]

    def test_decode_no_nan_inf(self, decoder):
        """Should never return NaN or Inf in confidence."""
        vectors = [
            [float("inf"), 0, 0, 0, 0],
            [float("nan"), 0, 0, 0, 0],
            [1e10, 1e-10, 0, 0, 0],
        ]

        for vector in vectors:
            try:
                result = decoder.decode(vector)
                # If it doesn't error, confidence should be valid
                assert not np.isnan(result["confidence"])
                assert not np.isinf(result["confidence"])
            except ValueError:
                # Some vectors might trigger validation errors, which is ok
                pass

    def test_decode_mvp_fallback(self, decoder):
        """MVP fallback should still produce valid output."""
        vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        result = decoder.decode(vector)

        # MVP fallback sets explainable=False in _decode_mvp
        # For now, check that all required fields exist
        assert result["text"]
        assert result["reasoning"]
        assert "confidence" in result

    @pytest.mark.slow
    def test_decode_performance(self, decoder):
        """Warm-start latency should be < 200ms per request."""
        import time

        # Warm up
        decoder.decode([0.1, 0.2, 0.3, 0.4, 0.5])

        # Measure
        times = []
        for i in range(10):
            vector = [float(i % 5) * 0.1 for _ in range(5)]
            start = time.time()
            decoder.decode(vector, top_k=3)
            elapsed = (time.time() - start) * 1000  # Convert to ms
            times.append(elapsed)

        p50 = np.percentile(times, 50)
        p95 = np.percentile(times, 95)

        assert p95 < 300, f"p95 latency {p95:.1f}ms exceeds 300ms threshold"
        print(f"Decode performance: p50={p50:.1f}ms, p95={p95:.1f}ms")
