"""
Deterministic Seeding (Phase B.4)

Provides deterministic tie-breaking and sampling for FAB operations:
- Uses z_slice.seed (from window metadata) for reproducibility
- Deterministic sorting for nodes with equal scores
- Deterministic sampling when selecting k from n candidates

Use cases:
- Reproducible tests (same seed → same results)
- Deterministic tie-breaking (avoid flapping between equal-score nodes)
- Stable node selection across runs

Usage:
    # Create seeded RNG
    rng = SeededRNG(seed=42)

    # Deterministic tie-breaking
    nodes = [(vec1, 0.8), (vec2, 0.8), (vec3, 0.7)]
    sorted_nodes = deterministic_sort(nodes, rng=rng)

    # Deterministic sampling
    selected = deterministic_sample(candidates, k=5, rng=rng)
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Any
import random as random_module


@dataclass
class SeededRNG:
    """Seeded random number generator for deterministic operations"""

    seed: int
    """Random seed (from z_slice.seed or user-provided)"""

    _rng: random_module.Random = field(init=False)
    """Internal Random instance"""

    def __post_init__(self):
        """Initialize RNG with seed"""
        self._rng = random_module.Random(self.seed)

    def random(self) -> float:
        """Generate random float in [0.0, 1.0)"""
        return self._rng.random()

    def randint(self, a: int, b: int) -> int:
        """Generate random integer in [a, b]"""
        return self._rng.randint(a, b)

    def choice(self, seq: List[Any]) -> Any:
        """Choose random element from sequence"""
        return self._rng.choice(seq)

    def shuffle(self, seq: List[Any]) -> List[Any]:
        """Shuffle sequence (returns copy)"""
        shuffled = seq.copy()
        self._rng.shuffle(shuffled)
        return shuffled

    def sample(self, population: List[Any], k: int) -> List[Any]:
        """Sample k elements from population without replacement"""
        return self._rng.sample(population, k=k)

    def reset(self) -> None:
        """Reset RNG to initial seed state"""
        self._rng = random_module.Random(self.seed)


def deterministic_sort(
    items: List[Tuple[Any, float]],
    rng: SeededRNG,
    key_index: int = 1,
    reverse: bool = True
) -> List[Tuple[Any, float]]:
    """
    Sort items by score with deterministic tie-breaking.

    Args:
        items: List of (item, score) tuples
        rng: Seeded RNG for tie-breaking
        key_index: Index of score in tuple (default: 1)
        reverse: Sort descending (default: True)

    Returns:
        Sorted list of (item, score) tuples

    Algorithm:
        1. Assign random tie-breaker to each item (deterministic from seed)
        2. Sort by (score, tie_breaker)
        3. Higher tie-breaker wins ties
    """
    # Assign tie-breakers
    items_with_tiebreaker = [
        (item, score, rng.random())
        for item, score in items
    ]

    # Sort by (score, tie_breaker)
    sorted_items = sorted(
        items_with_tiebreaker,
        key=lambda x: (x[key_index], x[2]),  # (score, tie_breaker)
        reverse=reverse
    )

    # Remove tie-breaker from result
    return [(item, score) for item, score, _ in sorted_items]


def deterministic_sample(
    population: List[Tuple[Any, float]],
    k: int,
    rng: SeededRNG
) -> List[Tuple[Any, float]]:
    """
    Sample k items from population (deterministic).

    Args:
        population: List of (item, score) tuples
        k: Number of items to sample
        rng: Seeded RNG for sampling

    Returns:
        List of k sampled (item, score) tuples

    Note:
        Sampling is without replacement.
        If k > len(population), returns all items.
    """
    if k >= len(population):
        return population.copy()

    return rng.sample(population, k=k)


def deterministic_top_k(
    items: List[Tuple[Any, float]],
    k: int,
    rng: SeededRNG
) -> List[Tuple[Any, float]]:
    """
    Select top-k items by score with deterministic tie-breaking.

    Args:
        items: List of (item, score) tuples
        k: Number of top items to select
        rng: Seeded RNG for tie-breaking

    Returns:
        List of top-k (item, score) tuples (sorted descending)

    Algorithm:
        1. Sort items deterministically
        2. Take first k
    """
    sorted_items = deterministic_sort(items, rng=rng, reverse=True)
    return sorted_items[:k]


def hash_to_seed(text: str) -> int:
    """
    Convert text to deterministic seed.

    Args:
        text: Input text (e.g., window ID, z_slice hash)

    Returns:
        Integer seed in [0, 2^32-1]

    Algorithm:
        Uses Python's built-in hash() with modulo to ensure positive int.
    """
    # Python's hash() returns signed int, convert to positive
    hash_value = hash(text)
    # Map to [0, 2^32-1] for consistent seed range
    seed = hash_value % (2**32)
    return seed


def combine_seeds(*seeds: int) -> int:
    """
    Combine multiple seeds into single deterministic seed.

    Args:
        *seeds: Variable number of integer seeds

    Returns:
        Combined seed

    Algorithm:
        XOR all seeds together, modulo 2^32
    """
    combined = 0
    for seed in seeds:
        combined ^= seed
    return combined % (2**32)
