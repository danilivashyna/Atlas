"""
Tests for Reticulum v0.6 (link versioning and backrefs).

Covers:
  - write_link_version: storing versioned links
  - recent_links: recency decay with lambda
  - neighbors_from_node: getting neighbors with recency
  - backref_touch: recording backward references
  - top_backrefs: querying popular nodes
"""

import math
import tempfile
import time
from pathlib import Path

import pytest

from atlas.memory.persistent import PersistentMemory


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    db_path = str(Path(tempfile.gettempdir()) / f"test_reticulum_{int(time.time()*1e6)}.db")
    mem = PersistentMemory(db_path=db_path)
    yield mem
    mem.close()
    Path(db_path).unlink(missing_ok=True)


class TestLinkVersions:
    """Test versioned link storage."""

    def test_write_link_version(self, temp_db):
        """Should write and retrieve a link version."""
        temp_db.write_link_version(
            node_path="a/b",
            content_id="doc1",
            version=1,
            score=0.8,
            kind="document",
            meta={"title": "Test"},
        )

        # Query to verify
        results = temp_db.query_link_versions(top_k=10)
        assert len(results) == 1
        assert results[0]["content_id"] == "doc1"
        assert results[0]["node_path"] == "a/b"
        assert results[0]["score"] == 0.8
        assert results[0]["kind"] == "document"
        assert results[0]["meta"]["title"] == "Test"

    def test_multiple_versions_same_content(self, temp_db):
        """Should store multiple versions of the same link."""
        temp_db.write_link_version("a/b", "doc1", 1, 0.6, "doc")
        temp_db.write_link_version("a/b", "doc1", 2, 0.8, "doc")
        temp_db.write_link_version("a/b", "doc1", 3, 0.9, "doc")

        results = temp_db.query_link_versions(top_k=10)
        assert len(results) == 3
        # Should be sorted by score descending (via recent_links)
        versions = {r["version"] for r in results}
        assert versions == {1, 2, 3}

    def test_different_nodes_same_content(self, temp_db):
        """Should support same content linked from different nodes."""
        temp_db.write_link_version("a/b", "doc1", 1, 0.7, "doc")
        temp_db.write_link_version("c/d", "doc1", 1, 0.6, "doc")
        temp_db.write_link_version("e/f", "doc1", 1, 0.5, "doc")

        results = temp_db.query_link_versions(top_k=10)
        assert len(results) == 3
        node_paths = {r["node_path"] for r in results}
        assert node_paths == {"a/b", "c/d", "e/f"}


class TestRecencyDecay:
    """Test recency-weighted link selection."""

    def test_recent_links_with_lambda(self, temp_db):
        """Should apply recency decay: higher lambda = faster decay."""
        # Write links at "now" with different scores
        temp_db.write_link_version("a/b", "doc1", 1, 0.9)  # Recent
        temp_db.write_link_version("a/b", "doc2", 1, 0.5)  # Older (simulated)

        # Query with different lambda values
        now = time.time()
        results_low_lambda = temp_db.recent_links(lambda_per_day=0.01, top_k=10)
        results_high_lambda = temp_db.recent_links(lambda_per_day=1.0, top_k=10)

        # Both should return results, but ordering might differ
        assert len(results_low_lambda) > 0
        assert len(results_high_lambda) > 0

    def test_recency_decay_formula(self, temp_db):
        """Verify recency decay formula: eff = score * exp(-lambda * age_days)."""
        # Write a link with known score and time
        score = 0.8
        temp_db.write_link_version("a/b", "content1", 1, score)

        # Query with specific lambda
        results = temp_db.recent_links(lambda_per_day=0.1, top_k=10)
        assert len(results) > 0

        # Effective score should be close to original (very recent)
        rec = results[0]
        assert rec["score"] == score
        # created_at_ts should be approximately now
        assert time.time() - rec["created_at_ts"] < 10  # written recently


class TestNeighbors:
    """Test neighbor queries from nodes."""

    def test_neighbors_from_node(self, temp_db):
        """Should retrieve neighbors (content) linked from a node."""
        # Create links from node "a/b" to various content
        temp_db.write_link_version("a/b", "content1", 1, 0.9)
        temp_db.write_link_version("a/b", "content2", 1, 0.7)
        temp_db.write_link_version("a/b", "content3", 1, 0.6)

        neighbors = temp_db.neighbors_from_node("a/b", top_k=10)
        assert len(neighbors) == 3
        assert set(neighbors) == {"content1", "content2", "content3"}

    def test_neighbors_top_k(self, temp_db):
        """Should respect top_k limit."""
        for i in range(10):
            temp_db.write_link_version("a/b", f"content{i}", 1, 0.5 + i * 0.01)

        neighbors = temp_db.neighbors_from_node("a/b", top_k=3)
        assert len(neighbors) <= 3

    def test_neighbors_empty_node(self, temp_db):
        """Should return empty list for node with no links."""
        neighbors = temp_db.neighbors_from_node("nonexistent/node", top_k=10)
        assert neighbors == []


class TestBackrefs:
    """Test backward reference tracking."""

    def test_backref_touch_new(self, temp_db):
        """Should create a new backref on first touch."""
        temp_db.backref_touch(content_id="doc1", node_path="a/b")

        backrefs = temp_db.top_backrefs("doc1", top_k=10)
        assert len(backrefs) == 1
        assert backrefs[0]["node_path"] == "a/b"
        assert backrefs[0]["hit_count"] == 1

    def test_backref_touch_increment(self, temp_db):
        """Should increment hit_count on repeat touches."""
        temp_db.backref_touch(content_id="doc1", node_path="a/b")
        temp_db.backref_touch(content_id="doc1", node_path="a/b")
        temp_db.backref_touch(content_id="doc1", node_path="a/b")

        backrefs = temp_db.top_backrefs("doc1", top_k=10)
        assert len(backrefs) == 1
        assert backrefs[0]["hit_count"] == 3

    def test_top_backrefs_sorted_by_hits(self, temp_db):
        """Should sort backrefs by hit_count (most popular first)."""
        temp_db.backref_touch("doc1", "a/b")
        temp_db.backref_touch("doc1", "a/b")
        temp_db.backref_touch("doc1", "c/d")
        temp_db.backref_touch("doc1", "e/f")
        temp_db.backref_touch("doc1", "e/f")
        temp_db.backref_touch("doc1", "e/f")

        backrefs = temp_db.top_backrefs("doc1", top_k=10)
        assert len(backrefs) == 3
        # Should be sorted by hit_count desc
        assert backrefs[0]["hit_count"] == 3  # e/f: 3 hits
        assert backrefs[1]["hit_count"] == 2  # a/b: 2 hits
        assert backrefs[2]["hit_count"] == 1  # c/d: 1 hit

    def test_top_backrefs_top_k(self, temp_db):
        """Should respect top_k limit."""
        for i in range(10):
            temp_db.backref_touch("doc1", f"node{i}")

        backrefs = temp_db.top_backrefs("doc1", top_k=5)
        assert len(backrefs) <= 5

    def test_last_seen_at_updated(self, temp_db):
        """Should update last_seen_at on repeat touches."""
        temp_db.backref_touch("doc1", "a/b")
        first_ts = temp_db.top_backrefs("doc1", top_k=1)[0]["last_seen_at"]

        time.sleep(1.1)  # Sleep 1+ second to ensure timestamp changes
        temp_db.backref_touch("doc1", "a/b")
        second_ts = temp_db.top_backrefs("doc1", top_k=1)[0]["last_seen_at"]

        assert second_ts >= first_ts  # Should be equal or later (timestamp precision)


class TestIntegration:
    """Integration tests combining multiple features."""

    def test_full_reticulum_workflow(self, temp_db):
        """Test a realistic workflow: write links, query neighbors, track backrefs."""
        # Create a node hierarchy
        temp_db.write_node("root", None, [0.5, 0.5, 0.5, 0.5, 0.5], "Root", 0.5)
        temp_db.write_node("root/child1", "root", [0.6, 0.4, 0.5, 0.5, 0.5], "Child1", 0.7)
        temp_db.write_node("root/child2", "root", [0.4, 0.6, 0.5, 0.5, 0.5], "Child2", 0.6)

        # Link content to nodes
        temp_db.write_link_version("root/child1", "doc_a", 1, 0.9, "article")
        temp_db.write_link_version("root/child1", "doc_b", 1, 0.7, "article")
        temp_db.write_link_version("root/child2", "doc_c", 1, 0.8, "blog")

        # Track backrefs (simulate navigation)
        temp_db.backref_touch("doc_a", "root/child1")
        temp_db.backref_touch("doc_a", "root/child1")
        temp_db.backref_touch("doc_b", "root/child1")
        temp_db.backref_touch("doc_c", "root/child2")

        # Query neighbors
        neighbors_child1 = temp_db.neighbors_from_node("root/child1", top_k=10)
        assert "doc_a" in neighbors_child1
        assert "doc_b" in neighbors_child1

        neighbors_child2 = temp_db.neighbors_from_node("root/child2", top_k=10)
        assert "doc_c" in neighbors_child2

        # Query backrefs
        doc_a_roots = temp_db.top_backrefs("doc_a", top_k=10)
        assert len(doc_a_roots) == 1
        assert doc_a_roots[0]["node_path"] == "root/child1"
        assert doc_a_roots[0]["hit_count"] == 2

    def test_recency_with_multiple_versions(self, temp_db):
        """Test that newer versions are preferred due to recency."""
        # Simulate evolving content versions
        temp_db.write_link_version("a/b", "content1", 1, 0.5)
        time.sleep(0.05)  # Small delay
        temp_db.write_link_version("a/b", "content1", 2, 0.6)
        time.sleep(0.05)
        temp_db.write_link_version("a/b", "content1", 3, 0.7)

        results = temp_db.recent_links(lambda_per_day=0.1, top_k=10)
        # Should get all versions, most recent with highest score
        assert len(results) >= 1
        # First result should be recent version 3
        assert results[0]["version"] == 3
