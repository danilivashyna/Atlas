"""
MMR-like Rebalance (Phase B.3)

Implements Maximal Marginal Relevance (MMR) style rebalancing for FAB nodes:
- Coverage penalty: nodes too close to existing nodes get penalized
- Diversity boost: encourages spatial spread in vector space
- Soft rebalance: applies during fill() without breaking total cap

MMR formula (adapted):
    score_rebalanced = λ * score_base - (1-λ) * max(similarity to existing nodes)

    λ=1.0: pure relevance (no diversity)
    λ=0.0: pure diversity (max distance from existing)
    λ=0.5: balanced (default)

Usage:
    config = RebalanceConfig(
        lambda_weight=0.5,      # Balance relevance vs diversity
        distance_threshold=0.3,  # Distance below this triggers penalty
        min_distance_boost=0.1   # Minimum penalty for close nodes
    )

    rebalancer = MMRRebalancer(config=config)

    # Rebalance a candidate node
    new_score = rebalancer.rebalance_score(
        candidate_score=0.8,
        candidate_vector=[0.1, 0.2, ...],
        existing_nodes=[(vec1, score1), (vec2, score2), ...]
    )
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import math


@dataclass
class RebalanceConfig:
    """Configuration for MMR-like rebalancing"""

    lambda_weight: float = 0.5
    """Balance between relevance (1.0) and diversity (0.0). Default: 0.5 (balanced)"""

    distance_threshold: float = 0.3
    """Cosine distance threshold: nodes closer than this get penalized. Default: 0.3"""

    min_distance_boost: float = 0.1
    """Minimum penalty for nodes within distance_threshold. Default: 0.1"""

    max_penalty: float = 0.5
    """Maximum penalty (cap on diversity term). Default: 0.5"""


@dataclass
class RebalanceStats:
    """Statistics from rebalancing operation"""

    nodes_evaluated: int = 0
    """Number of candidate nodes evaluated"""

    nodes_penalized: int = 0
    """Number of nodes that received coverage penalty"""

    avg_penalty: float = 0.0
    """Average penalty applied (for diagnostics)"""

    max_similarity: float = 0.0
    """Maximum similarity encountered (closest pair)"""


class MMRRebalancer:
    """MMR-like rebalancer for FAB node selection"""

    def __init__(self, config: Optional[RebalanceConfig] = None):
        self.config = config or RebalanceConfig()
        self.stats = RebalanceStats()

    def cosine_distance(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Compute cosine distance between two vectors.

        Args:
            vec1: First vector (normalized)
            vec2: Second vector (normalized)

        Returns:
            Cosine distance in [0.0, 2.0] (0.0 = identical, 2.0 = opposite)

        Note:
            Assumes vectors are L2-normalized. If not, results may be inaccurate.
        """
        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimension mismatch: {len(vec1)} != {len(vec2)}")

        # Cosine similarity: dot product of normalized vectors
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        # Clamp to [-1, 1] to handle floating point errors
        dot_product = max(-1.0, min(1.0, dot_product))

        # Cosine distance: 1 - similarity
        similarity = dot_product
        distance = 1.0 - similarity

        return distance

    def compute_coverage_penalty(
        self, candidate_vector: List[float], existing_nodes: List[Tuple[List[float], float]]
    ) -> float:
        """
        Compute coverage penalty for a candidate node.

        Args:
            candidate_vector: Vector representation of candidate node
            existing_nodes: List of (vector, score) tuples for existing nodes

        Returns:
            Penalty in [0.0, max_penalty]. Higher = more similar to existing nodes.

        Algorithm:
            1. Compute distance to all existing nodes
            2. Find minimum distance (closest node)
            3. If min_distance < threshold: apply penalty
            4. Penalty = max_penalty * (1 - min_distance / threshold)
        """
        if not existing_nodes:
            return 0.0  # No existing nodes, no penalty

        # Find closest existing node
        min_distance = float("inf")
        for existing_vec, _ in existing_nodes:
            distance = self.cosine_distance(candidate_vector, existing_vec)
            min_distance = min(min_distance, distance)

        # Update stats
        max_similarity = 1.0 - min_distance
        self.stats.max_similarity = max(self.stats.max_similarity, max_similarity)

        # Apply penalty if within threshold
        if min_distance < self.config.distance_threshold:
            # Linear penalty: closer = higher penalty
            penalty_ratio = 1.0 - (min_distance / self.config.distance_threshold)
            penalty = min(
                self.config.max_penalty,
                self.config.min_distance_boost
                + (self.config.max_penalty - self.config.min_distance_boost) * penalty_ratio,
            )
            return penalty

        return 0.0  # Beyond threshold, no penalty

    def rebalance_score(
        self,
        candidate_score: float,
        candidate_vector: List[float],
        existing_nodes: List[Tuple[List[float], float]],
    ) -> float:
        """
        Rebalance candidate score using MMR formula.

        Args:
            candidate_score: Base relevance score [0.0, 1.0]
            candidate_vector: Vector representation of candidate
            existing_nodes: List of (vector, score) tuples for existing nodes

        Returns:
            Rebalanced score [0.0, 1.0]

        Formula:
            score_new = λ * score_base - (1-λ) * coverage_penalty
        """
        self.stats.nodes_evaluated += 1

        # Compute coverage penalty
        penalty = self.compute_coverage_penalty(candidate_vector, existing_nodes)

        # Track penalty stats
        if penalty > 0.0:
            self.stats.nodes_penalized += 1
            # Update running average
            prev_avg = self.stats.avg_penalty
            n = self.stats.nodes_penalized
            self.stats.avg_penalty = prev_avg + (penalty - prev_avg) / n

        # MMR formula
        relevance_term = self.config.lambda_weight * candidate_score
        diversity_term = (1.0 - self.config.lambda_weight) * penalty

        rebalanced_score = relevance_term - diversity_term

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, rebalanced_score))

    def rebalance_batch(
        self,
        candidates: List[Tuple[List[float], float]],
        existing_nodes: List[Tuple[List[float], float]],
        top_k: int,
    ) -> List[Tuple[List[float], float, float]]:
        """
        Rebalance a batch of candidates and select top-k.

        Args:
            candidates: List of (vector, base_score) tuples
            existing_nodes: List of (vector, score) tuples for existing nodes
            top_k: Number of candidates to select

        Returns:
            List of (vector, base_score, rebalanced_score) tuples (top-k by rebalanced score)

        Algorithm:
            1. Compute rebalanced score for each candidate
            2. Sort by rebalanced score (descending)
            3. Select top-k
            4. Incrementally add to existing_nodes (greedy MMR)
        """
        results = []
        current_existing = list(existing_nodes)  # Copy to avoid mutation

        # Greedy selection: pick best, add to existing, repeat
        remaining_candidates = candidates.copy()

        for _ in range(min(top_k, len(candidates))):
            if not remaining_candidates:
                break

            # Rebalance all remaining candidates
            scored_candidates = []
            for vec, base_score in remaining_candidates:
                rebalanced = self.rebalance_score(base_score, vec, current_existing)
                scored_candidates.append((vec, base_score, rebalanced))

            # Pick best rebalanced score
            best_idx = max(range(len(scored_candidates)), key=lambda i: scored_candidates[i][2])
            best_vec, best_base, best_rebalanced = scored_candidates[best_idx]

            # Add to results and existing nodes
            results.append((best_vec, best_base, best_rebalanced))
            current_existing.append((best_vec, best_rebalanced))

            # Remove from remaining
            remaining_candidates.pop(best_idx)

        return results

    def reset_stats(self) -> RebalanceStats:
        """Reset statistics and return previous stats"""
        old_stats = self.stats
        self.stats = RebalanceStats()
        return old_stats

    def get_stats(self) -> RebalanceStats:
        """Get current statistics (without resetting)"""
        return self.stats
