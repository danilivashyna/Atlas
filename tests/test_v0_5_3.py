"""
Tests for v0.5.3: Reticulum+ (versions, reverse links, recency)
"""

import os

import pytest

from atlas.memory import get_node_store


@pytest.fixture
def node_store():
    """Fixture with test nodes."""
    store = get_node_store()
    # Clear existing
    store.flush_links()
    store.flush_link_versions()
    store.flush_nodes()
    # Add test nodes
    store.write_node("dim1", None, [0.1, 0.2, 0.3, 0.4, 0.5], "Dim1", 1.0)
    store.write_node("dim1/dim1.1", "dim1", [0.2, 0.3, 0.4, 0.5, 0.6], "Dim1.1", 0.8)
    store.write_node("dim2", None, [0.5, 0.4, 0.3, 0.2, 0.1], "Dim2", 1.0)
    yield store
    store.flush_links()
    store.flush_link_versions()
    store.flush_nodes()


def test_link_versions_write_and_get(node_store):
    """Test writing and retrieving link versions."""
    # Write version 1
    node_store.write_link_version("dim1", "doc:cats", 1, 0.8, "doc", {"title": "Cats"})

    # Write version 2
    node_store.write_link_version("dim1", "doc:cats", 2, 0.9, "doc", {"title": "Cats Updated"})

    # Get all versions
    versions = node_store.get_link_versions("doc:cats")
    assert len(versions) == 2

    # Check ordering (desc by version)
    assert versions[0]["version"] == 2
    assert versions[0]["score"] == 0.9
    assert versions[1]["version"] == 1
    assert versions[1]["score"] == 0.8


def test_resolve_latest_links(node_store):
    """Test resolving latest links by content_id."""
    # Link same content to multiple nodes with different versions
    node_store.write_link_version("dim1", "doc:cats", 1, 0.8)
    node_store.write_link_version("dim1", "doc:cats", 2, 0.9)
    node_store.write_link_version("dim2", "doc:cats", 1, 0.7)

    # Resolve latest
    latest = node_store.resolve_latest("doc:cats", top_k=5)
    assert len(latest) == 2  # Two nodes

    # Should have latest versions
    paths = {item["node_path"] for item in latest}
    assert "dim1" in paths
    assert "dim2" in paths

    versions = {item["version"] for item in latest}
    assert 2 in versions  # dim1 has v2
    assert 1 in versions  # dim2 has v1


def test_reverse_query_by_content(node_store):
    """Test querying nodes by content_id."""
    # Link content to nodes
    node_store.write_link_version("dim1", "doc:cats", 1, 0.8)
    node_store.write_link_version("dim2", "doc:dogs", 1, 0.9)
    node_store.write_link_version("dim1/dim1.1", "doc:cats", 1, 0.6)

    # Query by content
    cats_links = node_store.get_link_versions("doc:cats")
    assert len(cats_links) == 2

    paths = {link["node_path"] for link in cats_links}
    assert "dim1" in paths
    assert "dim1/dim1.1" in paths

    dogs_links = node_store.get_link_versions("doc:dogs")
    assert len(dogs_links) == 1
    assert dogs_links[0]["node_path"] == "dim2"


def test_recency_weighting():
    """Test recency weighting calculation."""
    import math
    import time

    lam = 0.05  # /day
    now = time.time()

    # Recent link (0 days old)
    age_days = 0.0
    score = 0.8
    effective = score * math.exp(-lam * age_days)
    assert abs(effective - 0.8) < 0.001

    # Older link (10 days old)
    age_days = 10.0
    effective = score * math.exp(-lam * age_days)
    expected = 0.8 * math.exp(-0.5)  # 0.05 * 10 = 0.5
    assert abs(effective - expected) < 0.001

    # Much older (100 days)
    age_days = 100.0
    effective = score * math.exp(-lam * age_days)
    expected = 0.8 * math.exp(-5.0)
    assert effective < 0.1  # Significantly decayed


def test_link_version_uniqueness(node_store):
    """Test that (node_path, content_id, version) is unique."""
    # Write same version twice - should replace
    node_store.write_link_version("dim1", "doc:test", 1, 0.8, "doc", {"v": 1})
    node_store.write_link_version("dim1", "doc:test", 1, 0.9, "doc", {"v": 2})

    versions = node_store.get_link_versions("doc:test")
    assert len(versions) == 1
    assert versions[0]["score"] == 0.9  # Latest write wins
    assert versions[0]["meta"]["v"] == 2
