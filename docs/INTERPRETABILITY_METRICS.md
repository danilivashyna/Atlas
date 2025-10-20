# Interpretability Metrics

This document defines metrics for evaluating the interpretability of Atlas' semantic dimensions.

## Overview

Interpretability is not just about model accuracy—it's about whether humans can understand and trust the model's representations. We evaluate interpretability through both automated metrics and human evaluation.

## Automated Metrics

### 1. Dim-Coherence@k

**Definition**: Topic coherence for the top-k words associated with each dimension.

**Purpose**: Measure whether words that strongly activate a dimension are semantically related.

**Method**: Use NPMI (Normalized Pointwise Mutual Information) or topic coherence scores.

#### Implementation

```python
def dim_coherence_at_k(dimension: int, k: int = 20) -> float:
    """
    Compute coherence for top-k words in a dimension.

    Args:
        dimension: Which dimension to evaluate (0-4)
        k: Number of top words to consider

    Returns:
        Coherence score (higher is better, range roughly [-1, 1])
    """
    # 1. Find top-k words for this dimension
    top_words = get_top_k_words_for_dimension(dimension, k)

    # 2. Compute NPMI for all word pairs
    npmi_scores = []
    for i, w1 in enumerate(top_words):
        for j, w2 in enumerate(top_words):
            if i < j:  # Avoid duplicates
                npmi = compute_npmi(w1, w2)
                npmi_scores.append(npmi)

    # 3. Average NPMI
    coherence = np.mean(npmi_scores)
    return coherence

def get_top_k_words_for_dimension(dimension: int, k: int) -> List[str]:
    """Get words that most strongly activate this dimension"""
    # Encode all words in vocabulary
    words = load_vocabulary()
    vectors = encoder(words)

    # Sort by absolute value in this dimension
    dim_values = np.abs(vectors[:, dimension])
    top_indices = np.argsort(dim_values)[-k:]

    return [words[i] for i in top_indices]

def compute_npmi(word1: str, word2: str, corpus=None) -> float:
    """
    Compute Normalized PMI between two words.

    NPMI = PMI(w1, w2) / -log(p(w1, w2))

    Requires a reference corpus to compute co-occurrence.
    """
    if corpus is None:
        corpus = load_reference_corpus()

    # Count occurrences
    p_w1 = count_word(word1, corpus) / len(corpus)
    p_w2 = count_word(word2, corpus) / len(corpus)
    p_w1_w2 = count_cooccurrence(word1, word2, corpus, window=10) / len(corpus)

    # PMI
    pmi = np.log(p_w1_w2 / (p_w1 * p_w2)) if p_w1_w2 > 0 else -np.inf

    # Normalize
    npmi = pmi / -np.log(p_w1_w2) if p_w1_w2 > 0 else 0

    return npmi
```

#### Interpretation

| Coherence Score | Interpretation |
|----------------|----------------|
| > 0.5 | Excellent coherence (words highly related) |
| 0.3 - 0.5 | Good coherence (words moderately related) |
| 0.1 - 0.3 | Fair coherence (some relationship) |
| < 0.1 | Poor coherence (words appear random) |

#### Target

- **v0.1 (MVP)**: Coherence@20 > 0.3 for at least 3/5 dimensions
- **v0.2**: Coherence@20 > 0.4 for all dimensions
- **v0.3**: Coherence@20 > 0.5 for all dimensions

### 2. Counterfactual Consistency

**Definition**: When varying only one dimension, the decoded text should change in a predictable, dimension-appropriate way.

**Purpose**: Verify that dimensions have consistent, interpretable effects.

#### Implementation

```python
def counterfactual_consistency(dimension: int, test_texts: List[str]) -> float:
    """
    Measure consistency of dimension effects.

    Args:
        dimension: Which dimension to test
        test_texts: Sample texts to use

    Returns:
        Consistency score in [0, 1] (higher is better)
    """
    consistency_scores = []

    for text in test_texts:
        # Original encoding
        z_orig = encoder(text)
        orig_decoded = decoder(z_orig)

        # Vary dimension
        consistency_score = 0
        for delta in [-0.5, -0.25, 0.25, 0.5]:
            z_mod = z_orig.copy()
            z_mod[dimension] += delta
            z_mod = np.clip(z_mod, -1, 1)  # Keep in bounds

            mod_decoded = decoder(z_mod)

            # Check if change matches expected semantic shift
            expected_shift = get_expected_shift(dimension, delta)
            actual_shift = measure_semantic_shift(orig_decoded, mod_decoded)

            # Similarity between expected and actual
            similarity = cosine_similarity(expected_shift, actual_shift)
            consistency_score += similarity

        consistency_scores.append(consistency_score / 4)  # Average over deltas

    return np.mean(consistency_scores)

def get_expected_shift(dimension: int, delta: float) -> Dict[str, float]:
    """
    Define expected semantic changes for each dimension.

    Returns dict of semantic properties and expected change magnitudes.
    """
    # Example for dimension 1 (Positive ↔ Negative)
    if dimension == 1:
        return {
            "sentiment": delta,  # Direct effect
            "emotional_intensity": abs(delta),
            "formality": 0,  # No expected effect
            "concreteness": 0
        }
    # Define for other dimensions...

def measure_semantic_shift(text1: str, text2: str) -> Dict[str, float]:
    """
    Measure actual semantic differences between two texts.

    Returns dict of semantic property changes.
    """
    return {
        "sentiment": sentiment_classifier(text2) - sentiment_classifier(text1),
        "emotional_intensity": emotion_intensity(text2) - emotion_intensity(text1),
        "formality": formality_score(text2) - formality_score(text1),
        "concreteness": concreteness_score(text2) - concreteness_score(text1)
    }
```

#### Interpretation

| Consistency Score | Interpretation |
|------------------|----------------|
| > 0.8 | Excellent consistency (predictable changes) |
| 0.6 - 0.8 | Good consistency |
| 0.4 - 0.6 | Fair consistency |
| < 0.4 | Poor consistency (unpredictable effects) |

#### Target

- **v0.1**: Not implemented (rule-based decoder)
- **v0.2**: Consistency > 0.6 for primary dimensions (1, 2, 4)
- **v0.3**: Consistency > 0.7 for all dimensions

### 3. Stability (ARI/NMI)

**Definition**: Consistency of text clusterings across multiple training runs or initializations.

**Purpose**: Verify that learned dimensions are stable, not artifacts of random initialization.

#### Implementation

```python
def measure_stability(texts: List[str], n_runs: int = 5) -> Tuple[float, float]:
    """
    Measure stability using ARI and NMI across multiple runs.

    Args:
        texts: Test texts to cluster
        n_runs: Number of independent runs

    Returns:
        (mean_ari, mean_nmi) across all run pairs
    """
    from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
    from sklearn.cluster import KMeans

    # Encode texts with multiple model initializations
    all_clusterings = []
    for run in range(n_runs):
        # Re-initialize and train model (or load different checkpoint)
        model = train_model_from_scratch(seed=run)

        # Encode and cluster
        vectors = model.encoder(texts)
        kmeans = KMeans(n_clusters=5, random_state=42)
        clusters = kmeans.fit_predict(vectors)

        all_clusterings.append(clusters)

    # Compare all pairs of runs
    ari_scores = []
    nmi_scores = []

    for i in range(n_runs):
        for j in range(i + 1, n_runs):
            ari = adjusted_rand_score(all_clusterings[i], all_clusterings[j])
            nmi = normalized_mutual_info_score(all_clusterings[i], all_clusterings[j])

            ari_scores.append(ari)
            nmi_scores.append(nmi)

    return np.mean(ari_scores), np.mean(nmi_scores)
```

#### Interpretation

| ARI/NMI Score | Interpretation |
|--------------|----------------|
| > 0.8 | Excellent stability (highly consistent) |
| 0.6 - 0.8 | Good stability |
| 0.4 - 0.6 | Fair stability (some variation) |
| < 0.4 | Poor stability (high variance) |

#### Target

- **v0.1**: ARI > 0.95, NMI > 0.95 (deterministic, rule-based)
- **v0.2**: ARI > 0.7, NMI > 0.7 (neural, with fixed seeds)
- **v0.3**: ARI > 0.8, NMI > 0.8 (improved training stability)

### 4. Dimension Purity

**Definition**: Measure whether each dimension captures a single semantic factor.

**Purpose**: Quantify disentanglement at the individual dimension level.

#### Implementation

```python
def dimension_purity(dimension: int, semantic_labels: np.ndarray) -> float:
    """
    Measure how purely a dimension captures one semantic factor.

    Args:
        dimension: Which dimension to evaluate
        semantic_labels: Ground truth labels for semantic factors (N × k)

    Returns:
        Purity score in [0, 1] (higher means more pure)
    """
    # Get vectors for all test examples
    vectors = encoder(test_texts)
    dim_values = vectors[:, dimension]

    # For each semantic factor, compute correlation
    correlations = []
    for factor_idx in range(semantic_labels.shape[1]):
        factor_values = semantic_labels[:, factor_idx]
        corr = np.corrcoef(dim_values, factor_values)[0, 1]
        correlations.append(abs(corr))

    # Purity = max correlation / sum of correlations
    # (ratio of dominant factor to all factors)
    purity = max(correlations) / sum(correlations)
    return purity
```

#### Interpretation

| Purity Score | Interpretation |
|-------------|----------------|
| > 0.7 | High purity (dominated by one factor) |
| 0.5 - 0.7 | Moderate purity |
| 0.3 - 0.5 | Low purity (mixed factors) |
| < 0.3 | Very low purity (entangled) |

## Human Evaluation

### Protocol

**Goal**: Assess whether human annotators find dimension interpretations meaningful and consistent.

#### Setup

1. **Sample Selection**: 50 diverse text examples
2. **Annotators**: 3 independent annotators per example
3. **Task**: Rate dimension interpretability on Likert scale (1-5)

#### Rating Scale

For each dimension, annotators rate:

**Question**: "How well does this dimension capture [semantic property]?"

1. **Strongly Disagree** - Dimension appears random/meaningless
2. **Disagree** - Some patterns but inconsistent
3. **Neutral** - Mixed evidence
4. **Agree** - Generally captures the property well
5. **Strongly Agree** - Clearly and consistently captures the property

#### Instructions for Annotators

```
You will see 50 texts and their vector representations.
For each dimension (0-4), evaluate whether it captures the claimed semantic property:

Dimension 0: Object ↔ Action (grammatical structure)
Dimension 1: Positive ↔ Negative (emotional tone)
Dimension 2: Abstract ↔ Concrete (level of abstraction)
Dimension 3: I ↔ World (point of observation)
Dimension 4: Living ↔ Mechanical (essential nature)

For each example:
1. Read the original text
2. Look at the vector values
3. Compare with similar texts
4. Rate how well each dimension matches its description (1-5)

Consider:
- Are similar texts grouped together by this dimension?
- Does varying this dimension produce expected changes?
- Is the dimension consistent across examples?
```

#### Example Annotation Interface

```
Text: "Собака бежит по парку"
Vector: [-0.5, 0.2, 0.4, 0.1, 0.6]

Dimension 0 (Object ↔ Action):
  Value: -0.5 (Action-oriented)
  How well does this capture grammatical structure?
  [ 1 ] [ 2 ] [ 3 ] [ 4 ] [ 5 ]

Dimension 1 (Positive ↔ Negative):
  Value: 0.2 (Slightly positive)
  How well does this capture emotional tone?
  [ 1 ] [ 2 ] [ 3 ] [ 4 ] [ 5 ]

[Continue for all dimensions...]
```

### Inter-Annotator Agreement

Measure consistency between annotators using **Krippendorff's α**:

```python
def krippendorffs_alpha(ratings: np.ndarray) -> float:
    """
    Compute Krippendorff's α for inter-annotator agreement.

    Args:
        ratings: (n_annotators × n_items) matrix of ratings

    Returns:
        α ∈ [-1, 1], where 1 = perfect agreement, 0 = random
    """
    from krippendorff import alpha
    return alpha(reliability_data=ratings, level_of_measurement='ordinal')
```

#### Interpretation

| α Score | Interpretation |
|---------|----------------|
| > 0.8 | Excellent agreement |
| 0.67 - 0.8 | Good agreement (acceptable) |
| 0.4 - 0.67 | Tentative agreement |
| < 0.4 | Poor agreement (not reliable) |

#### Target

- **v0.1**: Not conducted (MVP)
- **v0.2**: α > 0.6 (acceptable agreement)
- **v0.3**: α > 0.7 (good agreement)

### Analysis and Reporting

#### Per-Dimension Scores

```python
def analyze_human_eval(ratings: np.ndarray) -> pd.DataFrame:
    """
    Analyze human evaluation results.

    Args:
        ratings: (n_examples × n_annotators × n_dimensions) array

    Returns:
        DataFrame with summary statistics per dimension
    """
    results = []

    for dim in range(5):
        dim_ratings = ratings[:, :, dim].flatten()

        results.append({
            'dimension': dim,
            'mean_rating': np.mean(dim_ratings),
            'std_rating': np.std(dim_ratings),
            'median_rating': np.median(dim_ratings),
            'pct_agree': np.mean(dim_ratings >= 4),  # % rated 4 or 5
            'pct_disagree': np.mean(dim_ratings <= 2)  # % rated 1 or 2
        })

    return pd.DataFrame(results)
```

#### Example Report

```
Human Evaluation Results (n=50 examples, 3 annotators)

Dimension 0 (Object ↔ Action):
  Mean: 3.8 ± 0.9
  Agreement rate: 68%
  Krippendorff's α: 0.71
  Interpretation: Good - dimension generally captures structure

Dimension 1 (Positive ↔ Negative):
  Mean: 4.2 ± 0.7
  Agreement rate: 82%
  Krippendorff's α: 0.78
  Interpretation: Excellent - strong sentiment capture

[Continue for all dimensions...]
```

## Composite Interpretability Score

Combine multiple metrics into a single interpretability score:

```python
def compute_interpretability_score(
    coherence_scores: List[float],
    consistency_scores: List[float],
    stability_ari: float,
    human_eval_means: List[float]
) -> float:
    """
    Compute composite interpretability score.

    Weights:
    - 30% Dim-Coherence (average across dimensions)
    - 25% Counterfactual Consistency
    - 20% Stability (ARI)
    - 25% Human Evaluation (average across dimensions)
    """
    # Normalize all scores to [0, 1]
    coherence_norm = np.mean([(c + 1) / 2 for c in coherence_scores])  # NPMI to [0,1]
    consistency_norm = np.mean(consistency_scores)
    stability_norm = stability_ari
    human_norm = np.mean(human_eval_means) / 5  # Likert 1-5 to [0,1]

    # Weighted average
    score = (
        0.30 * coherence_norm +
        0.25 * consistency_norm +
        0.20 * stability_norm +
        0.25 * human_norm
    )

    return score
```

#### Interpretation

| Score | Interpretation |
|-------|----------------|
| > 0.8 | Excellent interpretability |
| 0.7 - 0.8 | Good interpretability |
| 0.6 - 0.7 | Acceptable interpretability |
| < 0.6 | Poor interpretability (needs improvement) |

## Monitoring and Logging

### Continuous Monitoring

Track interpretability metrics over time:

```python
def log_interpretability_metrics(
    version: str,
    metrics: Dict[str, float]
):
    """Log metrics to tracking system (wandb/mlflow)"""
    import wandb  # or mlflow

    wandb.log({
        'version': version,
        'timestamp': datetime.now(),
        **metrics
    })
```

### Regression Detection

Alert if interpretability degrades:

```python
def check_interpretability_regression(
    current_metrics: Dict[str, float],
    baseline_metrics: Dict[str, float],
    threshold: float = 0.1
) -> List[str]:
    """
    Check for significant drops in interpretability.

    Returns list of degraded metrics.
    """
    regressions = []

    for metric_name, current_value in current_metrics.items():
        baseline_value = baseline_metrics.get(metric_name)
        if baseline_value is not None:
            if current_value < baseline_value - threshold:
                regressions.append(
                    f"{metric_name}: {baseline_value:.3f} → {current_value:.3f}"
                )

    return regressions
```

## Reporting Template

### Interpretability Report

```markdown
# Interpretability Report - Atlas v0.X.X

Date: YYYY-MM-DD
Model Version: 0.X.X
Evaluation Dataset: [dataset name, size]

## Automated Metrics

### Dim-Coherence@20
| Dimension | Score | Status |
|-----------|-------|--------|
| 0 (Structure) | 0.45 | ✓ Good |
| 1 (Sentiment) | 0.52 | ✓ Excellent |
| 2 (Abstraction) | 0.38 | ○ Fair |
| 3 (Perspective) | 0.41 | ✓ Good |
| 4 (Animacy) | 0.48 | ✓ Good |

**Average: 0.45** (Target: > 0.40) ✓

### Counterfactual Consistency
| Dimension | Score | Status |
|-----------|-------|--------|
| 0 | 0.68 | ✓ Good |
| 1 | 0.75 | ✓ Good |
| 2 | 0.62 | ○ Fair |
| 3 | 0.71 | ✓ Good |
| 4 | 0.69 | ✓ Good |

**Average: 0.69** (Target: > 0.65) ✓

### Stability
- ARI: 0.82 (Target: > 0.70) ✓
- NMI: 0.79 (Target: > 0.70) ✓

## Human Evaluation

- Participants: 3 annotators
- Examples: 50 texts
- Krippendorff's α: 0.73 (Good agreement) ✓

| Dimension | Mean Rating | Agreement % |
|-----------|------------|-------------|
| 0 | 3.8 ± 0.9 | 68% |
| 1 | 4.2 ± 0.7 | 82% |
| 2 | 3.5 ± 1.1 | 56% |
| 3 | 3.9 ± 0.8 | 72% |
| 4 | 4.0 ± 0.8 | 76% |

## Composite Score

**Overall Interpretability: 0.74** (Good) ✓

## Recommendations

- Dimension 2 (Abstraction) shows lower coherence and human ratings
  → Increase regularization weight for this dimension
  → Add more abstract/concrete pairs to training data

- All other dimensions meet or exceed targets
- Model ready for v0.X release
```

## Tools and Scripts

### Running Metrics

```bash
# Compute all automated metrics
python scripts/evaluate_interpretability.py \
  --model checkpoints/model-v0.2.0.pt \
  --test-data data/test.jsonl \
  --output reports/interp_v0.2.0.json

# Run human evaluation interface
python scripts/human_eval_interface.py \
  --model checkpoints/model-v0.2.0.pt \
  --n-examples 50 \
  --output annotations/human_eval_v0.2.0.json
```

## References

1. **NPMI**: Bouma, G. (2009). "Normalized (Pointwise) Mutual Information in Collocation Extraction"
2. **Topic Coherence**: Röder et al. (2015). "Exploring the Space of Topic Coherence Measures"
3. **Krippendorff's α**: Krippendorff, K. (2011). "Computing Krippendorff's Alpha-Reliability"
4. **Disentanglement Metrics**: Locatello et al. (2019). "Challenging Common Assumptions in Unsupervised Learning of Disentangled Representations"

---

**Document Version**: 1.0
**Last Updated**: 2025-01-19
