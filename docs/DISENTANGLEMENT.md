# Disentanglement Methodology

This document explains how Atlas achieves interpretable semantic dimensions through disentanglement techniques.

## Overview

**Goal**: Learn a 5-dimensional semantic space where each dimension captures a distinct, interpretable semantic property.

**Challenge**: Neural networks naturally learn entangled representations where dimensions are correlated and not individually interpretable.

**Solution**: Apply regularization techniques and training objectives that encourage dimensions to become orthogonal and semantically distinct.

## Theoretical Foundation

### What is Disentanglement?

A representation is **disentangled** if:
1. Each dimension captures a single factor of variation
2. Dimensions are independent (orthogonal)
3. Each dimension can be interpreted semantically
4. Changing one dimension doesn't affect others

**Mathematical Definition**:

For a learned representation z = f(x) ∈ ℝ^5:
- **Independence**: p(z) = ∏ᵢ p(zᵢ) (factorized distribution)
- **Orthogonality**: E[zᵢ · zⱼ] ≈ 0 for i ≠ j
- **Interpretability**: Each zᵢ maps to a semantic concept

## Current Implementation (v0.1.0)

**Status**: Rule-based, not learned

The current version uses hand-crafted rules to assign semantic properties:

```python
def encode_text(self, text):
    vector = np.zeros(5)

    # dim₁: Object ↔ Action (based on vowel ratio)
    vowel_ratio = count_vowels(text) / len(text)
    vector[0] = map_to_range(vowel_ratio, 0.3, 0.5)

    # dim₂: Positive ↔ Negative (sentiment)
    sentiment = simple_sentiment(text)
    vector[1] = sentiment

    # ... (other dimensions)

    return normalize(vector)
```

**Limitations**:
- No true disentanglement (no learning)
- Dimensions may be correlated
- Limited to predefined rules

## Planned Neural Implementation (v0.2+)

### Architecture

```
Input: Text (variable length)
    ↓
Encoder: Transformer (BERT-multilingual)
    ↓ (pooling)
Embedding: 768-dim dense vector
    ↓
Projection: Linear(768 → 5)
    ↓
Disentanglement Regularization
    ↓
Output: 5D semantic vector (normalized)
```

### Loss Function

The total loss combines multiple objectives:

```
L_total = L_reconstruction + λ₁·L_orthogonality + λ₂·L_sparsity
          + λ₃·L_tc + λ₄·L_info
```

Where:
- **L_reconstruction**: How well can we decode back to text?
- **L_orthogonality**: Are dimensions independent?
- **L_sparsity**: Are representations sparse?
- **L_tc**: Total correlation (independence measure)
- **L_info**: Information maximization between dims and semantics

## Regularization Techniques

### 1. Orthogonality Constraint

**Goal**: Ensure dimensions are uncorrelated

**Method**: Penalize deviation from identity in the weight matrix

```python
def orthogonality_loss(W):
    """
    Penalize ||W^T W - I||_F^2

    W: weight matrix (5 × 768)
    Returns: scalar loss
    """
    WtW = torch.mm(W.t(), W)  # (5 × 5)
    I = torch.eye(5)
    loss = torch.norm(WtW - I, p='fro')**2
    return loss
```

**Effect**: Forces learned dimensions to be orthogonal in the embedding space

**Weight**: λ₁ = 0.1 (typical value)

### 2. Sparsity Regularization (L1)

**Goal**: Encourage sparse activations (most dims close to 0)

**Method**: L1 penalty on the latent code

```python
def sparsity_loss(z):
    """
    L1 penalty: Σᵢ |zᵢ|

    z: latent code (batch_size × 5)
    Returns: scalar loss
    """
    return torch.mean(torch.abs(z))
```

**Effect**: Each text activates only a few dimensions strongly

**Weight**: λ₂ = 0.01

### 3. Total Correlation (β-TC-VAE)

**Goal**: Minimize statistical dependence between dimensions

**Method**: Based on β-TC-VAE, penalize total correlation

```python
def total_correlation_loss(z):
    """
    TC(z) = KL(p(z) || ∏ᵢ p(zᵢ))

    Approximated using minibatch-weighted sampling
    """
    # Estimate p(z) from batch
    log_qz = estimate_log_density(z)  # Joint distribution

    # Estimate ∏ᵢ p(zᵢ) (product of marginals)
    log_qz_product = sum(
        estimate_log_marginal(z[:, i])
        for i in range(5)
    )

    tc = log_qz - log_qz_product
    return torch.mean(tc)
```

**Effect**: Dimensions become statistically independent

**Weight**: λ₃ = 1.0

**Reference**: [Understanding disentangling in β-VAE (Burgess et al., 2018)](https://arxiv.org/abs/1804.03599)

### 4. InfoNCE / InfoMax

**Goal**: Maximize mutual information between specific dimensions and semantic properties

**Method**: Contrastive learning on labeled semantic properties

```python
def info_max_loss(z, semantic_labels):
    """
    Maximize I(zᵢ; sᵢ) where sᵢ is semantic property i

    z: latent code (batch_size × 5)
    semantic_labels: ground truth properties (batch_size × 5)
    """
    loss = 0
    for dim in range(5):
        # Contrastive loss for dimension i
        positive = z[:, dim]  # Current dimension
        target = semantic_labels[:, dim]  # Target property

        # InfoNCE: positive pairs vs negative pairs
        loss += contrastive_loss(positive, target)

    return loss
```

**Effect**: Each dimension learns to capture its intended semantic property

**Weight**: λ₄ = 0.5

**Requirement**: Need labeled data with semantic annotations

### 5. Counterfactual Regularization

**Goal**: Changing one dimension should have predictable effect on output

**Method**: Generate counterfactual examples and check consistency

```python
def counterfactual_loss(encoder, decoder, x, dim_to_vary):
    """
    Vary dimension i, check that output changes predictably
    """
    z_original = encoder(x)
    loss = 0

    # Sample different values for dimension i
    for new_value in [-1.0, -0.5, 0.0, 0.5, 1.0]:
        z_modified = z_original.clone()
        z_modified[:, dim_to_vary] = new_value

        # Decode both
        x_original_decoded = decoder(z_original)
        x_modified_decoded = decoder(z_modified)

        # Measure difference (should be localized to semantic property i)
        diff = semantic_difference(x_original_decoded, x_modified_decoded)

        # Penalize if difference affects wrong properties
        loss += wrong_properties_changed(diff, dim_to_vary)

    return loss
```

**Effect**: Ensures dimensions have consistent, interpretable effects

**Weight**: Applied during training every N batches

## Training Procedure

### Phase 1: Pretraining (Optional)

Train encoder/decoder without disentanglement:

```python
for epoch in range(pretrain_epochs):
    for batch in dataloader:
        # Standard reconstruction
        z = encoder(batch.text)
        reconstruction = decoder(z)
        loss = reconstruction_loss(reconstruction, batch.text)
        loss.backward()
        optimizer.step()
```

**Goal**: Learn basic semantic representations

**Duration**: 5-10 epochs

### Phase 2: Disentanglement Training

Add regularization gradually:

```python
for epoch in range(main_epochs):
    # Anneal regularization weights
    λ_ortho = min(0.1, epoch * 0.01)
    λ_tc = min(1.0, epoch * 0.1)

    for batch in dataloader:
        z = encoder(batch.text)
        reconstruction = decoder(z)

        # Combined loss
        L_recon = reconstruction_loss(reconstruction, batch.text)
        L_ortho = orthogonality_loss(encoder.projection_weights)
        L_sparse = sparsity_loss(z)
        L_tc_val = total_correlation_loss(z)

        loss = L_recon + λ_ortho*L_ortho + λ_sparse*L_sparse + λ_tc*L_tc_val

        loss.backward()
        optimizer.step()
```

**Annealing**: Gradually increase regularization strength

**Duration**: 20-50 epochs

### Phase 3: Fine-tuning with Semantic Labels

If labeled data available:

```python
for epoch in range(finetune_epochs):
    for batch in labeled_dataloader:
        z = encoder(batch.text)

        # Supervised loss on semantic properties
        L_info = info_max_loss(z, batch.semantic_labels)
        L_counterfactual = counterfactual_loss(encoder, decoder, batch.text, dim_to_vary=random.choice([0,1,2,3,4]))

        loss = L_recon + L_ortho + L_tc + L_info + L_counterfactual

        loss.backward()
        optimizer.step()
```

**Duration**: 5-10 epochs

## Hyperparameters

| Parameter | Symbol | Typical Value | Range |
|-----------|--------|---------------|-------|
| Orthogonality weight | λ₁ | 0.1 | [0.01, 1.0] |
| Sparsity weight | λ₂ | 0.01 | [0.001, 0.1] |
| Total correlation weight | λ₃ | 1.0 | [0.1, 10.0] |
| InfoMax weight | λ₄ | 0.5 | [0.1, 2.0] |
| Learning rate | α | 1e-4 | [1e-5, 1e-3] |
| Batch size | B | 32 | [16, 128] |
| Dimensionality | d | 5 | fixed |

**Finding Good Hyperparameters**:
- Use grid search or Bayesian optimization
- Monitor disentanglement metrics (see below)
- Balance reconstruction quality vs. disentanglement

## Evaluation of Disentanglement

### Quantitative Metrics

#### 1. SAP (Separated Attribute Predictability)

Measure how well individual dimensions predict semantic attributes:

```python
def compute_sap(z, attributes):
    """
    For each attribute, train a classifier on each dimension
    SAP = mean difference between top 2 dimensions
    """
    scores = []
    for attr in attributes:
        dim_scores = []
        for dim in range(5):
            # Train linear classifier: z[:, dim] → attr
            score = train_and_evaluate(z[:, dim], attr)
            dim_scores.append(score)

        # Difference between best and second-best
        dim_scores.sort(reverse=True)
        scores.append(dim_scores[0] - dim_scores[1])

    return np.mean(scores)
```

**Higher is better** (> 0.5 is good)

#### 2. MIG (Mutual Information Gap)

Measure mutual information between dimensions and factors:

```python
def compute_mig(z, factors):
    """
    MIG = mean of (I(zᵢ; fⱼ_max) - I(zᵢ; fⱼ_2nd))
    """
    # Compute I(zᵢ; fⱼ) for all pairs
    mi_matrix = mutual_information_matrix(z, factors)

    # For each factor, find top 2 dimensions
    gaps = []
    for j in range(factors.shape[1]):
        mi_scores = mi_matrix[:, j]
        mi_scores.sort()
        gap = mi_scores[-1] - mi_scores[-2]
        gaps.append(gap / entropy(factors[:, j]))

    return np.mean(gaps)
```

**Range**: [0, 1], higher is better

#### 3. DCI (Disentanglement, Completeness, Informativeness)

Three separate scores:

```python
def compute_dci(z, factors):
    """
    D: Disentanglement (each dim captures one factor)
    C: Completeness (each factor captured by one dim)
    I: Informativeness (how much info retained)
    """
    # Train ensemble of classifiers
    importance_matrix = train_gradient_boosting(z, factors)

    # Disentanglement
    D = 1 - entropy_of_importance(importance_matrix, axis=1).mean()

    # Completeness
    C = 1 - entropy_of_importance(importance_matrix, axis=0).mean()

    # Informativeness
    I = prediction_accuracy(z, factors)

    return D, C, I
```

**All in [0, 1]**, higher is better

### Qualitative Evaluation

#### Dimension Intervention

Manually vary each dimension and observe changes:

```python
def dimension_intervention_demo(text, dim, values):
    """Show how varying dimension affects output"""
    z_base = encoder(text)

    print(f"Original: {text}")
    print(f"Base vector: {z_base}")
    print()

    for val in values:
        z_mod = z_base.clone()
        z_mod[dim] = val
        decoded = decoder(z_mod)
        print(f"dim_{dim}={val:+.1f}: {decoded}")
```

**Example Output**:
```
Original: Собака
Base vector: [-0.5, 0.0, 0.4, 0.0, 0.5]

dim_1=-1.0: Грусть
dim_1=-0.5: Тоска
dim_1= 0.0: Собака
dim_1=+0.5: Радость
dim_1=+1.0: Счастье
```

#### Dimension Clustering

Visualize which texts activate each dimension:

```python
def dimension_clustering(texts):
    """Cluster texts by strongest dimension"""
    vectors = encoder(texts)
    strongest_dim = np.argmax(np.abs(vectors), axis=1)

    for dim in range(5):
        examples = [t for t, d in zip(texts, strongest_dim) if d == dim]
        print(f"Dimension {dim}: {examples[:10]}")
```

## Why 5 Dimensions?

**Choice Rationale**:
1. **Interpretability**: Humans can understand 5-7 concepts simultaneously
2. **Compression**: Forces model to learn essential properties
3. **Visualization**: 5D can be visualized (radar plots, projections)
4. **Empirical**: 5 dimensions sufficient for basic semantic properties

**Trade-offs**:
- **Too few (2-3)**: Insufficient expressiveness, high reconstruction error
- **Too many (10+)**: Harder to interpret, dimensions become entangled
- **5 dimensions**: Sweet spot for interpretability vs. expressiveness

**Future Work**: Adaptive dimensionality based on domain

## Verification of Semantic Meaning

### Intended Dimension Semantics

| Dim | Poles | How to Verify |
|-----|-------|---------------|
| 0 | Object ↔ Action | Nouns cluster at one end, verbs at other |
| 1 | Positive ↔ Negative | Positive words cluster high, negative low |
| 2 | Abstract ↔ Concrete | Abstract concepts vs. physical objects |
| 3 | I ↔ World | First-person references vs. external |
| 4 | Living ↔ Mechanical | Animate beings vs. inanimate objects |

### Verification Tests

For each dimension:

1. **Contrast Set**: Create pairs known to differ on that dimension
   ```python
   contrast_pairs = {
       1: [("любовь", "ненависть"), ("радость", "печаль")],
       4: [("собака", "машина"), ("человек", "робот")]
   }
   ```

2. **Measure Separation**: Verify intended dimension shows largest difference
   ```python
   for dim, pairs in contrast_pairs.items():
       for w1, w2 in pairs:
           z1 = encoder(w1)
           z2 = encoder(w2)
           diff = np.abs(z1 - z2)
           assert np.argmax(diff) == dim, f"Dimension {dim} not most different"
   ```

3. **Semantic Coherence**: Words with similar dimension value should be semantically related
   ```python
   def verify_coherence(dim, threshold=0.1):
       """Check that similar dimension values = similar meanings"""
       texts = load_test_corpus()
       vectors = encoder(texts)

       # Find texts with similar dim value
       for anchor_text, anchor_vec in zip(texts, vectors):
           similar = [t for t, v in zip(texts, vectors)
                     if abs(v[dim] - anchor_vec[dim]) < threshold]

           # Check semantic similarity (manual or automated)
           coherence_score = measure_coherence(anchor_text, similar)
           assert coherence_score > 0.7, f"Low coherence for dim {dim}"
   ```

## Implementation Roadmap

### v0.1 (Current)
- [x] Rule-based encoder/decoder
- [x] 5-dimensional output
- [x] Basic dimension interpretations

### v0.2 (Planned)
- [ ] Neural encoder (BERT-based)
- [ ] Neural decoder (LSTM/Transformer)
- [ ] Orthogonality regularization
- [ ] Basic disentanglement metrics

### v0.3 (Future)
- [ ] Total correlation loss
- [ ] InfoMax with semantic labels
- [ ] Counterfactual regularization
- [ ] Human evaluation of interpretability

### v0.4 (Advanced)
- [ ] Adaptive dimensionality
- [ ] Multi-lingual disentanglement
- [ ] Hierarchical semantic structure
- [ ] Interactive dimension editing

## References

1. **β-VAE**: Higgins et al., "β-VAE: Learning Basic Visual Concepts with a Constrained Variational Framework" (2017)
2. **β-TC-VAE**: Chen et al., "Isolating Sources of Disentanglement in Variational Autoencoders" (2018)
3. **FactorVAE**: Kim & Mnih, "Disentangling by Factorising" (2018)
4. **InfoGAN**: Chen et al., "InfoGAN: Interpretable Representation Learning by Information Maximizing Generative Adversarial Nets" (2016)
5. **Evaluation Metrics**: Locatello et al., "Challenging Common Assumptions in the Unsupervised Learning of Disentangled Representations" (2019)

## Contact

For questions about disentanglement methodology:
- Open a discussion: https://github.com/danilivashyna/Atlas/discussions
- See CONTRIBUTING.md for contribution guidelines

---

**Document Version**: 1.0
**Last Updated**: 2025-01-19
**Status**: Planning document for v0.2+ neural implementations
