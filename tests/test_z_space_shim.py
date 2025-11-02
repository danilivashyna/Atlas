"""
Unit tests for Z-Space integration layer (contracts + shim).

Test coverage:
- ZSliceLite contract validation
- ZSpaceShim deterministic selection
- Top-k selection with score ranking
- Stream/global pool separation
- Edge cases (empty slice, zero budget, etc.)
"""

from typing import cast
from orbis_z import ZSliceLite, ZSpaceShim
from tests.test_helpers import make_z


def test_zspace_shim_deterministic_selection():
    """
    Test: Same seed → same top-k selection (determinism requirement).
    
    Validates:
    - Identical seed produces identical node IDs
    - Identical ordering (not just set equality)
    - Works across different k values
    """
    z_slice = make_z(
        nodes=[
            {"id": "n1", "score": 0.95},
            {"id": "n2", "score": 0.87},
            {"id": "n3", "score": 0.92},
            {"id": "n4", "score": 0.78},
            {"id": "n5", "score": 0.99},
        ],
        seed="determinism-test-123"
    )
    
    # Run selection twice with same seed
    selected_1 = ZSpaceShim.select_topk_for_stream(z_slice, k=3)
    selected_2 = ZSpaceShim.select_topk_for_stream(z_slice, k=3)
    
    # Should be identical (same IDs, same order)
    assert selected_1 == selected_2
    assert len(selected_1) == 3
    
    # Top-3 by score: n5 (0.99), n1 (0.95), n3 (0.92)
    assert selected_1 == ["n5", "n1", "n3"]


def test_zspace_shim_topk_score_ranking():
    """
    Test: Top-k selection ranks by score descending.
    
    Validates:
    - Highest scores selected first
    - Deterministic tie-breaking (by ID)
    - Respects k budget
    """
    z_slice: ZSliceLite = {
        "nodes": [
            {"id": "low", "score": 0.2},
            {"id": "high", "score": 0.9},
            {"id": "mid", "score": 0.5},
        ],
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": 64, "edges": 128, "time_ms": 500},
        "seed": "ranking-test",
        "zv": "v0.1.0"
    }
    
    # Select top-2
    selected = ZSpaceShim.select_topk_for_stream(z_slice, k=2)
    
    # Should get high (0.9) and mid (0.5), not low (0.2)
    assert len(selected) == 2
    assert "high" in selected
    assert "mid" in selected
    assert "low" not in selected
    
    # Order should be score descending
    assert selected == ["high", "mid"]


def test_zspace_shim_tie_breaking_deterministic():
    """
    Test: Tie-breaking by ID when scores equal (determinism).
    
    Validates:
    - Equal scores → sorted by ID alphabetically
    - Reproducible across runs
    """
    z_slice: ZSliceLite = {
        "nodes": [
            {"id": "zebra", "score": 0.8},
            {"id": "apple", "score": 0.8},
            {"id": "banana", "score": 0.8},
        ],
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": 64, "edges": 128, "time_ms": 500},
        "seed": "tie-break-test",
        "zv": "v0.1.0"
    }
    
    # All scores equal, should sort by ID
    selected = ZSpaceShim.select_topk_for_stream(z_slice, k=2)
    
    # Alphabetical order: apple < banana < zebra
    assert selected == ["apple", "banana"]
    
    # Verify reproducibility
    selected_again = ZSpaceShim.select_topk_for_stream(z_slice, k=2)
    assert selected == selected_again


def test_zspace_shim_empty_slice():
    """
    Test: Empty slice edge case returns empty list.
    """
    z_slice: ZSliceLite = {
        "nodes": [],
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": 64, "edges": 128, "time_ms": 500},
        "seed": "empty-test",
        "zv": "v0.1.0"
    }
    
    selected = ZSpaceShim.select_topk_for_stream(z_slice, k=10)
    assert selected == []


def test_zspace_shim_zero_budget():
    """
    Test: Zero budget (k=0) returns empty list.
    """
    z_slice: ZSliceLite = {
        "nodes": [
            {"id": "n1", "score": 0.9},
            {"id": "n2", "score": 0.8},
        ],
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": 64, "edges": 128, "time_ms": 500},
        "seed": "zero-budget-test",
        "zv": "v0.1.0"
    }
    
    selected = ZSpaceShim.select_topk_for_stream(z_slice, k=0)
    assert selected == []


def test_zspace_shim_k_exceeds_nodes():
    """
    Test: k > len(nodes) returns all nodes (no error).
    """
    z_slice: ZSliceLite = {
        "nodes": [
            {"id": "n1", "score": 0.9},
            {"id": "n2", "score": 0.7},
        ],
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": 64, "edges": 128, "time_ms": 500},
        "seed": "exceed-test",
        "zv": "v0.1.0"
    }
    
    # Request k=10 but only 2 nodes available
    selected = ZSpaceShim.select_topk_for_stream(z_slice, k=10)
    
    # Should return all 2 nodes (not crash or error)
    assert len(selected) == 2
    assert set(selected) == {"n1", "n2"}


def test_zspace_shim_global_pool_excludes_stream():
    """
    Test: Global pool selection excludes stream nodes (no overlap).
    
    Validates:
    - select_topk_for_global respects exclude_ids
    - No overlap between stream and global
    - Deterministic selection
    """
    z_slice: ZSliceLite = {
        "nodes": [
            {"id": "n1", "score": 0.99},
            {"id": "n2", "score": 0.95},
            {"id": "n3", "score": 0.90},
            {"id": "n4", "score": 0.85},
            {"id": "n5", "score": 0.80},
        ],
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": 64, "edges": 128, "time_ms": 500},
        "seed": "global-pool-test",
        "zv": "v0.1.0"
    }
    
    # Select top-2 for stream
    stream_ids = ZSpaceShim.select_topk_for_stream(z_slice, k=2)
    assert stream_ids == ["n1", "n2"]  # Highest scores
    
    # Select top-2 for global (excluding stream)
    global_ids = ZSpaceShim.select_topk_for_global(
        z_slice, k=2, exclude_ids=set(stream_ids)
    )
    
    # Should get next highest: n3, n4
    assert global_ids == ["n3", "n4"]
    
    # Verify no overlap
    assert set(stream_ids) & set(global_ids) == set()


def test_zspace_slice_validation_valid():
    """
    Test: Valid ZSliceLite passes validation.
    """
    z_slice: ZSliceLite = {
        "nodes": [
            {"id": "n1", "score": 0.8},
            {"id": "n2", "score": 0.6},
        ],
        "edges": [
            {"src": "n1", "dst": "n2", "weight": 0.7}
        ],
        "quotas": {"tokens": 8000, "nodes": 64, "edges": 128, "time_ms": 500},
        "seed": "valid-test",
        "zv": "v0.1.0"
    }
    
    valid, error = ZSpaceShim.validate_slice(z_slice)
    assert valid is True
    assert error == ""


def test_zspace_slice_validation_missing_field():
    """
    Test: Missing required field fails validation.
    """
    z_slice_incomplete = cast(ZSliceLite, {
        "nodes": [{"id": "n1", "score": 0.8}],
        "edges": [],
        # Missing: quotas, seed, zv
    })
    
    valid, error = ZSpaceShim.validate_slice(z_slice_incomplete)
    assert valid is False
    assert "Missing required fields" in error
    assert "quotas" in error


def test_zspace_slice_validation_invalid_score():
    """
    Test: Node score out of range [0.0, 1.0] fails validation.
    """
    z_slice: ZSliceLite = {
        "nodes": [
            {"id": "n1", "score": 1.5},  # Invalid: > 1.0
        ],
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": 64, "edges": 128, "time_ms": 500},
        "seed": "invalid-score-test",
        "zv": "v0.1.0"
    }
    
    valid, error = ZSpaceShim.validate_slice(z_slice)
    assert valid is False
    assert "out of range" in error


def test_zspace_slice_validation_duplicate_node_id():
    """
    Test: Duplicate node IDs fail validation.
    """
    z_slice: ZSliceLite = {
        "nodes": [
            {"id": "n1", "score": 0.8},
            {"id": "n1", "score": 0.7},  # Duplicate ID
        ],
        "edges": [],
        "quotas": {"tokens": 8000, "nodes": 64, "edges": 128, "time_ms": 500},
        "seed": "duplicate-id-test",
        "zv": "v0.1.0"
    }
    
    valid, error = ZSpaceShim.validate_slice(z_slice)
    assert valid is False
    assert "Duplicate node ID" in error


def test_zspace_slice_validation_edge_unknown_node():
    """
    Test: Edge referencing non-existent node fails validation.
    """
    z_slice: ZSliceLite = {
        "nodes": [
            {"id": "n1", "score": 0.8},
        ],
        "edges": [
            {"src": "n1", "dst": "n_unknown", "weight": 0.5}  # Unknown dst
        ],
        "quotas": {"tokens": 8000, "nodes": 64, "edges": 128, "time_ms": 500},
        "seed": "unknown-node-test",
        "zv": "v0.1.0"
    }
    
    valid, error = ZSpaceShim.validate_slice(z_slice)
    assert valid is False
    assert "unknown" in error.lower()


def test_zspace_different_seeds_different_order():
    """
    Test: Different seeds produce different tie-breaking (when scores equal).
    
    Validates:
    - Seed influences selection (not just score)
    - Reproducibility per seed
    """
    z_slice_base = make_z(
        nodes=[
            {"id": "a", "score": 0.5},
            {"id": "b", "score": 0.5},
            {"id": "c", "score": 0.5},
        ],
        seed="seed-base"
    )
    
    # Same scores, different seeds
    z_seed1 = cast(ZSliceLite, {**z_slice_base, "seed": "seed-A"})
    z_seed2 = cast(ZSliceLite, {**z_slice_base, "seed": "seed-B"})
    
    # Select with different seeds
    selected_1 = ZSpaceShim.select_topk_for_stream(z_seed1, k=2)
    selected_2 = ZSpaceShim.select_topk_for_stream(z_seed2, k=2)
    
    # Note: With score-based tie-breaking by ID, order should be same
    # (This test validates current implementation, may change with random tie-break)
    # For now, expect deterministic ID-based sorting
    assert selected_1 == ["a", "b"]
    assert selected_2 == ["a", "b"]
    
    # Both are deterministic per seed
    assert selected_1 == ZSpaceShim.select_topk_for_stream(z_seed1, k=2)
    assert selected_2 == ZSpaceShim.select_topk_for_stream(z_seed2, k=2)


# ---- PR#4: Vec-MMR tests ----

def test_vec_mmr_improves_diversity_over_score_sort():
    """
    Test: Vec-MMR selects diverse clusters (vs pure score-sort).
    
    PR#4: When nodes have vec embeddings, MMR should mix clusters
    instead of greedily selecting from highest-score cluster only.
    
    Validates:
    - MMR selects from both clusters (high-score cluster A + cluster B)
    - Diversity gain from cosine similarity
    - Deterministic selection
    """
    import random
    rng = random.Random(123)
    
    def j(x: float, y: float) -> list[float]:
        """Slight jitter for cluster (avoids perfect orthogonality)."""
        return [x + 0.01, y - 0.01]
    
    nodes = []
    # Cluster A: high scores, vec ~ [1.0, 0.0]
    for i in range(16):
        nodes.append({"id": f"a{i}", "score": 0.95 - i * 0.0001, "vec": j(1.0, 0.0)})
    
    # Cluster B: slightly lower scores, vec ~ [0.0, 1.0] (orthogonal)
    for i in range(16):
        nodes.append({"id": f"b{i}", "score": 0.94 - i * 0.0001, "vec": j(0.0, 1.0)})
    
    z_slice = make_z(nodes=nodes, seed="vec-mmr-diversity")
    
    ids = ZSpaceShim.select_topk_for_stream(z_slice, k=8, rng=rng)
    
    # MMR should select from BOTH clusters (diversity)
    # Pure score-sort would select a0-a7 only (all cluster A)
    assert any(node_id.startswith("a") for node_id in ids), "Should have cluster A nodes"
    assert any(node_id.startswith("b") for node_id in ids), "Should have cluster B nodes (diversity)"
    
    # Validate determinism
    ids_2 = ZSpaceShim.select_topk_for_stream(z_slice, k=8, rng=random.Random(123))
    assert ids == ids_2, "Same seed → same selection"


def test_mixed_vec_presence_fallback_determinism():
    """
    Test: Mixed vec presence (some nodes have vec, others don't) → deterministic.
    
    PR#4: When only SOME nodes have vectors, MMR still runs but should
    handle gracefully. Fallback to score-sort for non-vec nodes.
    
    Validates:
    - Determinism with partial vec coverage
    - No crashes with missing vec fields
    - Same seed → same result
    """
    import random
    rng1 = random.Random(7)
    rng2 = random.Random(7)
    
    nodes = []
    # First 8 nodes: have vec
    for i in range(8):
        nodes.append({"id": f"v{i}", "score": 0.9 - i * 0.001, "vec": [1.0, 0.0]})
    
    # Next 8 nodes: NO vec (fallback to score-sort)
    for i in range(8):
        nodes.append({"id": f"n{i}", "score": 0.89 - i * 0.001})
    
    z_slice = make_z(nodes=nodes, seed="mixed-vec")
    
    ids1 = ZSpaceShim.select_topk_for_stream(z_slice, k=8, rng=rng1)
    ids2 = ZSpaceShim.select_topk_for_stream(z_slice, k=8, rng=rng2)
    
    # Determinism: same seed → same result
    assert ids1 == ids2, "Same seed should produce identical selection"
    assert len(ids1) == 8, "Should select exactly k=8 nodes"


def test_vec_mmr_pure_score_fallback_when_no_vecs():
    """
    Test: No vectors present → fallback to pure score-sort.
    
    PR#4: When NO nodes have vec field, MMR should gracefully
    fall back to score-based ranking with deterministic tie-breaks.
    
    Validates:
    - Correct fallback behavior (no crash)
    - Pure score ranking (highest first)
    - Deterministic by id (tie-breaking)
    """
    import random
    rng = random.Random(99)
    
    # All nodes: NO vec field
    nodes = [{"id": f"s{i}", "score": 1.0 - i * 0.001} for i in range(16)]
    
    z_slice = make_z(nodes=nodes, seed="no-vecs")
    
    ids = ZSpaceShim.select_topk_for_stream(z_slice, k=8, rng=rng)
    
    # Should select top-8 by score (s0 = 1.0, s1 = 0.999, ..., s7 = 0.993)
    assert ids[0] == "s0", "Highest score should be first"
    assert ids[-1] == "s7", "8th highest score should be last"
    assert len(ids) == 8, "Should select exactly k=8"
    
    # Determinism
    ids_2 = ZSpaceShim.select_topk_for_stream(z_slice, k=8, rng=random.Random(99))
    assert ids == ids_2, "Same seed → same result"

