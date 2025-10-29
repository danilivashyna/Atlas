"""
Tests for Deterministic Seeding (Phase B.4)

Coverage:
- SeededRNG reproducibility (same seed → same sequence)
- Deterministic sort with tie-breaking
- Deterministic sampling
- Top-k selection
- Seed hashing and combining
- Reset functionality
"""

from src.orbis_fab.seeding import (
    SeededRNG,
    deterministic_sort,
    deterministic_sample,
    deterministic_top_k,
    hash_to_seed,
    combine_seeds,
)


def test_seeding_rng_reproducibility():
    """Same seed produces same random sequence"""
    rng1 = SeededRNG(seed=42)
    rng2 = SeededRNG(seed=42)
    
    # Generate 10 random values
    seq1 = [rng1.random() for _ in range(10)]
    seq2 = [rng2.random() for _ in range(10)]
    
    assert seq1 == seq2  # Identical sequences


def test_seeding_rng_different_seeds():
    """Different seeds produce different sequences"""
    rng1 = SeededRNG(seed=42)
    rng2 = SeededRNG(seed=43)
    
    seq1 = [rng1.random() for _ in range(10)]
    seq2 = [rng2.random() for _ in range(10)]
    
    assert seq1 != seq2  # Different sequences


def test_seeding_deterministic_sort():
    """Deterministic sort with tie-breaking"""
    items = [
        ("a", 0.8),
        ("b", 0.8),  # Tie with "a"
        ("c", 0.9),
        ("d", 0.7),
    ]
    
    rng1 = SeededRNG(seed=100)
    rng2 = SeededRNG(seed=100)
    
    # Sort twice with same seed
    sorted1 = deterministic_sort(items, rng=rng1)
    sorted2 = deterministic_sort(items, rng=rng2)
    
    assert sorted1 == sorted2  # Identical results
    
    # Check ordering: c (0.9) > a/b (0.8, tie-broken) > d (0.7)
    assert sorted1[0][1] == 0.9  # c first
    assert sorted1[-1][1] == 0.7  # d last
    
    # Tie-breaking: a and b should have deterministic order
    tie_order = [sorted1[1][0], sorted1[2][0]]
    assert set(tie_order) == {"a", "b"}  # Both present


def test_seeding_deterministic_sample():
    """Deterministic sampling without replacement"""
    population = [
        ("item1", 0.9),
        ("item2", 0.8),
        ("item3", 0.7),
        ("item4", 0.6),
        ("item5", 0.5),
    ]
    
    rng1 = SeededRNG(seed=200)
    rng2 = SeededRNG(seed=200)
    
    # Sample 3 items
    sample1 = deterministic_sample(population, k=3, rng=rng1)
    sample2 = deterministic_sample(population, k=3, rng=rng2)
    
    assert sample1 == sample2  # Identical samples
    assert len(sample1) == 3
    
    # All sampled items from population
    for item in sample1:
        assert item in population


def test_seeding_deterministic_sample_k_exceeds():
    """Sample returns all items when k >= population size"""
    population = [("a", 1.0), ("b", 0.5)]
    
    rng = SeededRNG(seed=300)
    sample = deterministic_sample(population, k=10, rng=rng)
    
    assert len(sample) == 2  # Only 2 items available
    assert set(sample) == set(population)


def test_seeding_deterministic_top_k():
    """Top-k selection with tie-breaking"""
    items = [
        ("a", 0.9),
        ("b", 0.8),
        ("c", 0.8),  # Tie with b
        ("d", 0.7),
        ("e", 0.6),
    ]
    
    rng1 = SeededRNG(seed=400)
    rng2 = SeededRNG(seed=400)
    
    # Select top 3
    top_k1 = deterministic_top_k(items, k=3, rng=rng1)
    top_k2 = deterministic_top_k(items, k=3, rng=rng2)
    
    assert top_k1 == top_k2  # Identical results
    assert len(top_k1) == 3
    
    # Should include: a (0.9), b/c (0.8, one of them), and possibly d (0.7)
    assert top_k1[0][1] == 0.9  # a first
    
    # Second and third should be 0.8 (b or c) and 0.7 or 0.8
    scores = [item[1] for item in top_k1]
    assert scores[0] >= scores[1] >= scores[2]  # Descending order


def test_seeding_rng_reset():
    """Reset RNG reproduces same sequence"""
    rng = SeededRNG(seed=500)
    
    # Generate sequence
    seq1 = [rng.random() for _ in range(5)]
    
    # Reset and regenerate
    rng.reset()
    seq2 = [rng.random() for _ in range(5)]
    
    assert seq1 == seq2  # Identical after reset


def test_seeding_hash_to_seed():
    """Hash text to deterministic seed"""
    text1 = "window-abc-123"
    text2 = "window-abc-123"
    text3 = "window-xyz-456"
    
    seed1 = hash_to_seed(text1)
    seed2 = hash_to_seed(text2)
    seed3 = hash_to_seed(text3)
    
    assert seed1 == seed2  # Same text → same seed
    assert seed1 != seed3  # Different text → different seed
    
    # Seed should be non-negative integer
    assert isinstance(seed1, int)
    assert seed1 >= 0


def test_seeding_combine_seeds():
    """Combine multiple seeds deterministically"""
    seed1 = 100
    seed2 = 200
    seed3 = 300
    
    # Combine in same order
    combined1 = combine_seeds(seed1, seed2, seed3)
    combined2 = combine_seeds(seed1, seed2, seed3)
    
    assert combined1 == combined2  # Deterministic
    
    # Different order produces different result (XOR not commutative with order in mind)
    # Actually XOR is commutative, so order doesn't matter - adjust test
    combined3 = combine_seeds(seed3, seed2, seed1)
    assert combined1 == combined3  # XOR is commutative


def test_seeding_rng_methods():
    """Test all RNG methods work correctly"""
    rng = SeededRNG(seed=600)
    
    # random()
    r = rng.random()
    assert 0.0 <= r < 1.0
    
    # randint()
    i = rng.randint(1, 10)
    assert 1 <= i <= 10
    
    # choice()
    items = ["a", "b", "c"]
    c = rng.choice(items)
    assert c in items
    
    # shuffle()
    seq = [1, 2, 3, 4, 5]
    shuffled = rng.shuffle(seq)
    assert len(shuffled) == len(seq)
    assert set(shuffled) == set(seq)
    assert seq == [1, 2, 3, 4, 5]  # Original unchanged
    
    # sample()
    population = [10, 20, 30, 40, 50]
    sample = rng.sample(population, k=3)
    assert len(sample) == 3
    assert all(item in population for item in sample)


def test_seeding_realistic_scenario():
    """Realistic scenario: tie-breaking in node selection"""
    # 10 candidates with some tied scores
    candidates = [
        ("node1", 0.95),
        ("node2", 0.90),
        ("node3", 0.90),  # Tie with node2
        ("node4", 0.90),  # Tie with node2, node3
        ("node5", 0.85),
        ("node6", 0.85),  # Tie with node5
        ("node7", 0.80),
        ("node8", 0.75),
        ("node9", 0.70),
        ("node10", 0.65),
    ]
    
    # Use window ID as seed
    window_id = "stream-window-42"
    seed = hash_to_seed(window_id)
    rng = SeededRNG(seed=seed)
    
    # Select top 5 deterministically
    top5 = deterministic_top_k(candidates, k=5, rng=rng)
    
    assert len(top5) == 5
    
    # Should include node1 (0.95) and 3 from tied 0.90 group
    assert top5[0][0] == "node1"
    assert top5[0][1] == 0.95
    
    # Next 3 should be from 0.90 group (deterministically chosen)
    scores_0_90 = [item for item in top5[1:4] if item[1] == 0.90]
    assert len(scores_0_90) == 3
    
    # Re-run with same window ID → same results
    rng2 = SeededRNG(seed=hash_to_seed(window_id))
    top5_again = deterministic_top_k(candidates, k=5, rng=rng2)
    assert top5 == top5_again
