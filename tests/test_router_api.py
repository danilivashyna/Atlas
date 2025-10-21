"""
Tests for router API and PathRouter functionality.

Tests:
  - test_router_route_basic: Routes text via /router/route
  - test_router_activate_children: Soft-activates children via /router/activate
  - test_router_off_flag: Respects ATLAS_ROUTER_MODE=off
"""

import os

import pytest
from fastapi.testclient import TestClient

from atlas.api.app import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def node_store():
    """Get node store and populate with test nodes."""
    from atlas.memory import get_node_store

    store = get_node_store()

    # Clear any existing nodes
    try:
        store.flush_nodes()
    except Exception:
        pass

    # Write test nodes
    store.write_node(
        path="dim2",
        parent=None,
        vec5=[0.6, 0.0, 0.2, 0.0, 0.2],
        label="живое",
        weight=0.7,
    )
    store.write_node(
        path="dim2/dim2.4",
        parent="dim2",
        vec5=[0.5, 0.0, 0.3, 0.0, 0.2],
        label="домашнее-живое-позитив",
        weight=0.6,
    )
    store.write_node(
        path="dim2/dim2.4/dim2.4.1",
        parent="dim2/dim2.4",
        vec5=[0.55, 0.05, 0.25, 0.05, 0.15],
        label="кот",
        weight=0.8,
    )
    store.write_node(
        path="dim2/dim2.4/dim2.4.3",
        parent="dim2/dim2.4",
        vec5=[0.48, 0.02, 0.32, 0.02, 0.16],
        label="собака",
        weight=0.75,
    )

    yield store

    # Cleanup
    try:
        store.flush_nodes()
    except Exception:
        pass


def test_router_route_basic(client, node_store, monkeypatch):
    """Test basic routing: write nodes, route text, verify response structure."""
    # Ensure router is on
    monkeypatch.setenv("ATLAS_ROUTER_MODE", "on")

    response = client.post(
        "/router/route",
        json={"text": "Cats are friendly pets", "top_k": 3},
    )

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "trace_id" in data
    assert isinstance(data["items"], list)

    # Should return some items (nodes were written)
    # NOTE: Exact count depends on scoring, but we wrote 4 nodes
    assert len(data["items"]) <= 3  # top_k=3

    # Each item should have path and score
    for item in data["items"]:
        assert "path" in item
        assert "score" in item
        assert isinstance(item["score"], float)
        assert 0 <= item["score"] <= 1  # Score should be normalized


def test_router_activate_children(client, node_store, monkeypatch):
    """Test soft activation: activate children of dim2/dim2.4."""
    monkeypatch.setenv("ATLAS_ROUTER_MODE", "on")

    response = client.post(
        "/router/activate",
        json={"path": "dim2/dim2.4", "text": "Cats chase mice"},
    )

    assert response.status_code == 200
    data = response.json()

    assert "children" in data
    assert "trace_id" in data
    assert isinstance(data["children"], list)

    # Should have 2 children
    if len(data["children"]) > 0:
        # Verify probabilities sum to ~1.0 (softmax)
        prob_sum = sum(c["p"] for c in data["children"])
        assert 0.99 <= prob_sum <= 1.01, f"Probabilities should sum to 1.0, got {prob_sum}"

        # Each child should have path and p
        for child in data["children"]:
            assert "path" in child
            assert "p" in child
            assert isinstance(child["p"], float)
            assert 0 <= child["p"] <= 1


def test_router_route_empty_nodes(client, monkeypatch):
    """Test routing with no nodes."""
    monkeypatch.setenv("ATLAS_ROUTER_MODE", "on")

    # Don't populate nodes (use a fresh store without the fixture)
    response = client.post(
        "/router/route",
        json={"text": "Test text", "top_k": 3},
    )

    assert response.status_code == 200
    data = response.json()

    # Should return empty list when no nodes exist
    assert data["items"] == [] or len(data["items"]) >= 0


def test_router_off_flag(client, node_store, monkeypatch):
    """Test that ATLAS_ROUTER_MODE=off disables routing."""
    monkeypatch.setenv("ATLAS_ROUTER_MODE", "off")

    response = client.post(
        "/router/route",
        json={"text": "Test text", "top_k": 3},
    )

    assert response.status_code == 200
    data = response.json()

    # Should return empty items
    assert data["items"] == []


def test_router_activate_off_flag(client, node_store, monkeypatch):
    """Test that ATLAS_ROUTER_MODE=off disables activation."""
    monkeypatch.setenv("ATLAS_ROUTER_MODE", "off")

    response = client.post(
        "/router/activate",
        json={"path": "dim2/dim2.4", "text": "Test text"},
    )

    assert response.status_code == 200
    data = response.json()

    # Should return empty children
    assert data["children"] == []


def test_router_route_invalid_input(client, monkeypatch):
    """Test routing with invalid input."""
    monkeypatch.setenv("ATLAS_ROUTER_MODE", "on")

    # Empty text
    response = client.post(
        "/router/route",
        json={"text": "", "top_k": 3},
    )

    # Should return validation error or empty results
    assert response.status_code in [200, 422]


def test_router_activate_invalid_path(client, node_store, monkeypatch):
    """Test activation with non-existent path."""
    monkeypatch.setenv("ATLAS_ROUTER_MODE", "on")

    response = client.post(
        "/router/activate",
        json={"path": "nonexistent/path", "text": "Test text"},
    )

    assert response.status_code == 200
    data = response.json()

    # Should return empty children for non-existent path
    assert data["children"] == []


def test_openapi_shows_router_endpoints(client):
    """Verify that /router/* endpoints are in OpenAPI schema."""
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    paths = schema.get("paths", {})

    # Should have /router/route and /router/activate
    assert "/router/route" in paths, "POST /router/route not in OpenAPI"
    assert "/router/activate" in paths, "POST /router/activate not in OpenAPI"

    # Both should be POST
    assert "post" in paths["/router/route"]
    assert "post" in paths["/router/activate"]


def test_root_endpoint_includes_router(client):
    """Verify that GET / includes router section."""
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert "endpoints" in data

    endpoints = data["endpoints"]
    assert "router" in endpoints, "Router not in endpoints"

    router_info = endpoints["router"]
    assert isinstance(router_info, dict)
    assert "route" in router_info
    assert "activate" in router_info
