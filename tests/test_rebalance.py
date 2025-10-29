"""
Tests for MMR-like Rebalance (Phase B.3)

Coverage:
- Cosine distance computation
- Coverage penalty (close nodes get penalized)
- MMR score rebalancing (λ * relevance - (1-λ) * penalty)
- Batch rebalancing (greedy selection)
- Statistics tracking
- Edge cases (empty existing nodes, dimension mismatch)
"""

from src.orbis_fab.rebalance import (
    RebalanceConfig,
    MMRRebalancer,
)


def test_rebalance_cosine_distance():
    """Cosine distance computation for normalized vectors"""
    rebalancer = MMRRebalancer()
    
    # Identical vectors: distance = 0.0
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]
    assert rebalancer.cosine_distance(vec1, vec2) == 0.0
    
    # Orthogonal vectors: distance = 1.0 (similarity = 0.0)
    vec3 = [1.0, 0.0, 0.0]
    vec4 = [0.0, 1.0, 0.0]
    dist = rebalancer.cosine_distance(vec3, vec4)
    assert abs(dist - 1.0) < 1e-6
    
    # Opposite vectors: distance ≈ 2.0 (similarity = -1.0)
    vec5 = [1.0, 0.0, 0.0]
    vec6 = [-1.0, 0.0, 0.0]
    dist = rebalancer.cosine_distance(vec5, vec6)
    assert abs(dist - 2.0) < 1e-6


def test_rebalance_coverage_penalty_empty():
    """No penalty when no existing nodes"""
    config = RebalanceConfig(distance_threshold=0.3)
    rebalancer = MMRRebalancer(config=config)
    
    candidate = [0.5, 0.5, 0.0]
    existing_nodes = []
    
    penalty = rebalancer.compute_coverage_penalty(candidate, existing_nodes)
    assert penalty == 0.0


def test_rebalance_coverage_penalty_close():
    """Close nodes get penalized"""
    config = RebalanceConfig(
        distance_threshold=0.3,
        min_distance_boost=0.1,
        max_penalty=0.5
    )
    rebalancer = MMRRebalancer(config=config)
    
    # Candidate very close to existing node (distance ≈ 0.0)
    candidate = [1.0, 0.0, 0.0]
    existing_nodes = [([0.99, 0.1, 0.0], 0.8)]  # Nearly identical (after normalization)
    
    penalty = rebalancer.compute_coverage_penalty(candidate, existing_nodes)
    # Distance ≈ 0.0 < threshold (0.3) → penalty should be close to max_penalty
    assert penalty > 0.1  # At least min_distance_boost
    assert penalty <= 0.5  # Capped at max_penalty


def test_rebalance_coverage_penalty_far():
    """Distant nodes get no penalty"""
    config = RebalanceConfig(distance_threshold=0.3)
    rebalancer = MMRRebalancer(config=config)
    
    # Candidate far from existing node (distance > threshold)
    candidate = [1.0, 0.0, 0.0]
    existing_nodes = [([0.0, 1.0, 0.0], 0.8)]  # Orthogonal (distance = 1.0)
    
    penalty = rebalancer.compute_coverage_penalty(candidate, existing_nodes)
    assert penalty == 0.0  # Distance (1.0) > threshold (0.3)


def test_rebalance_score_pure_relevance():
    """λ=1.0: pure relevance (no diversity penalty)"""
    config = RebalanceConfig(lambda_weight=1.0)
    rebalancer = MMRRebalancer(config=config)
    
    candidate_score = 0.8
    candidate_vector = [1.0, 0.0, 0.0]
    existing_nodes = [([0.99, 0.1, 0.0], 0.9)]  # Very close
    
    rebalanced = rebalancer.rebalance_score(candidate_score, candidate_vector, existing_nodes)
    # λ=1.0 → score_new = 1.0 * 0.8 - 0.0 * penalty = 0.8
    assert abs(rebalanced - 0.8) < 1e-6


def test_rebalance_score_pure_diversity():
    """λ=0.0: pure diversity (max penalty)"""
    config = RebalanceConfig(
        lambda_weight=0.0,
        distance_threshold=0.3,
        max_penalty=0.5
    )
    rebalancer = MMRRebalancer(config=config)
    
    candidate_score = 0.8
    candidate_vector = [1.0, 0.0, 0.0]
    existing_nodes = [([1.0, 0.0, 0.0], 0.9)]  # Identical (distance = 0.0)
    
    rebalanced = rebalancer.rebalance_score(candidate_score, candidate_vector, existing_nodes)
    # λ=0.0 → score_new = 0.0 * 0.8 - 1.0 * penalty
    # penalty should be max_penalty (0.5) since distance = 0.0 < threshold
    # score_new = 0.0 - 0.5 = -0.5 → clamped to 0.0
    assert rebalanced == 0.0


def test_rebalance_score_balanced():
    """λ=0.5: balanced relevance and diversity"""
    config = RebalanceConfig(
        lambda_weight=0.5,
        distance_threshold=0.5,
        min_distance_boost=0.1,
        max_penalty=0.4
    )
    rebalancer = MMRRebalancer(config=config)
    
    candidate_score = 0.8
    candidate_vector = [1.0, 0.0, 0.0]
    existing_nodes = [([0.9, 0.0, 0.0], 0.7)]  # Close but not identical
    
    rebalanced = rebalancer.rebalance_score(candidate_score, candidate_vector, existing_nodes)
    # Should be less than original score due to penalty
    assert rebalanced < candidate_score
    assert rebalanced > 0.0  # But not zero (balanced)


def test_rebalance_batch_greedy_selection():
    """Greedy batch selection picks diverse nodes"""
    config = RebalanceConfig(
        lambda_weight=0.5,
        distance_threshold=0.3,
        max_penalty=0.5
    )
    rebalancer = MMRRebalancer(config=config)
    
    # Three candidates: two close, one far
    candidates = [
        ([1.0, 0.0, 0.0], 0.9),   # High score, will be picked first
        ([0.99, 0.1, 0.0], 0.85), # Close to first, will be penalized
        ([0.0, 1.0, 0.0], 0.8),   # Orthogonal, should be picked second
    ]
    
    existing_nodes = []
    results = rebalancer.rebalance_batch(candidates, existing_nodes, top_k=2)
    
    # Should pick candidates 0 and 2 (diverse pair)
    assert len(results) == 2
    _, base1, _ = results[0]
    _, base2, _ = results[1]
    
    # First pick: highest base score (0.9)
    assert base1 == 0.9
    
    # Second pick: should be orthogonal candidate (0.8), not close one (0.85)
    # because close one gets penalized
    assert base2 == 0.8


def test_rebalance_stats_tracking():
    """Statistics are tracked correctly"""
    config = RebalanceConfig(lambda_weight=0.5)
    rebalancer = MMRRebalancer(config=config)
    
    # Evaluate 3 candidates
    candidates = [
        ([1.0, 0.0, 0.0], 0.9),
        ([0.9, 0.1, 0.0], 0.8),
        ([0.0, 1.0, 0.0], 0.7),
    ]
    
    existing_nodes = []
    for vec, score in candidates:
        rebalancer.rebalance_score(score, vec, existing_nodes)
        existing_nodes.append((vec, score))
    
    stats = rebalancer.get_stats()
    assert stats.nodes_evaluated == 3
    # First candidate: no existing nodes, no penalty
    # Second candidate: close to first, penalized
    # Third candidate: far from first/second, no penalty (or small)
    assert stats.nodes_penalized >= 1  # At least second candidate


def test_rebalance_reset_stats():
    """Reset statistics returns old stats"""
    rebalancer = MMRRebalancer()
    
    # Evaluate some nodes
    rebalancer.rebalance_score(0.8, [1.0, 0.0], [([0.9, 0.1], 0.7)])
    
    old_stats = rebalancer.reset_stats()
    assert old_stats.nodes_evaluated == 1
    
    # New stats should be reset
    new_stats = rebalancer.get_stats()
    assert new_stats.nodes_evaluated == 0


def test_rebalance_dimension_mismatch():
    """Dimension mismatch raises ValueError"""
    rebalancer = MMRRebalancer()
    
    vec1 = [1.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]  # Different dimension
    
    try:
        rebalancer.cosine_distance(vec1, vec2)
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "dimension mismatch" in str(e).lower()


def test_rebalance_realistic_scenario():
    """Realistic scenario: rebalance 5 candidates with 2 existing nodes"""
    config = RebalanceConfig(
        lambda_weight=0.6,  # Favor relevance slightly
        distance_threshold=0.4,
        max_penalty=0.3
    )
    rebalancer = MMRRebalancer(config=config)
    
    # 2 existing nodes
    existing = [
        ([1.0, 0.0, 0.0], 0.9),
        ([0.0, 1.0, 0.0], 0.85),
    ]
    
    # 5 candidates: mix of close and far
    candidates = [
        ([0.95, 0.05, 0.0], 0.88),  # Close to existing[0]
        ([0.0, 0.95, 0.05], 0.87),  # Close to existing[1]
        ([0.0, 0.0, 1.0], 0.80),    # Far from both (orthogonal)
        ([0.7, 0.7, 0.0], 0.75),    # Moderate distance
        ([0.5, 0.5, 0.5], 0.70),    # Moderate distance
    ]
    
    # Select top 3
    results = rebalancer.rebalance_batch(candidates, existing, top_k=3)
    
    assert len(results) == 3
    
    # First pick should likely be candidate 2 or 0 (high base score)
    # But if 0/1 are too close to existing, 2 (orthogonal) should win
    base_scores = [r[1] for r in results]
    rebalanced_scores = [r[2] for r in results]
    
    # Rebalanced scores should differ from base due to penalties
    assert rebalanced_scores != base_scores
    
    # Stats should show penalties applied
    stats = rebalancer.get_stats()
    assert stats.nodes_evaluated > 0
    assert stats.nodes_penalized > 0  # At least some candidates penalized
