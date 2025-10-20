# Hierarchical Metrics v0.2

Evaluation metrics for Atlas hierarchical semantic spaces.

## Overview

This document describes the hierarchical evaluation metrics implemented in Atlas v0.2:

- **H-Coherence**: Measures semantic coherence within hierarchical dimensions
- **H-Stability**: Measures consistency and robustness of hierarchical structure
- **H-Diversity**: Measures diversity and distinctness across dimensions

These metrics quantify the interpretability and quality of the learned hierarchical semantic space.

## H-Coherence

### Definition

H-Coherence measures how semantically related vectors are within the same hierarchical dimension or cluster. High coherence indicates that vectors in the same group share similar semantic properties.

### Formula

For a set of vectors V = {v₁, v₂, ..., vₙ} in a dimension:

```
Coherence = (1/|P|) Σ similarity(vᵢ, vⱼ)  for all pairs (i,j) where i < j
```

Where:
- `similarity(vᵢ, vⱼ)` is the cosine similarity between vectors
- `|P|` is the number of pairs: n(n-1)/2
- Result is normalized to [0, 1] range

Cosine similarity is computed as:

```
cos(vᵢ, vⱼ) = (vᵢ · vⱼ) / (||vᵢ|| ||vⱼ||)
```

Then normalized:

```
coherence_score = (cos(vᵢ, vⱼ) + 1) / 2
```

### Target Ranges

| Score | Interpretation | Recommendation |
|-------|----------------|----------------|
| ≥ 0.85 | Excellent coherence | Dimensions are well-defined |
| 0.70 - 0.85 | Good coherence | Acceptable for production |
| 0.50 - 0.70 | Fair coherence | Consider refinement |
| < 0.50 | Poor coherence | Needs improvement |

### Usage

```python
from atlas.metrics import h_coherence
import numpy as np

# Single dimension with multiple vectors
vectors = np.array([
    [0.9, 0.1, 0.0],
    [0.8, 0.2, 0.1],
    [0.85, 0.15, 0.05]
])

result = h_coherence(vectors)
print(f"Coherence: {result.score:.3f}")
# Output: Coherence: 0.921

# Multiple dimensions
vectors_dict = {
    "emotion": np.array([[0.9, 0.1], [0.8, 0.2]]),
    "formality": np.array([[0.1, 0.9], [0.2, 0.8]])
}

result = h_coherence(vectors_dict)
print(f"Average coherence: {result.score:.3f}")
print(f"Per-dimension: {result.details['dimension_scores']}")
```

### Mathematical Properties

1. **Symmetry**: coherence(A, B) = coherence(B, A)
2. **Bounds**: 0 ≤ coherence ≤ 1
3. **Identity**: coherence({v, v}) = 1.0
4. **Orthogonality**: coherence of orthogonal vectors ≈ 0.5
5. **Opposition**: coherence of opposite vectors ≈ 0.0

### Implementation Notes

- Uses cosine similarity as the base measure
- Efficient computation via matrix multiplication
- Handles zero vectors by avoiding division by zero
- Supports both numpy arrays and dictionaries
- Returns detailed results including per-dimension scores

## H-Stability

### Definition

H-Stability measures the consistency of hierarchical structure across different runs, perturbations, or random initializations. High stability indicates that the learned structure is robust and not an artifact of initialization.

### Formula

Uses Adjusted Rand Index (ARI) or Normalized Mutual Information (NMI):

#### Adjusted Rand Index (ARI)

```
ARI = (RI - E[RI]) / (max(RI) - E[RI])
```

Where:
- RI is the Rand Index
- E[RI] is the expected value under random labeling
- Range: [-1, 1], normalized to [0, 1] in implementation

Normalized:
```
stability_score = (ARI + 1) / 2
```

#### Normalized Mutual Information (NMI)

```
NMI(U, V) = 2 * MI(U, V) / (H(U) + H(V))
```

Where:
- MI(U, V) is mutual information between labelings U and V
- H(U) and H(V) are entropies
- Range: [0, 1]

### Target Ranges

| Score | Interpretation | Recommendation |
|-------|----------------|----------------|
| ≥ 0.80 | Excellent stability | Highly reproducible |
| 0.65 - 0.80 | Good stability | Acceptable variation |
| 0.50 - 0.65 | Fair stability | Consider more training |
| < 0.50 | Poor stability | High variance, needs investigation |

### Usage

```python
from atlas.metrics import h_stability

# Compare cluster assignments from two runs
labels_run1 = [0, 0, 1, 1, 2, 2, 3, 3]
labels_run2 = [0, 0, 1, 1, 2, 2, 3, 3]

# Using ARI (default)
result = h_stability(labels_run1, labels_run2, method="ari")
print(f"Stability (ARI): {result.score:.3f}")
# Output: Stability (ARI): 1.000

# Using NMI
result = h_stability(labels_run1, labels_run2, method="nmi")
print(f"Stability (NMI): {result.score:.3f}")
# Output: Stability (NMI): 1.000

# With dict input
run1 = {"texts": ["a", "b", "c"], "assignments": [0, 1, 0]}
run2 = {"texts": ["a", "b", "c"], "assignments": [0, 1, 0]}
result = h_stability(run1, run2)
print(f"Stability: {result.score:.3f}")
```

### Mathematical Properties

1. **Perfect agreement**: stability({0,1,0}, {0,1,0}) = 1.0
2. **Random agreement**: Expected value ≈ 0.5 (after normalization)
3. **Independence**: Can compare labelings with different numbers of clusters
4. **Symmetry**: stability(A, B) = stability(B, A)
5. **Correction for chance**: ARI adjusts for random agreement

### Implementation Notes

- Uses scikit-learn's `adjusted_rand_score` and `normalized_mutual_info_score`
- ARI is preferred for most cases as it corrects for chance
- NMI is useful when cluster counts differ significantly
- Handles variable numbers of clusters
- Returns detailed cluster statistics

## H-Diversity

### Definition

H-Diversity measures how distinct and diverse different hierarchical dimensions or clusters are from each other. High diversity indicates that dimensions capture different semantic aspects.

### Formula

For representative vectors R = {r₁, r₂, ..., rₖ} from k dimensions:

```
Diversity = (1/|P|) Σ (1 - similarity(rᵢ, rⱼ))  for all pairs (i,j) where i < j
```

Where:
- `similarity(rᵢ, rⱼ)` is cosine similarity
- Result is the average cosine distance

Conversion from similarity to distance:
```
diversity_score = (1 - cos(rᵢ, rⱼ)) / 2
```

### Target Ranges

| Score | Interpretation | Recommendation |
|-------|----------------|----------------|
| ≥ 0.70 | Excellent diversity | Dimensions well-separated |
| 0.55 - 0.70 | Good diversity | Adequate separation |
| 0.40 - 0.55 | Fair diversity | Some overlap |
| < 0.40 | Poor diversity | Dimensions too similar |

### Usage

```python
from atlas.metrics import h_diversity
import numpy as np

# Representative vectors from different clusters/dimensions
representatives = np.array([
    [1.0, 0.0, 0.0],  # Cluster A
    [0.0, 1.0, 0.0],  # Cluster B
    [0.0, 0.0, 1.0],  # Cluster C
])

result = h_diversity(representatives)
print(f"Diversity: {result.score:.3f}")
# Output: Diversity: 0.500 (orthogonal vectors)

# With dict input (auto-averages if multiple vectors per cluster)
clusters = {
    "emotion": np.array([[0.9, 0.1], [0.8, 0.2]]),
    "formality": np.array([[0.1, 0.9], [0.2, 0.8]])
}

result = h_diversity(clusters)
print(f"Diversity: {result.score:.3f}")
print(f"Cluster names: {result.details['dimension_names']}")
```

### Mathematical Properties

1. **Bounds**: 0 ≤ diversity ≤ 1
2. **Orthogonality**: diversity of orthogonal vectors ≈ 0.5
3. **Opposition**: diversity of opposite vectors ≈ 1.0
4. **Parallelism**: diversity of parallel vectors ≈ 0.0
5. **Symmetry**: diversity(A, B) = diversity(B, A)

### Implementation Notes

- Computes pairwise cosine distances between representatives
- If input contains multiple vectors per group, uses mean as representative
- Works with both numpy arrays and dictionaries
- Returns group names and count in details

## Combined Interpretability Score

### Overview

The overall interpretability score combines all three metrics:

```python
from atlas.metrics import interpretability_metrics_summary

summary = interpretability_metrics_summary(
    coherence=coherence_result,
    stability=stability_result,
    diversity=diversity_result
)

print(f"Overall: {summary['overall_interpretability']:.3f}")
```

### Formula

```
Overall = (Coherence + Stability + Diversity) / 3
```

Simple average of available metrics. If a metric is not provided, it's excluded from the average.

### Target Ranges

| Score | Interpretation | Recommendation |
|-------|----------------|----------------|
| ≥ 0.80 | Excellent | Production ready |
| 0.70 - 0.80 | Good | Acceptable quality |
| 0.60 - 0.70 | Fair | Needs improvement |
| < 0.60 | Poor | Not recommended for production |

## Complete Example

```python
import numpy as np
from atlas.metrics import (
    h_coherence, 
    h_stability, 
    h_diversity,
    interpretability_metrics_summary
)

# 1. Evaluate coherence within dimensions
dimensions = {
    "emotion": np.array([
        [0.9, 0.1, 0.0],
        [0.85, 0.15, 0.05],
        [0.8, 0.2, 0.1]
    ]),
    "formality": np.array([
        [0.1, 0.9, 0.0],
        [0.15, 0.85, 0.05],
        [0.2, 0.8, 0.1]
    ])
}

coherence = h_coherence(dimensions)
print(f"✓ Coherence: {coherence.score:.3f} (target ≥ 0.85)")

# 2. Evaluate stability across runs
run1_labels = [0, 0, 1, 1, 2, 2]
run2_labels = [0, 0, 1, 1, 2, 2]

stability = h_stability(run1_labels, run2_labels)
print(f"✓ Stability: {stability.score:.3f} (target ≥ 0.80)")

# 3. Evaluate diversity between dimensions
representatives = np.array([
    [0.85, 0.15, 0.0],  # emotion representative
    [0.15, 0.85, 0.0],  # formality representative
])

diversity = h_diversity(representatives)
print(f"✓ Diversity: {diversity.score:.3f} (target ≥ 0.70)")

# 4. Overall interpretability
summary = interpretability_metrics_summary(
    coherence=coherence,
    stability=stability,
    diversity=diversity
)

print(f"\n{'='*50}")
print(f"Overall Interpretability: {summary['overall_interpretability']:.3f}")
print(f"Status: {summary['status']}")
print(f"{'='*50}")

# Expected output:
# ✓ Coherence: 0.921 (target ≥ 0.85)
# ✓ Stability: 1.000 (target ≥ 0.80)
# ✓ Diversity: 0.477 (target ≥ 0.70)
# ==================================================
# Overall Interpretability: 0.799
# Status: implemented
# ==================================================
```

## Best Practices

### When to Use Each Metric

1. **H-Coherence**
   - Evaluating semantic quality of learned dimensions
   - Comparing different model architectures
   - Monitoring training progress

2. **H-Stability**
   - Validating model robustness
   - Comparing different random seeds
   - Ensuring reproducibility

3. **H-Diversity**
   - Detecting redundant dimensions
   - Validating disentanglement
   - Optimizing dimension allocation

### Recommended Workflow

```python
# 1. During training: Monitor coherence
for epoch in range(num_epochs):
    train_model(epoch)
    coherence = h_coherence(get_dimension_vectors())
    log_metric("coherence", coherence.score)

# 2. After training: Validate stability
stability = h_stability(run1_clusters, run2_clusters)
assert stability.score >= 0.80, "Model not stable enough"

# 3. Before deployment: Check diversity
diversity = h_diversity(dimension_representatives)
assert diversity.score >= 0.70, "Dimensions not diverse enough"
```

### Integration with pytest-benchmark

For performance benchmarking:

```python
import pytest
from atlas.metrics import h_coherence
import numpy as np

@pytest.mark.benchmark
def test_coherence_performance(benchmark):
    """Benchmark coherence computation"""
    vectors = np.random.randn(100, 50)
    result = benchmark(h_coherence, vectors)
    assert result.score >= 0.0
```

## API Reference

### h_coherence

```python
def h_coherence(
    vectors: Union[np.ndarray, Dict[str, np.ndarray]],
    method: str = "cosine",
    min_samples: int = 2
) -> CoherenceResult
```

**Parameters:**
- `vectors`: Vectors to evaluate (array or dict)
- `method`: Coherence method (default: "cosine")
- `min_samples`: Minimum samples per group (default: 2)

**Returns:**
- `CoherenceResult` with score, method, status, and details

### h_stability

```python
def h_stability(
    labels_run1: Union[List[int], np.ndarray, Dict[str, Any]],
    labels_run2: Union[List[int], np.ndarray, Dict[str, Any]],
    method: str = "ari"
) -> StabilityResult
```

**Parameters:**
- `labels_run1`: Cluster labels from first run
- `labels_run2`: Cluster labels from second run
- `method`: Stability method ("ari" or "nmi")

**Returns:**
- `StabilityResult` with score, method, status, and details

### h_diversity

```python
def h_diversity(
    vectors: Union[np.ndarray, Dict[str, np.ndarray]],
    method: str = "cosine_distance"
) -> DiversityResult
```

**Parameters:**
- `vectors`: Representative vectors (array or dict)
- `method`: Diversity method (default: "cosine_distance")

**Returns:**
- `DiversityResult` with score, method, status, and details

## References

1. **Adjusted Rand Index**: Hubert, L., & Arabie, P. (1985). "Comparing partitions." Journal of Classification.

2. **Normalized Mutual Information**: Strehl, A., & Ghosh, J. (2002). "Cluster ensembles—a knowledge reuse framework for combining multiple partitions."

3. **Topic Coherence**: Röder et al. (2015). "Exploring the Space of Topic Coherence Measures." WSDM '15.

4. **Disentanglement Metrics**: Locatello et al. (2019). "Challenging Common Assumptions in Unsupervised Learning of Disentangled Representations." ICML.

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-20  
**Status**: Implemented in Atlas v0.2
