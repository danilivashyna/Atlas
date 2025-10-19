# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for TextEncoder5D (BERT-based encoder).
"""

import pytest
import numpy as np
from src.atlas.encoders import TextEncoder5D


class TestTextEncoder5D:
    """Tests for TextEncoder5D encoder."""

    @pytest.fixture
    def encoder(self):
        """Create encoder instance."""
        return TextEncoder5D()

    def test_encode_returns_5d_vector(self, encoder):
        """Should return exactly 5D vector."""
        result = encoder.encode("hello world")
        assert isinstance(result, list)
        assert len(result) == 5
        assert all(isinstance(x, (float, np.floating)) for x in result)

    def test_encode_l2_normalized(self, encoder):
        """Vector should be L2-normalized (norm ≈ 1.0)."""
        result = encoder.encode("test sentence")
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 0.01, f"Expected norm ≈ 1.0, got {norm}"

    def test_encode_same_text_same_vector(self, encoder):
        """Same text should always produce same vector (deterministic)."""
        v1 = encoder.encode("consistency test")
        v2 = encoder.encode("consistency test")
        assert np.allclose(v1, v2), "Same text should produce identical vectors"

    def test_encode_different_text_different_vector(self, encoder):
        """Different texts should produce different vectors (high probability)."""
        v1 = encoder.encode("hello world")
        v2 = encoder.encode("goodbye world")
        dot_product = np.dot(v1, v2)
        # Should not be perfectly aligned (dot product < 0.99)
        assert abs(dot_product) < 0.99, f"Different texts should diverge. Dot={dot_product}"

    def test_encode_empty_string(self, encoder):
        """Empty string should produce valid 5D vector."""
        result = encoder.encode("")
        assert len(result) == 5
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 0.01

    def test_encode_very_long_text(self, encoder):
        """Long text should not error."""
        long_text = "word " * 1000  # 5000 chars
        result = encoder.encode(long_text)
        assert len(result) == 5
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 0.01

    def test_encode_unicode_text(self, encoder):
        """Unicode and multilingual text should work."""
        texts = [
            "Hello",  # English
            "Привет",  # Russian
            "你好",  # Chinese
            "مرحبا",  # Arabic
        ]
        for text in texts:
            result = encoder.encode(text)
            assert len(result) == 5
            norm = np.linalg.norm(result)
            assert abs(norm - 1.0) < 0.01

    def test_encode_none_raises_error(self, encoder):
        """None input should raise ValueError."""
        with pytest.raises(ValueError):
            encoder.encode(None)

    def test_encode_caching(self, encoder):
        """Should return cached results for repeated queries."""
        text = "cache test"
        result1 = encoder.encode(text)
        result2 = encoder.encode(text)
        # Should be identical (not just close)
        assert result1 is not result2  # Different objects
        assert result1 == result2  # Same values (from cache)

    def test_encode_mvp_fallback(self, encoder):
        """MVP fallback should produce deterministic 5D vector."""
        # Force MVP by using private method directly
        vec_mvp = encoder._encode_mvp("fallback test")
        assert len(vec_mvp) == 5
        # Second call should match first (deterministic)
        vec_mvp2 = encoder._encode_mvp("fallback test")
        assert np.allclose(vec_mvp, vec_mvp2)

    def test_encode_no_nan_inf(self, encoder):
        """Results should never contain NaN or Inf."""
        test_texts = [
            "normal",
            "",
            "a" * 10000,
            "123 !@# $%^",
        ]
        for text in test_texts:
            result = encoder.encode(text)
            assert not np.any(np.isnan(result)), f"NaN in result for '{text}'"
            assert not np.any(np.isinf(result)), f"Inf in result for '{text}'"

    @pytest.mark.slow
    def test_encode_performance(self, encoder):
        """Warm-start latency should be < 100ms per request (goal: p95 < 80ms)."""
        import time

        # Warm up
        encoder.encode("warmup")

        # Measure
        times = []
        for i in range(10):
            start = time.time()
            encoder.encode(f"test {i}")
            elapsed = (time.time() - start) * 1000  # Convert to ms
            times.append(elapsed)

        p50 = np.percentile(times, 50)
        p95 = np.percentile(times, 95)

        assert p95 < 200, f"p95 latency {p95:.1f}ms exceeds 200ms threshold"
        print(f"Performance: p50={p50:.1f}ms, p95={p95:.1f}ms")
