"""
Comprehensive tests for v0.5: ANN, path-aware routing, reticulum, metrics.
"""

import os

import pytest

# Set environment for all tests
os.environ["ATLAS_MEMORY_BACKEND"] = "sqlite"
os.environ["ATLAS_ROUTER_MODE"] = "on"
os.environ["ATLAS_ANN_BACKEND"] = "inproc"


@pytest.fixture
def node_store():
    """Fixture for node store with test data."""
    from atlas.memory import get_node_store

    ns = get_node_store()
    ns.flush_nodes()
    ns.flush_links()
    ns.flush_link_versions()

    # Seed test nodes
    ns.write_node("dim2", None, [0.6, 0.1, 0.2, 0.0, 0.1], label="animals", weight=0.7)
    ns.write_node("dim2/dim2.4", "dim2", [0.5, 0.0, 0.3, 0.0, 0.2], label="cats", weight=0.6)
    ns.write_node("dim2/dim2.5", "dim2", [0.4, 0.1, 0.2, 0.2, 0.1], label="dogs", weight=0.5)

    yield ns

    # Cleanup
    ns.flush_nodes()
    ns.flush_links()
    ns.flush_link_versions()


@pytest.fixture
def client():
    """Fixture for FastAPI test client."""
    from fastapi.testclient import TestClient

    from atlas.api.app import app

    return TestClient(app)


# ===== ANN Index Tests =====


def test_ann_inproc_build_and_query(node_store):
    """Test inproc ANN index build and query."""
    from atlas.router.ann_index import InprocANN

    ann = InprocANN()
    nodes = node_store.get_all_nodes()

    # Build
    ann.rebuild([(n["path"], n["vec5"]) for n in nodes])
    assert ann.size() == 3

    # Query
    query_vec = [0.6, 0.1, 0.2, 0.0, 0.1]  # Same as dim2
    results = ann.search(query_vec, top_k=2)
    assert len(results) == 2
    assert results[0][0] == "dim2"  # Exact match


def test_ann_faiss_backend_graceful_fallback():
    """Test FAISS backend (gracefully skipped if not installed)."""
    from atlas.router.ann_index import FAISSANN

    with pytest.raises(RuntimeError):
        FAISSANN()
    # Should gracefully handle missing faiss


def test_ann_off_backend():
    """Test ANN backend=off returns None."""
    from atlas.router.ann_index import get_ann_index

    ann = get_ann_index("off")
    assert ann is None


# ===== PathRouter with Path-Aware Priors =====


def test_path_router_prior_path_effect(node_store):
    """Test that path-aware priors affect ranking."""
    from atlas import SemanticSpace
    from atlas.router import PathRouter

    space = SemanticSpace()
    router = PathRouter(
        space,
        node_store,
        alpha=0.4,
        beta=0.4,
        gamma=0.1,
        delta=0.1,
        decay=0.85,
    )

    # Route a query
    scores = router.route("animals and cats", top_k=3)
    assert len(scores) <= 3
    assert all(isinstance(s.score, float) for s in scores)

    # When routing to children, prior_path should give weight to ancestors
    # (This test is primarily sanity check; exact rankings depend on encoder)


def test_path_router_with_ann(node_store):
    """Test PathRouter using ANN for candidate selection."""
    from atlas import SemanticSpace
    from atlas.router import PathRouter, get_ann_index

    space = SemanticSpace()
    ann = get_ann_index("inproc")
    nodes = node_store.get_all_nodes()
    ann.rebuild([(n["path"], n["vec5"]) for n in nodes])

    router = PathRouter(space, node_store, ann_index=ann)
    scores = router.route("kittens", top_k=3, use_ann=True)
    assert len(scores) <= 3


# ===== Router Batch API Tests =====


def test_router_batch_basic(client, node_store):
    """Test batch routing endpoint."""
    response = client.post(
        "/router/route_batch",
        json={
            "items": [
                {"text": "cats and kittens", "top_k": 3},
                {"text": "animals", "top_k": 2},
            ],
            "use_ann": False,
            "rebuild_index": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 2
    assert "trace_id" in data


def test_index_rebuild_idempotent(client, node_store):
    """Test index rebuild is idempotent."""
    # First rebuild
    response1 = client.post("/router/index/update", json={"action": "sync", "backend": "inproc"})
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["ok"] is True
    count1 = data1["size"]

    # Second rebuild (should be same)
    response2 = client.post("/router/index/update", json={"action": "sync", "backend": "inproc"})
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["size"] == count1


# ===== Reticulum Tests =====


def test_link_write_query(client, node_store):
    """Test link write and query."""
    # Write link
    response1 = client.post(
        "/reticulum/link_version",
        json={
            "path": "dim2/dim2.4",
            "content_id": "doc:cats101",
            "version": 1,
            "kind": "doc",
            "score": 0.92,
            "meta": {"title": "Cats 101"},
        },
    )
    assert response1.status_code == 200
    assert response1.json()["ok"] is True

    # Query link
    response2 = client.post("/reticulum/recent", json={"path": "dim2/dim2.4", "top_k": 5})
    assert response2.status_code == 200
    data = response2.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["content_id"] == "doc:cats101"


def test_query_subtree(client, node_store):
    """Test subtree query in reticulum."""
    # Write multiple links under dim2
    client.post(
        "/reticulum/link_version",
        json={
            "path": "dim2",
            "content_id": "doc:animals",
            "version": 1,
            "score": 0.8,
        },
    )
    client.post(
        "/reticulum/link_version",
        json={
            "path": "dim2/dim2.4",
            "content_id": "doc:cats",
            "version": 1,
            "score": 0.9,
        },
    )
    client.post(
        "/reticulum/link_version",
        json={
            "path": "dim2/dim2.5",
            "content_id": "doc:dogs",
            "version": 1,
            "score": 0.85,
        },
    )

    # Query subtree with prefix
    response = client.post("/reticulum/recent", json={"path": "dim2", "top_k": 10})
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 2  # Should get dim2 and children


def test_missing_path_grace(client):
    """Test graceful handling of missing paths."""
    response = client.post("/reticulum/recent", json={"path": "nonexistent", "top_k": 5})
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []


# ===== Metrics Tests =====


def test_metrics_exposed(client):
    """Test that v0.5 metrics are exposed in /metrics."""
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()

    # Check standard metrics
    assert "requests_total" in data
    assert "errors_total" in data

    # Check v0.5 mensum metrics (if present)
    if "v0_5_mensum" in data:
        mensum = data["v0_5_mensum"]
        assert "router" in mensum
        assert "reticulum" in mensum
        assert "nodes" in mensum


# ===== OpenAPI & Root Endpoint =====


def test_openapi_has_v0_5_endpoints(client):
    """Test that OpenAPI schema includes v0.5 endpoints."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()

    paths = schema["paths"].keys()
    assert "/router/route_batch" in paths
    assert "/router/index/update" in paths
    assert "/reticulum/link_version" in paths
    assert "/reticulum/recent" in paths


def test_root_endpoint_includes_v0_5(client):
    """Test that root endpoint documents v0.5 features."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()

    assert "endpoints" in data
    endpoints = data["endpoints"]

    # Check v0.5 additions
    assert "reticulum" in endpoints
    assert isinstance(endpoints["router"], dict)
    assert "route_batch" in endpoints["router"]
    assert "index_rebuild" in endpoints["router"]
