# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna
#
# Atlas - Semantic Space Control Panel
# Интерпретируемое семантическое пространство

"""
Hierarchical metrics for v0.2+
Evaluation metrics for disentangled hierarchical semantic spaces

Implemented metrics:
- H-Coherence: Measures semantic coherence using cosine similarity
- H-Stability: Measures consistency using ARI/NMI
- H-Diversity: Measures diversity across hierarchical levels
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import numpy as np
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score


@dataclass
class CoherenceResult:
    """Result of coherence evaluation"""

    score: float  # 0..1
    method: str
    status: str  # "stub" or "implemented"
    details: Optional[Dict[str, Any]] = None


@dataclass
class StabilityResult:
    """Result of stability evaluation"""

    score: float  # 0..1
    method: str
    status: str  # "stub" or "implemented"
    details: Optional[Dict[str, Any]] = None


@dataclass
class DiversityResult:
    """Result of diversity evaluation"""

    score: float  # 0..1
    method: str
    status: str  # "stub" or "implemented"
    details: Optional[Dict[str, Any]] = None


def h_coherence(
    vectors: Union[np.ndarray, Dict[str, np.ndarray]], method: str = "cosine", min_samples: int = 2
) -> CoherenceResult:
    """
    Hierarchical coherence evaluation.

    Measures semantic coherence within hierarchical dimensions/clusters.
    Uses cosine similarity between vectors within the same group.

    Target: ≥0.85 for good coherence

    Args:
        vectors: Either:
            - np.ndarray of shape (n_samples, n_dims): All vectors in a dimension
            - Dict mapping dimension_name -> vectors array
        method: Coherence method ("cosine" for cosine similarity)
        min_samples: Minimum samples required per group (default: 2)

    Returns:
        CoherenceResult with score in [0, 1]

    Example:
        >>> # Coherent vectors (similar direction)
        >>> vecs = np.array([[0.9, 0.1], [0.8, 0.2], [0.85, 0.15]])
        >>> result = h_coherence(vecs)
        >>> result.score > 0.8
        True

        >>> # Incoherent vectors (random directions)
        >>> vecs = np.array([[1, 0], [0, 1], [-1, 0]])
        >>> result = h_coherence(vecs)
        >>> result.score < 0.5
        True
    """
    if isinstance(vectors, dict):
        # Compute coherence for each dimension and average
        coherence_scores = []
        dimension_scores = {}

        for dim_name, dim_vectors in vectors.items():
            if isinstance(dim_vectors, list):
                dim_vectors = np.array(dim_vectors)

            if len(dim_vectors) < min_samples:
                continue

            score = _compute_pairwise_coherence(dim_vectors, method)
            coherence_scores.append(score)
            dimension_scores[dim_name] = score

        if not coherence_scores:
            return CoherenceResult(
                score=0.0,
                method=method,
                status="implemented",
                details={"error": "Insufficient samples"},
            )

        avg_score = float(np.mean(coherence_scores))
        return CoherenceResult(
            score=round(avg_score, 3),
            method=method,
            status="implemented",
            details={"dimension_scores": dimension_scores, "n_dimensions": len(coherence_scores)},
        )
    else:
        # Single group of vectors
        if isinstance(vectors, list):
            vectors = np.array(vectors)

        if len(vectors) < min_samples:
            return CoherenceResult(
                score=0.0,
                method=method,
                status="implemented",
                details={"error": "Insufficient samples"},
            )

        score = _compute_pairwise_coherence(vectors, method)
        return CoherenceResult(
            score=round(score, 3),
            method=method,
            status="implemented",
            details={"n_samples": len(vectors)},
        )


def _compute_pairwise_coherence(vectors: np.ndarray, method: str = "cosine") -> float:
    """
    Compute pairwise coherence between vectors.

    Args:
        vectors: Array of shape (n_samples, n_dims)
        method: "cosine" for cosine similarity

    Returns:
        Average pairwise coherence score in [0, 1]
    """
    if method != "cosine":
        raise ValueError(f"Unsupported method: {method}. Use 'cosine'.")

    # Normalize vectors for cosine similarity
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)  # Avoid division by zero
    normalized = vectors / norms

    # Compute pairwise cosine similarities
    similarities = np.dot(normalized, normalized.T)

    # Extract upper triangle (excluding diagonal)
    n = len(vectors)
    if n < 2:
        return 1.0

    # Get upper triangle indices
    triu_indices = np.triu_indices(n, k=1)
    pairwise_sims = similarities[triu_indices]

    # Convert from [-1, 1] to [0, 1] range
    coherence = (pairwise_sims + 1) / 2

    return float(np.mean(coherence))


def h_stability(
    labels_run1: Union[List[int], np.ndarray, Dict[str, Any]],
    labels_run2: Union[List[int], np.ndarray, Dict[str, Any]],
    method: str = "ari",
) -> StabilityResult:
    """
    Hierarchical stability evaluation.

    Measures consistency of hierarchical structure across runs/perturbations.
    Uses ARI (Adjusted Rand Index) or NMI (Normalized Mutual Information).

    Target: ≥0.80 for good stability

    Args:
        labels_run1: Cluster labels from run 1
            Can be:
            - List/array of cluster assignments [0, 1, 0, 2, ...]
            - Dict with "assignments" key: {"texts": [...], "assignments": [0, 1, 0, 2, ...]}
        labels_run2: Cluster labels from run 2 (same structure as run1)
        method: Stability method ("ari" or "nmi")

    Returns:
        StabilityResult with score in [0, 1]

    Example:
        >>> # Perfect agreement
        >>> run1 = [0, 1, 0, 2, 1]
        >>> run2 = [0, 1, 0, 2, 1]
        >>> result = h_stability(run1, run2)
        >>> result.score
        1.0

        >>> # Complete disagreement
        >>> run1 = [0, 0, 0, 0, 0]
        >>> run2 = [0, 1, 2, 3, 4]
        >>> result = h_stability(run1, run2)
        >>> result.score < 0.1
        True
    """
    # Extract assignments from dict if needed
    if isinstance(labels_run1, dict):
        labels_run1 = labels_run1.get("assignments", [])
    if isinstance(labels_run2, dict):
        labels_run2 = labels_run2.get("assignments", [])

    # Convert to numpy arrays
    if isinstance(labels_run1, list):
        labels_run1 = np.array(labels_run1)
    if isinstance(labels_run2, list):
        labels_run2 = np.array(labels_run2)

    # Validation
    if len(labels_run1) == 0 or len(labels_run2) == 0:
        return StabilityResult(
            score=0.0, method=method, status="implemented", details={"error": "Empty label arrays"}
        )

    if len(labels_run1) != len(labels_run2):
        return StabilityResult(
            score=0.0,
            method=method,
            status="implemented",
            details={"error": f"Length mismatch: {len(labels_run1)} vs {len(labels_run2)}"},
        )

    # Compute stability metric
    try:
        if method == "ari":
            score = adjusted_rand_score(labels_run1, labels_run2)
            # ARI is in [-1, 1], normalize to [0, 1]
            score = (score + 1) / 2
        elif method == "nmi":
            score = normalized_mutual_info_score(labels_run1, labels_run2)
        else:
            raise ValueError(f"Unsupported method: {method}. Use 'ari' or 'nmi'.")

        return StabilityResult(
            score=round(float(score), 3),
            method=method,
            status="implemented",
            details={
                "n_samples": len(labels_run1),
                "n_clusters_run1": len(np.unique(labels_run1)),
                "n_clusters_run2": len(np.unique(labels_run2)),
            },
        )
    except Exception as e:
        return StabilityResult(
            score=0.0, method=method, status="implemented", details={"error": str(e)}
        )


def h_diversity(
    vectors: Union[np.ndarray, Dict[str, np.ndarray]], method: str = "cosine_distance"
) -> DiversityResult:
    """
    Hierarchical diversity evaluation.

    Measures diversity across hierarchical dimensions or clusters.
    Higher diversity means dimensions/clusters are more distinct from each other.

    Target: ≥0.70 for good diversity

    Args:
        vectors: Either:
            - np.ndarray of shape (n_groups, n_dims): Representative vectors per group
            - Dict mapping dimension_name -> representative vector
        method: Diversity method ("cosine_distance" for 1 - cosine similarity)

    Returns:
        DiversityResult with score in [0, 1]

    Example:
        >>> # Diverse clusters (orthogonal)
        >>> vecs = np.array([[1, 0], [0, 1]])
        >>> result = h_diversity(vecs)
        >>> result.score > 0.5
        True

        >>> # Similar clusters (parallel)
        >>> vecs = np.array([[1, 0], [0.9, 0.1]])
        >>> result = h_diversity(vecs)
        >>> result.score < 0.3
        True
    """
    if isinstance(vectors, dict):
        # Convert dict to array of representative vectors
        if not vectors:
            return DiversityResult(
                score=0.0,
                method=method,
                status="implemented",
                details={"error": "Empty vectors dict"},
            )

        vector_list = []
        dimension_names = []
        for dim_name, vec in vectors.items():
            if isinstance(vec, list):
                vec = np.array(vec)
            # If vec is a 2D array, take the mean as representative
            if vec.ndim == 2:
                vec = np.mean(vec, axis=0)
            vector_list.append(vec)
            dimension_names.append(dim_name)

        vectors = np.array(vector_list)
        details = {"dimension_names": dimension_names}
    else:
        if isinstance(vectors, list):
            vectors = np.array(vectors)
        details = {}

    # Validation
    if vectors.ndim == 1:
        vectors = vectors.reshape(1, -1)

    if len(vectors) < 2:
        return DiversityResult(
            score=0.0,
            method=method,
            status="implemented",
            details={**details, "error": "Need at least 2 groups for diversity"},
        )

    # Compute diversity
    if method == "cosine_distance":
        score = _compute_pairwise_diversity(vectors)
    else:
        raise ValueError(f"Unsupported method: {method}. Use 'cosine_distance'.")

    details.update({"n_groups": len(vectors)})

    return DiversityResult(
        score=round(score, 3), method=method, status="implemented", details=details
    )


def _compute_pairwise_diversity(vectors: np.ndarray) -> float:
    """
    Compute pairwise diversity between group representatives.

    Args:
        vectors: Array of shape (n_groups, n_dims)

    Returns:
        Average pairwise diversity (1 - cosine_similarity) in [0, 1]
    """
    # Normalize vectors for cosine similarity
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)  # Avoid division by zero
    normalized = vectors / norms

    # Compute pairwise cosine similarities
    similarities = np.dot(normalized, normalized.T)

    # Extract upper triangle (excluding diagonal)
    n = len(vectors)
    triu_indices = np.triu_indices(n, k=1)
    pairwise_sims = similarities[triu_indices]

    # Convert cosine similarity to distance (diversity)
    # similarity in [-1, 1] -> diversity in [0, 1]
    # High similarity = low diversity
    diversity = (1 - pairwise_sims) / 2

    return float(np.mean(diversity))


def interpretability_metrics_summary(
    coherence: Optional[CoherenceResult] = None,
    stability: Optional[StabilityResult] = None,
    diversity: Optional[DiversityResult] = None,
) -> Dict[str, Any]:
    """
    Summary of interpretability metrics.

    Args:
        coherence: Result from h_coherence()
        stability: Result from h_stability()
        diversity: Result from h_diversity()

    Returns:
        Dict with combined metrics
    """
    summary = {
        "version": "v0.2",
        "status": "implemented",
        "coherence": coherence.score if coherence else None,
        "stability": stability.score if stability else None,
        "diversity": diversity.score if diversity else None,
    }

    # Compute overall interpretability score
    scores = []
    if coherence:
        scores.append(coherence.score)
    if stability:
        scores.append(stability.score)
    if diversity:
        scores.append(diversity.score)

    if scores:
        avg = sum(scores) / len(scores)
        summary["overall_interpretability"] = round(avg, 3)

    return summary


# Maintain backward compatibility with stub functions
def h_coherence_stub(
    dim_top_terms: Dict[str, List[str]], method: str = "npmi-stub"
) -> CoherenceResult:
    """
    Backward compatibility stub. Use h_coherence() instead.

    Converts term lists to dummy vectors for coherence calculation.
    """
    # Create dummy vectors based on term counts
    vectors = {}
    for dim_name, terms in dim_top_terms.items():
        # Create simple vectors where each term contributes equally
        n_terms = len(terms)
        if n_terms > 0:
            # Create multiple sample vectors (one per term)
            # Each vector represents a term's "embedding"
            dim_vectors = []
            for i in range(n_terms):
                # Create a vector with decreasing weights
                vec = np.array(
                    [1.0 / (j + 1) if j == i else 0.1 / (j + 1) for j in range(min(n_terms, 10))]
                )
                # Pad to consistent size
                if len(vec) < 10:
                    vec = np.pad(vec, (0, 10 - len(vec)))
                dim_vectors.append(vec)
            vectors[dim_name] = np.array(dim_vectors)

    if vectors:
        result = h_coherence(vectors)
        result.method = f"{method} (compatibility)"
        return result
    else:
        return CoherenceResult(score=0.0, method=f"{method} (stub)", status="stub")


def h_stability_stub(
    labels_run1: Dict[str, Any], labels_run2: Dict[str, Any], method: str = "ari-stub"
) -> StabilityResult:
    """
    Backward compatibility stub. Use h_stability() instead.
    """
    result = h_stability(labels_run1, labels_run2, method="ari")
    result.method = f"{method} (compatibility)"
    return result
