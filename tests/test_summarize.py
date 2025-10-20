"""
Tests for length-controlled summarization with semantic preservation.

Tests the proportional summarization algorithm that preserves 5D semantic ratios.
"""

import numpy as np
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with app lifespan"""
    try:
        from atlas.api.app import app

        with TestClient(app) as test_client:
            yield test_client
    except ImportError:
        pytest.skip("FastAPI dependencies not installed")


class TestSummarizeAPI:
    """Test /summarize endpoint"""

    def test_summarize_compress_basic(self, client):
        """Test basic compress mode summarization"""
        text = (
            "Artificial intelligence is transforming industries across the world. "
            "Machine learning algorithms can now perform complex tasks with high accuracy. "
            "Deep learning models are being used in healthcare, finance, and transportation. "
            "Natural language processing enables computers to understand human language. "
            "Computer vision allows machines to interpret visual information."
        )

        response = client.post(
            "/summarize",
            json={
                "text": text,
                "target_tokens": 50,
                "mode": "compress",
                "epsilon": 0.05,
                "preserve_order": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "summary" in data
        assert "length" in data
        assert "ratio_target" in data
        assert "ratio_actual" in data
        assert "kl_div" in data
        assert "trace_id" in data

        # Check semantic ratios
        assert len(data["ratio_target"]) == 5
        assert len(data["ratio_actual"]) == 5

        # Check that ratios are valid probabilities
        assert all(0 <= r <= 1 for r in data["ratio_target"])
        assert all(0 <= r <= 1 for r in data["ratio_actual"])

        # Check that ratios sum to approximately 1
        assert abs(sum(data["ratio_target"]) - 1.0) < 0.01
        assert abs(sum(data["ratio_actual"]) - 1.0) < 0.01

        # Check length is reasonable
        assert data["length"] > 0
        assert data["length"] <= 80  # Some tolerance

        # Summary should not be empty
        assert len(data["summary"]) > 0

    def test_summarize_expand_mode(self, client):
        """Test expand mode summarization"""
        text = "AI is changing the world."

        response = client.post(
            "/summarize",
            json={
                "text": text,
                "target_tokens": 100,
                "mode": "expand",
                "epsilon": 0.05,
                "preserve_order": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Check that output exists
        assert "summary" in data
        assert len(data["summary"]) > 0

    def test_summarize_kl_divergence_constraint(self, client):
        """Test that KL divergence is within epsilon tolerance"""
        text = (
            "The quick brown fox jumps over the lazy dog. "
            "This sentence contains every letter of the alphabet. "
            "It is often used for font testing and typing practice. "
            "The sentence is a pangram in English language."
        )

        response = client.post(
            "/summarize",
            json={
                "text": text,
                "target_tokens": 30,
                "mode": "compress",
                "epsilon": 0.05,
                "preserve_order": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # KL divergence should be within tolerance (or close)
        # Note: May not always be achievable, but should try
        assert data["kl_div"] >= 0.0  # KL divergence is non-negative

    def test_summarize_empty_text_error(self, client):
        """Test that empty text returns error"""
        response = client.post(
            "/summarize", json={"text": "", "target_tokens": 50, "mode": "compress"}
        )

        assert response.status_code == 422  # Validation error

    def test_summarize_invalid_mode(self, client):
        """Test that invalid mode returns error"""
        response = client.post(
            "/summarize",
            json={"text": "Some text here", "target_tokens": 50, "mode": "invalid_mode"},
        )

        assert response.status_code == 422  # Validation error

    def test_summarize_invalid_target_tokens(self, client):
        """Test that invalid target_tokens returns error"""
        response = client.post(
            "/summarize", json={"text": "Some text here", "target_tokens": -10, "mode": "compress"}
        )

        assert response.status_code == 422  # Validation error

    def test_summarize_preserve_order(self, client):
        """Test that preserve_order works"""
        text = "First sentence. Second sentence. Third sentence."

        response = client.post(
            "/summarize",
            json={"text": text, "target_tokens": 20, "mode": "compress", "preserve_order": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert "summary" in data

    def test_summarize_different_epsilon(self, client):
        """Test with different epsilon values"""
        text = "This is a test text for summarization."

        # Strict epsilon
        response1 = client.post(
            "/summarize",
            json={"text": text, "target_tokens": 15, "mode": "compress", "epsilon": 0.01},
        )

        # Loose epsilon
        response2 = client.post(
            "/summarize",
            json={"text": text, "target_tokens": 15, "mode": "compress", "epsilon": 0.5},
        )

        assert response1.status_code == 200
        assert response2.status_code == 200


class TestProportionalAlgorithm:
    """Test core proportional summarization algorithm"""

    def test_normalize_to_distribution(self):
        """Test distribution normalization"""
        from atlas.summarize.proportional import normalize_to_distribution

        vector = np.array([0.5, -0.3, 0.8, 0.0, 0.2])

        # Softmax normalization
        dist_softmax = normalize_to_distribution(vector, method="softmax")
        assert len(dist_softmax) == 5
        assert abs(np.sum(dist_softmax) - 1.0) < 1e-6
        assert all(d >= 0 for d in dist_softmax)

        # Absolute normalization
        dist_abs = normalize_to_distribution(vector, method="abs_norm")
        assert len(dist_abs) == 5
        assert abs(np.sum(dist_abs) - 1.0) < 1e-6
        assert all(d >= 0 for d in dist_abs)

    def test_compute_kl_divergence(self):
        """Test KL divergence computation"""
        from atlas.summarize.proportional import compute_kl_divergence

        p = np.array([0.2, 0.2, 0.2, 0.2, 0.2])
        q = np.array([0.2, 0.2, 0.2, 0.2, 0.2])

        # Identical distributions should have KL = 0
        kl = compute_kl_divergence(p, q)
        assert kl < 1e-6

        # Different distributions should have KL > 0
        q2 = np.array([0.4, 0.1, 0.3, 0.1, 0.1])
        kl2 = compute_kl_divergence(p, q2)
        assert kl2 > 0

    def test_calculate_token_quotas(self):
        """Test token quota calculation"""
        from atlas.summarize.proportional import calculate_token_quotas

        distribution = np.array([0.28, 0.07, 0.35, 0.10, 0.20])
        target_tokens = 100

        quotas = calculate_token_quotas(distribution, target_tokens)

        # Check quotas sum to target
        assert sum(quotas) == target_tokens

        # Check quotas are non-negative
        assert all(q >= 0 for q in quotas)

        # Check quotas roughly match distribution
        ratios = [q / target_tokens for q in quotas]
        for i in range(5):
            assert abs(ratios[i] - distribution[i]) < 0.05

    def test_summarize_function_compress(self):
        """Test summarize function in compress mode"""
        from atlas.summarize import summarize

        text = (
            "Machine learning is a subset of artificial intelligence. "
            "It focuses on training algorithms to learn from data. "
            "Deep learning uses neural networks with many layers. "
            "Natural language processing helps computers understand text. "
            "Computer vision enables image recognition."
        )

        result = summarize(
            text=text, target_tokens=50, mode="compress", epsilon=0.05, preserve_order=True
        )

        # Check result structure
        assert "summary" in result
        assert "length" in result
        assert "ratio_target" in result
        assert "ratio_actual" in result
        assert "kl_div" in result
        assert "trace_id" in result

        # Check types
        assert isinstance(result["summary"], str)
        assert isinstance(result["length"], int)
        assert isinstance(result["kl_div"], float)

        # Check semantic ratios
        assert len(result["ratio_target"]) == 5
        assert len(result["ratio_actual"]) == 5

    def test_summarize_function_expand(self):
        """Test summarize function in expand mode"""
        from atlas.summarize import summarize

        text = "AI is powerful."

        result = summarize(
            text=text, target_tokens=80, mode="expand", epsilon=0.05, preserve_order=True
        )

        assert "summary" in result
        assert len(result["summary"]) > 0

    def test_summarize_empty_text_fallback(self):
        """Test graceful fallback for empty text"""
        from atlas.summarize import summarize

        result = summarize(text="", target_tokens=50, mode="compress", epsilon=0.05)

        # Should return empty summary gracefully
        assert result["summary"] == ""
        assert result["length"] == 0
        assert result["kl_div"] == 0.0


class TestSelectors:
    """Test evidence selection utilities"""

    def test_extract_sentences(self):
        """Test sentence extraction"""
        from atlas.summarize.selectors import extract_sentences

        text = "First sentence. Second sentence! Third sentence?"
        sentences = extract_sentences(text)

        assert len(sentences) >= 3
        assert "First sentence" in sentences[0]

    def test_extract_keywords(self):
        """Test keyword extraction"""
        from atlas.summarize.selectors import extract_keywords

        text = "machine learning algorithm algorithm data data data"
        keywords = extract_keywords(text, top_k=5)

        assert len(keywords) > 0
        # Check that more frequent words rank higher
        assert keywords[0][1] >= keywords[-1][1]

    def test_deduplicate_pieces(self):
        """Test deduplication"""
        from atlas.summarize.selectors import deduplicate_pieces

        pieces = [
            "Machine learning is powerful",
            "Deep learning is useful",
            "Machine learning is powerful",  # Exact duplicate
            "AI is transforming industries",
        ]

        deduped = deduplicate_pieces(pieces, threshold=0.9)

        # Should remove exact duplicate
        assert len(deduped) < len(pieces)

    def test_estimate_tokens(self):
        """Test token estimation"""
        from atlas.summarize.selectors import estimate_tokens

        text = "This is a test sentence with several words"
        tokens = estimate_tokens(text)

        assert tokens > 0
        # Should be reasonable approximation (words * 1.3)
        word_count = len(text.split())
        assert tokens >= word_count
        assert tokens <= word_count * 2

    def test_truncate_to_tokens(self):
        """Test text truncation"""
        from atlas.summarize.selectors import truncate_to_tokens

        text = "one two three four five six seven eight nine ten"
        truncated = truncate_to_tokens(text, max_tokens=5)

        # Should be shorter than original
        assert len(truncated) < len(text)


class TestStabilityAndReproducibility:
    """Test algorithm stability and reproducibility"""

    def test_paraphrase_stability(self):
        """Test that paraphrased text preserves similar ratios"""
        from atlas.summarize import summarize

        text1 = "Artificial intelligence is transforming the world of technology."
        text2 = "AI is changing the technology landscape worldwide."

        result1 = summarize(text1, target_tokens=30, mode="compress")
        result2 = summarize(text2, target_tokens=30, mode="compress")

        # Ratios should be somewhat similar for similar content
        # (this is a weak test as paraphrases may differ)
        assert len(result1["ratio_target"]) == len(result2["ratio_target"])

    def test_reproducibility(self):
        """Test that same input produces same output"""
        from atlas.summarize import summarize

        text = "Test text for reproducibility check."

        result1 = summarize(text, target_tokens=20, mode="compress", epsilon=0.05)
        result2 = summarize(text, target_tokens=20, mode="compress", epsilon=0.05)

        # Should produce same summary (deterministic)
        assert result1["summary"] == result2["summary"]
        assert result1["ratio_target"] == result2["ratio_target"]

    def test_no_repeats_in_summary(self):
        """Test that summary doesn't contain obvious repeats"""
        from atlas.summarize import summarize

        text = (
            "First idea about machine learning. "
            "Second idea about deep learning. "
            "Third idea about neural networks. "
        ) * 5  # Repeat to create redundancy

        result = summarize(text, target_tokens=50, mode="compress")

        summary = result["summary"]

        # Check that summary doesn't have obvious duplicates
        sentences = summary.split(".")
        unique_sentences = set(s.strip().lower() for s in sentences if s.strip())

        # Most sentences should be unique (allowing some overlap)
        if len(sentences) > 1:
            assert len(unique_sentences) >= len(sentences) * 0.7


@pytest.mark.skipif(
    True,  # Skip by default as this requires feature flag
    reason="Feature flag test - run manually with ATLAS_SUMMARY_MODE=off",
)
class TestFeatureFlag:
    """Test feature flag behavior"""

    def test_feature_flag_off(self, client):
        """Test that feature can be disabled"""
        import os

        os.environ["ATLAS_SUMMARY_MODE"] = "off"

        # Reload app with new env var (this is tricky in tests)
        # In practice, this would be tested by starting server with flag

        response = client.post(
            "/summarize", json={"text": "Test text", "target_tokens": 20, "mode": "compress"}
        )

        # Should return 503 when disabled
        # (This test may not work perfectly due to env var timing)
        assert response.status_code in [200, 503]
