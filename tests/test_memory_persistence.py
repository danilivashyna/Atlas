"""Tests for persistent memory backends."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from atlas.memory.persistent import PersistentMemory


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        yield db_path


@pytest.fixture
def temp_jsonl():
    """Create temporary JSONL file for bulk loading."""
    with tempfile.TemporaryDirectory() as tmpdir:
        jsonl_path = os.path.join(tmpdir, "test.jsonl")
        records = [
            {"id": "doc1", "vector": [0.1, 0.0, 0.8, 0.0, 0.2], "meta": {"title": "doc1"}},
            {
                "id": "doc2",
                "vector": [0.2, 0.3, 0.4, 0.1, 0.0],
                "meta": {"title": "doc2", "source": "test"},
            },
            {"id": "doc3", "vector": [0.0, 0.0, 0.0, 0.5, 0.5]},  # no meta
        ]
        with open(jsonl_path, "w") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")
        yield jsonl_path


def test_flush_and_stats_sqlite(temp_db):
    """Test that flush() empties memory and stats returns zero count."""
    mem = PersistentMemory(db_path=temp_db)

    # Write some records
    mem.write("id1", [0.1, 0.2, 0.3, 0.4, 0.5], meta={"key": "value"})
    mem.write("id2", [0.5, 0.4, 0.3, 0.2, 0.1])

    stats = mem.stats()
    assert stats["backend"] == "sqlite"
    assert stats["count"] == 2

    # Flush all records
    removed = mem.flush()
    assert removed == 2

    # Verify empty
    stats = mem.stats()
    assert stats["count"] == 0

    mem.close()


def test_write_query_sqlite(temp_db):
    """Test writing and querying vectors."""
    mem = PersistentMemory(db_path=temp_db)

    # Write a vector
    vec = [0.1, 0.0, 0.8, 0.0, 0.2]
    meta = {"title": "test doc"}
    mem.write("doc1", vec, meta=meta)

    # Query with same vector
    results = mem.query(vec, top_k=1)
    assert len(results) == 1
    assert results[0]["id"] == "doc1"
    assert results[0]["score"] == pytest.approx(1.0, abs=0.01)
    assert results[0]["meta"] == meta

    mem.close()


def test_load_jsonl(temp_db, temp_jsonl):
    """Test bulk loading from JSONL file."""
    mem = PersistentMemory(db_path=temp_db)

    # Load records
    loaded = mem.load(temp_jsonl)
    assert loaded == 3

    # Verify count
    stats = mem.stats()
    assert stats["count"] == 3

    # Query should find all
    results = mem.query([0.0, 0.0, 1.0, 0.0, 0.0], top_k=5)
    assert len(results) == 3  # All records returned

    mem.close()


def test_cosine_similarity(temp_db):
    """Test cosine similarity computation."""
    mem = PersistentMemory(db_path=temp_db)

    # Write orthogonal vectors
    mem.write("v1", [1.0, 0.0, 0.0, 0.0, 0.0])
    mem.write("v2", [0.0, 1.0, 0.0, 0.0, 0.0])
    mem.write("v3", [1.0, 1.0, 0.0, 0.0, 0.0])

    # Query with v1 direction
    results = mem.query([1.0, 0.0, 0.0, 0.0, 0.0], top_k=3)
    assert results[0]["id"] == "v1"
    assert results[0]["score"] == pytest.approx(1.0, abs=0.01)
    # v3 should be next (shared dimension)
    assert results[1]["id"] in ["v3", "v2"]

    mem.close()


def test_empty_query(temp_db):
    """Test querying empty database."""
    mem = PersistentMemory(db_path=temp_db)

    results = mem.query([0.0, 0.0, 0.0, 0.0, 0.0], top_k=5)
    assert results == []

    mem.close()
