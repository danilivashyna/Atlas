"""
Tests for v0.5.1: Incremental ANN updates + Query embed cache
"""

import os

import pytest

from atlas.memory import get_node_store
from atlas.router.ann_index import (
    TTLCacheLRU,
    get_ann_index,
    get_query_cache,
    _reset_ann_singletons,
)


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset ANN/cache singletons before each test."""
    _reset_ann_singletons()
    yield
    _reset_ann_singletons()


@pytest.fixture
def node_store():
    """Fixture with test nodes."""
    store = get_node_store()
    # Clear existing
    store.flush_nodes()
    # Add test nodes
    store.write_node("dim1", None, [0.1, 0.2, 0.3, 0.4, 0.5], "Dim1", 1.0)
    store.write_node("dim1/dim1.1", "dim1", [0.2, 0.3, 0.4, 0.5, 0.6], "Dim1.1", 0.8)
    store.write_node("dim2", None, [0.5, 0.4, 0.3, 0.2, 0.1], "Dim2", 1.0)
    yield store
    store.flush_nodes()


def test_ttl_cache_lru():
    """Test TTLCacheLRU basic functionality."""
    cache = TTLCacheLRU(capacity=2, ttl=1.0)

    # Set and get
    cache.set("key1", "val1")
    assert cache.get("key1") == "val1"

    # LRU eviction
    cache.set("key2", "val2")
    cache.set("key3", "val3")  # Should evict key1
    assert cache.get("key1") is None
    assert cache.get("key2") == "val2"
    assert cache.get("key3") == "val3"


def test_query_cache():
    """Test QueryEmbedCache with hits/misses."""
    cache = get_query_cache(size=10, ttl=60)

    def compute():
        return [0.1, 0.2, 0.3, 0.4, 0.5]

    # First call - miss
    vec1, hit1 = cache.get_or_compute("test", compute)
    assert not hit1
    assert vec1 == [0.1, 0.2, 0.3, 0.4, 0.5]
    assert cache.misses >= 1
    assert cache.hits == 0

    # Second call - hit
    vec2, hit2 = cache.get_or_compute("test", compute)
    assert hit2
    assert vec2 == vec1
    assert cache.hits == 1


def test_ann_incremental_add(node_store):
    """Test incremental ANN add_nodes."""
    ann = get_ann_index("inproc")
    ann.rebuild([])  # Start empty

    # Add nodes
    items = [("dim1", [0.1, 0.2, 0.3, 0.4, 0.5]), ("dim2", [0.5, 0.4, 0.3, 0.2, 0.1])]
    added = ann.add_nodes(items)
    assert added == 2
    assert ann.size() == 2

    # Query should work
    results = ann.search([0.1, 0.2, 0.3, 0.4, 0.5], 1)
    assert len(results) == 1
    assert results[0][0] == "dim1"


def test_ann_incremental_remove(node_store):
    """Test incremental ANN remove_nodes."""
    ann = get_ann_index("inproc")
    ann.rebuild([("dim1", [0.1, 0.2, 0.3, 0.4, 0.5]), ("dim2", [0.5, 0.4, 0.3, 0.2, 0.1])])
    assert ann.size() == 2

    # Remove one
    removed = ann.remove_nodes(["dim1"])
    assert removed == 1
    assert ann.size() == 1

    # Query should not return removed
    results = ann.search([0.1, 0.2, 0.3, 0.4, 0.5], 1)
    assert len(results) == 0 or results[0][0] != "dim1"


def test_ann_sync_with_db(node_store):
    """Test ANN sync with database."""
    ann = get_ann_index("inproc")
    ann.rebuild([])  # Start empty

    # Sync should populate from DB
    items = [(n["path"], n["vec5"]) for n in node_store.get_all_nodes()]
    size = ann.rebuild(items)
    assert size == 3  # dim1, dim1.1, dim2

    # Add new node to DB
    node_store.write_node("dim3", None, [0.9, 0.8, 0.7, 0.6, 0.5], "Dim3", 1.0)

    # Sync again
    items = [(n["path"], n["vec5"]) for n in node_store.get_all_nodes()]
    size = ann.rebuild(items)
    assert size == 4
