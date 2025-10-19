# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

# v0.2 Development: GitHub Issues Templates

## Issue #v0.2-01: Neural Encoder (BERT→5D)

**Title:** Implement BERT-based 5D encoder with L2 normalization

**Description:**
Implement `TextEncoder5D` class that converts text to 5D semantic vectors using BERT backbone (all-MiniLM-L6-v2).

**Acceptance Criteria:**
- [ ] Implement `TextEncoder5D` in `src/atlas/models/encoder_bert.py`
  - Input: text string
  - Output: List[float] of 5 values in [-1, 1]
- [ ] Add L2 normalization: `||v||_2 = 1`
- [ ] Support optional orthogonal projection matrix
- [ ] Add unit tests: `tests/test_encoder_bert.py`
  - Test basic encoding
  - Test L2 norm preservation
  - Test batch encoding
- [ ] Add docstring examples
- [ ] Achieve >80% coverage

**Related Files:**
- `src/atlas/models/encoder_bert.py` (main)
- `tests/test_encoder_bert.py` (tests)
- `src/atlas/models/__init__.py` (export)

**Labels:** feature, neural-components, priority-1

---

## Issue #v0.2-02: Interpretable Transformer Decoder

**Title:** Implement Transformer decoder with reasoning explanations

**Description:**
Implement `InterpretableDecoder` that takes 5D vectors and generates interpretable reasoning for each dimension.

**Acceptance Criteria:**
- [ ] Implement `InterpretableDecoder` in `src/atlas/models/decoder_transformer.py`
  - Input: (B, 5) tensor of 5D vectors
  - Output: (B, 5) tensor of explanations + logits
- [ ] Add Transformer architecture with positional encoding
- [ ] Generate reasoning strings for each dimension
- [ ] Add unit tests: `tests/test_decoder_transformer.py`
  - Test forward pass
  - Test reasoning generation
  - Test edge cases
- [ ] Add docstring examples
- [ ] Achieve >80% coverage

**Related Files:**
- `src/atlas/models/decoder_transformer.py` (main)
- `tests/test_decoder_transformer.py` (tests)

**Labels:** feature, neural-components, priority-1

---

## Issue #v0.2-03: Hierarchical API (encode_h, decode_h, manipulate_h)

**Title:** Implement hierarchical REST API endpoints

**Description:**
Implement three core REST endpoints for hierarchical 5D space:
- `POST /encode_h`: Text → hierarchical tree of 5D vectors
- `POST /decode_h`: Tree → interpretable text + reasoning
- `POST /manipulate_h`: Surgical manipulation of dimensions

**Acceptance Criteria:**
- [ ] Implement `POST /encode_h` endpoint
  - Accept text, max_depth, expand_threshold
  - Return tree, norm, schema_id
- [ ] Implement `POST /decode_h` endpoint
  - Accept tree, top_k
  - Return text, reasoning[]
- [ ] Implement `POST /manipulate_h` endpoint
  - Accept text, edits[]
  - Return original, modified, changes[]
- [ ] Add Pydantic models in `src/atlas/api/models.py`
- [ ] Add integration tests: `tests/test_api_hierarchical.py`
- [ ] Generate OpenAPI docs
- [ ] Achieve >80% endpoint coverage

**Related Files:**
- `src/atlas/api/app.py` (endpoints)
- `src/atlas/api/models.py` (schemas)
- `tests/test_api_hierarchical.py` (tests)
- `docs/HIERARCHICAL_SCHEMA_v0.2.md` (schema)

**Labels:** feature, api, priority-1

---

## Issue #v0.2-04: Hierarchical Loss Functions

**Title:** Implement ortho_loss, l1_sparsity, router_entropy

**Description:**
Implement three regularization losses for training hierarchical encoders:
- Orthogonal projection loss: ||W^T W - I||_F
- L1 sparsity loss: mean(|x|)
- Router entropy loss: -mean(sum(p*log(p)))

**Acceptance Criteria:**
- [ ] Implement all three loss functions in `src/atlas/models/losses_hier.py`
- [ ] Add docstrings with mathematical formulas
- [ ] Add unit tests: `tests/test_losses_hier.py`
  - Test ortho_loss preserves orthogonality
  - Test l1_sparsity encourages sparsity
  - Test router_entropy prevents collapse
- [ ] Add type hints and error handling
- [ ] Verify gradient computation

**Related Files:**
- `src/atlas/models/losses_hier.py` (main)
- `tests/test_losses_hier.py` (tests)

**Labels:** feature, training, priority-1

---

## Issue #v0.2-05: Knowledge Distillation

**Title:** Implement teacher→student distillation for 5D encoders

**Description:**
Implement knowledge distillation losses for transferring from large teacher models (e.g., OpenAI embeddings 1536D) to student 5D encoders.

**Acceptance Criteria:**
- [ ] Implement `distill_loss()` using cosine similarity
- [ ] Implement `kl_distill_loss()` for routing probabilities
- [ ] Implement `combined_distill_loss()` with alpha weighting
- [ ] Add unit tests: `tests/test_distill.py`
- [ ] Verify with smoke inference on toy data
- [ ] Add docstrings with examples

**Related Files:**
- `src/atlas/training/distill.py` (main)
- `tests/test_distill.py` (tests)

**Labels:** feature, training, priority-2

---

## Issue #v0.2-06: Hierarchical Metrics Implementation

**Title:** Implement H-Coherence and H-Stability metrics

**Description:**
Replace stub implementations of metrics with real algorithms:
- H-Coherence: Measure sibling semantic similarity (target ≥0.85)
- H-Stability: Measure robustness to perturbations (target ≥0.80)

**Acceptance Criteria:**
- [ ] Implement `h_coherence()` in `src/atlas/metrics/metrics_hier.py`
  - Compute NPMI scores between sibling nodes
- [ ] Implement `h_stability()` in `src/atlas/metrics/metrics_hier.py`
  - Use ARI/NMI on tree structures with perturbations
- [ ] Add unit tests: `tests/test_metrics_hier.py`
- [ ] Add benchmarking script: `scripts/benchmark_metrics.py`
- [ ] Document target ranges in docstrings

**Related Files:**
- `src/atlas/metrics/metrics_hier.py` (main)
- `tests/test_metrics_hier.py` (tests)
- `scripts/benchmark_metrics.py` (benchmark)

**Labels:** feature, metrics, priority-2

---

## Issue #v0.2-07: Documentation & Examples

**Title:** Add hierarchical space guide + CLI/cURL examples

**Description:**
Comprehensive documentation on hierarchical 5D space, inference patterns, and debugging.

**Acceptance Criteria:**
- [ ] Write guide in `docs/HIERARCHICAL_SPACE.md`
  - Explain 5 dimensions
  - Show tree expansion strategy
  - Discuss interpretability benefits
- [ ] Add CLI examples: `atlas encode`, `atlas decode`, `atlas manipulate`
- [ ] Add cURL examples for all three endpoints
- [ ] Add Python integration examples in Jupyter notebook
- [ ] Update README.md with v0.2 link

**Related Files:**
- `docs/HIERARCHICAL_SPACE.md` (new)
- `docs/HIERARCHICAL_SCHEMA_v0.2.md` (new)
- `README.md` (update)
- `examples/hierarchical_demo.py` (new)

**Labels:** documentation, priority-2

---

## Issue #v0.2-08: CI/CD Smoke Tests & Caching

**Title:** Set up GitHub Actions for inference smoke tests

**Description:**
Add GitHub Actions workflow for continuous integration:
- Syntax checks (py_compile)
- Unit test suite (pytest)
- Smoke inference on sample texts
- Cache torch/transformers models

**Acceptance Criteria:**
- [ ] Create `.github/workflows/test.yml`
  - Run on push to main/PR
  - Cache transformers models
  - Report coverage
- [ ] Add `smoke_inference.py` script
- [ ] Ensure <5min total CI time
- [ ] Add badge to README

**Related Files:**
- `.github/workflows/test.yml` (new)
- `scripts/smoke_inference.py` (new)
- `README.md` (add badge)

**Labels:** devops, ci-cd, priority-2

---

## Development Workflow

### Step 1: Assign Issue
```bash
# One contributor claims the issue
# Add label "in-progress"
```

### Step 2: Create Feature Branch
```bash
git checkout -b feature/v0.2-01-encoder-bert
```

### Step 3: Implement & Test Locally
```bash
make dev
make test
make lint
```

### Step 4: Create Pull Request
- Link to issue: "Closes #v0.2-01"
- Add description from issue checklist
- Request review

### Step 5: Review & Merge
```bash
# After review approval + CI pass
git merge --squash
```

---

## Priority Matrix

### Priority 1 (Complete by EOW)
- #v0.2-01: Neural Encoder
- #v0.2-02: Interpretable Decoder
- #v0.2-03: Hierarchical API
- #v0.2-04: Loss Functions

### Priority 2 (Complete by Week 2)
- #v0.2-05: Distillation
- #v0.2-06: Metrics
- #v0.2-07: Documentation
- #v0.2-08: CI/CD

---

## Success Criteria for v0.2-beta

- [ ] All 8 issues completed
- [ ] >80% test coverage
- [ ] All endpoints documented with cURL examples
- [ ] CI/CD passing
- [ ] AGPL + Commercial licensing in place
- [ ] CLA signed by all contributors
