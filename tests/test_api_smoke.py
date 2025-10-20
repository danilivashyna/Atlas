# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Smoke tests for Atlas API v0.2.

Quick validation of core endpoints:
- /health: API is alive
- /encode_h: Hierarchical encoding
- /decode_h: Hierarchical decoding
- /docs: Swagger UI available
"""

from fastapi.testclient import TestClient
from atlas.api.app import app

client = TestClient(app)


def test_health():
    """Test /health endpoint returns 200."""
    r = client.get("/health")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    assert "status" in data, "Response must contain 'status' field"


def test_encode_h_basic():
    """Test /encode_h endpoint with simple text."""
    r = client.post("/encode_h", json={"text": "Собака", "max_depth": 1})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert "tree" in data, "Response must contain 'tree' field"
    assert "norm" in data, "Response must contain 'norm' field"

    tree = data["tree"]
    assert "value" in tree, "Tree node must have 'value' field"
    assert len(tree["value"]) == 5, "Value must be 5-dimensional"


def test_decode_h_basic():
    """Test /decode_h endpoint with sample tree."""
    # First encode
    r = client.post("/encode_h", json={"text": "Собака", "max_depth": 1})
    assert r.status_code == 200
    tree = r.json()["tree"]

    # Then decode
    r2 = client.post("/decode_h", json={"tree": tree, "top_k": 3})
    assert r2.status_code == 200, f"Expected 200, got {r2.status_code}: {r2.text}"
    data = r2.json()
    assert "text" in data, "Response must contain 'text' field"
    assert "reasoning" in data, "Response must contain 'reasoning' field"


def test_encode_h_decode_h_roundtrip():
    """Test encode_h → decode_h roundtrip."""
    text = "Кот прыгает быстро"

    # Encode
    r1 = client.post("/encode_h", json={"text": text, "max_depth": 2})
    assert r1.status_code == 200
    tree = r1.json()["tree"]

    # Decode
    r2 = client.post("/decode_h", json={"tree": tree, "top_k": 5})
    assert r2.status_code == 200

    body = r2.json()
    assert isinstance(body.get("text"), str), "Decoded text must be string"
    assert isinstance(body.get("reasoning"), list), "Reasoning must be list"


def test_explain_h_basic():
    """Test /explain_h endpoint with simple text."""
    r = client.post("/explain_h", json={"text": "Собака", "max_depth": 1})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert "tree" in data, "Response must contain 'tree' field"
    assert "nodes" in data, "Response must contain 'nodes' field"

    # Check tree structure
    tree = data["tree"]
    assert "value" in tree, "Tree node must have 'value' field"
    assert len(tree["value"]) == 5, "Value must be 5-dimensional"

    # Check nodes explanations
    nodes = data["nodes"]
    assert isinstance(nodes, list), "Nodes must be a list"
    assert len(nodes) > 0, "Must have at least root node explanation"

    # Check first node (root)
    root_node = nodes[0]
    assert "path" in root_node, "Node must have 'path' field"
    assert "label" in root_node, "Node must have 'label' field"
    assert "value" in root_node, "Node must have 'value' field"
    assert len(root_node["value"]) == 5, "Node value must be 5-dimensional"


def test_explain_h_with_depth():
    """Test /explain_h endpoint with different depths."""
    text = "Кот прыгает быстро"

    # Depth 0: only root
    r0 = client.post("/explain_h", json={"text": text, "max_depth": 0})
    assert r0.status_code == 200
    nodes0 = r0.json()["nodes"]
    assert len(nodes0) >= 1, "Should have at least root node"

    # Depth 1: root + children
    r1 = client.post("/explain_h", json={"text": text, "max_depth": 1})
    assert r1.status_code == 200
    nodes1 = r1.json()["nodes"]
    # Should have more nodes than depth 0 (root + some children)
    assert len(nodes1) >= len(nodes0), "Depth 1 should have at least as many nodes as depth 0"


def test_explain_h_empty_text():
    """Test /explain_h endpoint with empty text."""
    r = client.post("/explain_h", json={"text": ""})
    assert r.status_code == 422, f"Expected 422 for empty text, got {r.status_code}"


def test_docs_available():
    """Test /docs (Swagger UI) is available."""
    r = client.get("/docs")
    assert r.status_code == 200, f"Expected 200 for /docs, got {r.status_code}"
    assert "swagger" in r.text.lower(), "/docs should contain Swagger UI"


def test_openapi_schema():
    """Test OpenAPI schema is available."""
    r = client.get("/openapi.json")
    assert r.status_code == 200, f"Expected 200 for /openapi.json, got {r.status_code}"
    schema = r.json()
    assert "paths" in schema, "Schema must contain 'paths'"
    assert "/encode_h" in schema["paths"], "Schema must document /encode_h"
    assert "/decode_h" in schema["paths"], "Schema must document /decode_h"
    assert "/explain_h" in schema["paths"], "Schema must document /explain_h"


if __name__ == "__main__":
    # Run with: pytest -v tests/test_api_smoke.py
    pass
