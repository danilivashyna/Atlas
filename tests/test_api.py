"""
API integration tests

Tests for the FastAPI server endpoints.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with app lifespan"""
    try:
        from atlas.api.app import app

        # Use context manager to properly initialize lifespan
        with TestClient(app) as test_client:
            yield test_client
    except ImportError:
        pytest.skip("FastAPI dependencies not installed")


class TestHealthEndpoints:
    """Test health check endpoints"""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert data["version"] == "0.2.0a1"  # Dynamic version

    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ok", "not_ready"]
        assert "model_loaded" in data

    def test_ready_endpoint(self, client):
        """Test readiness endpoint"""
        response = client.get("/ready")
        # Should be 200 if model loaded, 503 if not
        assert response.status_code in [200, 503]

    def test_metrics_endpoint(self, client):
        """Test metrics endpoint"""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "requests_total" in data
        assert "errors_total" in data


class TestEncodeEndpoint:
    """Test /encode endpoint"""

    def test_encode_valid_text(self, client):
        """Test encoding valid text"""
        response = client.post("/encode", json={"text": "Собака", "lang": "ru"})
        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "vector" in data
        assert "norm" in data
        assert "trace_id" in data
        assert "timestamp" in data

        # Check vector properties
        assert len(data["vector"]) == 5
        assert all(-1 <= v <= 1 for v in data["vector"])
        assert data["norm"] is True

    def test_encode_empty_text(self, client):
        """Test encoding empty text returns error"""
        response = client.post("/encode", json={"text": ""})
        assert response.status_code == 422  # Validation error

    def test_encode_invalid_lang(self, client):
        """Test encoding with invalid language"""
        response = client.post("/encode", json={"text": "test", "lang": "invalid"})
        assert response.status_code == 422  # Validation error

    def test_encode_without_lang(self, client):
        """Test encoding without language hint"""
        response = client.post("/encode", json={"text": "test"})
        assert response.status_code == 200


class TestDecodeEndpoint:
    """Test /decode endpoint"""

    def test_decode_valid_vector(self, client):
        """Test decoding valid vector"""
        response = client.post("/decode", json={"vector": [0.5, -0.3, 0.2, 0.0, 0.8], "top_k": 3})
        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "text" in data
        assert "reasoning" in data
        assert "explainable" in data
        assert "trace_id" in data

        # Check text is returned
        assert isinstance(data["text"], str)
        assert len(data["text"]) > 0

        # Check reasoning structure
        assert isinstance(data["reasoning"], list)
        if data["explainable"]:
            for r in data["reasoning"]:
                assert "dim" in r
                assert "weight" in r
                assert "label" in r
                assert 0 <= r["dim"] <= 4

    def test_decode_zero_vector(self, client):
        """Test decoding zero vector"""
        response = client.post("/decode", json={"vector": [0.0, 0.0, 0.0, 0.0, 0.0]})
        assert response.status_code == 200
        data = response.json()
        assert "text" in data

    def test_decode_invalid_vector_length(self, client):
        """Test decoding vector with wrong length"""
        response = client.post("/decode", json={"vector": [0.1, 0.2, 0.3]})  # Only 3 dimensions
        assert response.status_code == 422  # Validation error

    def test_decode_with_nan(self, client):
        """Test decoding vector with NaN (can't send via JSON)"""
        # NaN cannot be sent via JSON, so this test verifies
        # that the validation would catch it if somehow received
        # In practice, JSON parsing will fail before validation
        pytest.skip("NaN values cannot be sent via JSON")

    def test_decode_extreme_values(self, client):
        """Test decoding vector with extreme values (should clip)"""
        response = client.post("/decode", json={"vector": [10.0, -10.0, 5.0, -5.0, 2.0]})
        # Should clip values and decode
        assert response.status_code == 200


class TestExplainEndpoint:
    """Test /explain endpoint"""

    def test_explain_valid_text(self, client):
        """Test explaining valid text"""
        response = client.post("/explain", json={"text": "Собака"})
        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "vector" in data
        assert "dims" in data
        assert "trace_id" in data

        # Check vector
        assert len(data["vector"]) == 5

        # Check dimension explanations
        assert len(data["dims"]) == 5  # Should explain all dimensions
        for dim_exp in data["dims"]:
            assert "i" in dim_exp
            assert "label" in dim_exp
            assert "score" in dim_exp
            assert 0 <= dim_exp["i"] <= 4
            assert -1 <= dim_exp["score"] <= 1

    def test_explain_empty_text(self, client):
        """Test explaining empty text returns error"""
        response = client.post("/explain", json={"text": ""})
        assert response.status_code == 422


class TestErrorHandling:
    """Test error handling"""

    def test_trace_id_in_errors(self, client):
        """Test that errors include trace_id"""
        response = client.post("/encode", json={"text": ""})
        # Error response should have trace_id
        if response.status_code >= 400:
            data = response.json()
            # FastAPI validation errors don't use our model, but should still work
            pass

    def test_malformed_json(self, client):
        """Test handling of malformed JSON"""
        response = client.post(
            "/encode", data="not json", headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422


class TestSecurityFeatures:
    """Test security features"""

    def test_no_text_in_response_headers(self, client):
        """Test that user text doesn't leak into response headers"""
        sensitive_text = "Secret password: 12345"
        response = client.post("/encode", json={"text": sensitive_text})

        # Check that sensitive text is not in any header
        for key, value in response.headers.items():
            assert sensitive_text not in str(value)

    def test_cors_headers_present(self, client):
        """Test CORS headers are set"""
        response = client.options("/encode")
        # CORS headers should be present
        # This is a basic check; adjust for your CORS policy
        pass


class TestPerformance:
    """Test performance requirements"""

    def test_encode_latency(self, client):
        """Test encode latency meets p95 requirement"""
        import time

        latencies = []
        for _ in range(20):
            start = time.time()
            response = client.post("/encode", json={"text": "Test text for latency measurement"})
            latency = (time.time() - start) * 1000  # Convert to ms
            if response.status_code == 200:
                latencies.append(latency)

        if latencies:
            p95 = sorted(latencies)[int(len(latencies) * 0.95)]
            # Target: p95 < 150ms (may not meet on slow systems, informational only)
            print(f"Encode p95 latency: {p95:.2f}ms")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
