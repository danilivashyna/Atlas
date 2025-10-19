# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna
#
# Atlas - Semantic Space Control Panel
# Интерпретируемое семантическое пространство

"""
Hierarchical metrics for v0.2+
Evaluation metrics for disentangled hierarchical semantic spaces

TODO (v0.2.1+):
- Implement H-Coherence using NPMI (Normalized Pointwise Mutual Information)
- Implement H-Stability using ARI/NMI (Adjusted Rand Index / Normalized Mutual Information)
- Add topic coherence via word embeddings
- Add stability tests across multiple runs
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass


@dataclass
class CoherenceResult:
    """Result of coherence evaluation"""
    score: float  # 0..1
    method: str
    status: str  # "stub" or "implemented"


@dataclass
class StabilityResult:
    """Result of stability evaluation"""
    score: float  # 0..1
    method: str
    status: str  # "stub" or "implemented"


def h_coherence_stub(
    dim_top_terms: Dict[str, List[str]],
    method: str = "npmi-stub"
) -> CoherenceResult:
    """
    Hierarchical coherence evaluation (STUB for v0.2).
    
    Measures semantic coherence of each hierarchical dimension.
    
    For v0.2: Returns 0.5 (neutral score)
    For v0.2.1+: Implement NPMI-based coherence
    
    Args:
        dim_top_terms: Dict mapping dim_name -> [top_k_terms]
            Example: {
                "dim0": ["собака", "кот", "лиса"],
                "dim1": ["любовь", "радость", "счастье"],
                ...
            }
        method: Coherence method ("npmi", "umass", "c_v", etc.)
        
    Returns:
        CoherenceResult with score in [0, 1]
        
    Example:
        >>> terms = {"dim0": ["dog", "cat", "mouse"], "dim1": ["love", "joy"]}
        >>> result = h_coherence_stub(terms)
        >>> result.score
        0.5
        >>> result.status
        'stub'
    """
    # MVP: Return neutral score
    # TODO (v0.2.1): Implement real NPMI coherence
    
    if not dim_top_terms:
        return CoherenceResult(
            score=0.0,
            method=f"{method} (stub)",
            status="stub"
        )
    
    # Placeholder: average based on number of terms
    avg_terms = sum(len(terms) for terms in dim_top_terms.values()) / len(dim_top_terms)
    score = min(avg_terms / 10.0, 1.0)  # Heuristic: 10 terms = perfect coherence
    
    return CoherenceResult(
        score=round(score, 3),
        method=f"{method} (stub - MVP)",
        status="stub"
    )


def h_stability_stub(
    labels_run1: Dict[str, Any],
    labels_run2: Dict[str, Any],
    method: str = "ari-stub"
) -> StabilityResult:
    """
    Hierarchical stability evaluation (STUB for v0.2).
    
    Measures consistency of hierarchical structure across runs.
    
    For v0.2: Returns 0.5 (neutral score)
    For v0.2.1+: Implement ARI/NMI-based stability
    
    Args:
        labels_run1: Cluster labels from run 1
            Example: {"texts": [...], "assignments": [0, 1, 0, 2, ...]}
        labels_run2: Cluster labels from run 2 (same structure)
        method: Stability method ("ari", "nmi", "adjusted_mutual_info", etc.)
        
    Returns:
        StabilityResult with score in [0, 1]
        
    Example:
        >>> run1 = {"texts": ["a", "b", "c"], "assignments": [0, 1, 0]}
        >>> run2 = {"texts": ["a", "b", "c"], "assignments": [0, 1, 0]}
        >>> result = h_stability_stub(run1, run2)
        >>> result.score
        1.0  # Perfect agreement
        >>> result.status
        'stub'
    """
    # MVP: Check if assignments are identical
    # TODO (v0.2.1): Implement real ARI/NMI stability
    
    if not labels_run1 or not labels_run2:
        return StabilityResult(
            score=0.0,
            method=f"{method} (stub)",
            status="stub"
        )
    
    # Simple check: perfect agreement if assignments are identical
    assign1 = labels_run1.get("assignments", [])
    assign2 = labels_run2.get("assignments", [])
    
    if not assign1 or not assign2:
        score = 0.5  # Unknown
    elif assign1 == assign2:
        score = 1.0  # Perfect agreement
    else:
        score = 0.5  # Partial (stub - real implementation would use ARI/NMI)
    
    return StabilityResult(
        score=round(score, 3),
        method=f"{method} (stub - MVP)",
        status="stub"
    )


def interpretability_metrics_summary(
    coherence: Optional[CoherenceResult] = None,
    stability: Optional[StabilityResult] = None
) -> Dict[str, Any]:
    """
    Summary of interpretability metrics.
    
    Args:
        coherence: Result from h_coherence_stub()
        stability: Result from h_stability_stub()
        
    Returns:
        Dict with combined metrics
    """
    summary = {
        "version": "v0.2 (MVP)",
        "status": "stub",
        "coherence": coherence.score if coherence else None,
        "stability": stability.score if stability else None,
        "notice": "Full metric implementations coming in v0.2.1+"
    }
    
    if coherence and stability:
        avg = (coherence.score + stability.score) / 2.0
        summary["overall_interpretability"] = round(avg, 3)
    
    return summary


# TODO: Implement these in v0.2.1+
"""
IMPLEMENTATION ROADMAP FOR v0.2.1+

1. H-Coherence (NPMI-based):
   - Compute co-occurrence frequencies for term pairs
   - Calculate NPMI scores
   - Average across dimension terms
   - Handle vocabulary size normalization

2. H-Stability (ARI/NMI-based):
   - Compare cluster assignments across runs
   - Compute Adjusted Rand Index (ARI)
   - Compute Normalized Mutual Information (NMI)
   - Handle variable number of clusters

3. Additional metrics:
   - Disentanglement score (SAP, FactorVAE-based)
   - Hierarchy depth utilization
   - Router entropy (percentage of active routes)
   - Cross-layer consistency

4. Benchmarking:
   - p50/p95 latency across hierarchy depths
   - Memory usage per level
   - Throughput (samples/sec)
"""
