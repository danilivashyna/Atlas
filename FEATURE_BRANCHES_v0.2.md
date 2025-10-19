# 🔧 Feature Branches for v0.2.0 Development

Complete roadmap for 8 parallel features. **Create branches in this order**, merge when tests pass.

---

## Feature 1: TextEncoder5D with BERT

**Branch:** `feature/v0.2-01-encoder-bert`

### Goal
Replace MVP `_seed5()` stub with real BERT-based TextEncoder5D using `sentence-transformers`.

### Implementation
- [ ] Lazy load `sentence-transformers/all-MiniLM-L6-v2` tokenizer + model (singleton)
- [ ] `encode(text: str) → List[float]` returns 5D vector, L2-normalized
- [ ] CPU-only inference (torch device="cpu")
- [ ] Graceful fallback to MVP if `transformers` not available
- [ ] Cache embeddings layer (reduce redundant calls)
- [ ] p95 latency < 80ms per request (warm start)
- [ ] Add `requests` example in docstring

### Acceptance
- [ ] `/encode` endpoint stable (no errors)
- [ ] Vector is always 5D, L2-norm ≈ 1.0
- [ ] No NaN/Inf values
- [ ] Handles empty strings gracefully
- [ ] All tests green
- [ ] Benchmarks: p95 < 80ms (warmup 10 requests)

### Tests to Add
```python
def test_encoder_bert_shapes():
    enc = TextEncoder5D()
    v = enc.encode("hello")
    assert len(v) == 5
    assert abs(np.linalg.norm(v) - 1.0) < 0.01

def test_encoder_bert_stability():
    enc = TextEncoder5D()
    v1 = enc.encode("test")
    v2 = enc.encode("test")
    assert np.allclose(v1, v2)

def test_encoder_bert_no_nan():
    enc = TextEncoder5D()
    v = enc.encode("" * 1000)  # edge case
    assert not np.any(np.isnan(v))
    assert not np.any(np.isinf(v))
```

### Performance Target
- Warm start: p50 < 30ms, p95 < 80ms (CPU)
- Memory: < 500MB for model + tokenizer

---

## Feature 2: InterpretableDecoder with Reasoning

**Branch:** `feature/v0.2-02-decoder-transformer`

### Goal
Implement real `InterpretableDecoder.decode(vec5) → (text, reasoning)` using lightweight Transformer head.

### Implementation
- [ ] Build conditioning MLP: `R5 → hidden → vocab_logits`
- [ ] Greedy decode: top-1 token per step, max 20 tokens
- [ ] Extract reasoning from attention weights (top-k dimensions)
- [ ] Fallback to "mvp-reconstructed" if model unavailable
- [ ] Return `DecodeResponse` with:
  - `text`: decoded string
  - `reasoning`: List[PathReasoning] with dimension contributions
  - `explainable`: bool (True if reasoning available)
- [ ] p95 latency < 120ms

### Acceptance
- [ ] `/decode` always returns 200 (graceful fallback)
- [ ] `top_k` parameter respected (1-10 range)
- [ ] Reasoning not empty (at least 1 item)
- [ ] Text never empty (fallback to "mvp")
- [ ] All tests green
- [ ] Round-trip idempotency: same vector → same text

### Tests to Add
```python
def test_decode_always_returns():
    dec = InterpretableDecoder()
    v = np.random.randn(5)
    v /= np.linalg.norm(v)
    result = dec.decode(v, top_k=3)
    assert result["text"]
    assert len(result["reasoning"]) <= 3

def test_decode_top_k_boundaries():
    dec = InterpretableDecoder()
    v = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
    result_k1 = dec.decode(v, top_k=1)
    result_k5 = dec.decode(v, top_k=5)
    assert len(result_k1["reasoning"]) <= 1
    assert len(result_k5["reasoning"]) <= 5
```

### Performance Target
- Warm start: p50 < 50ms, p95 < 120ms
- Memory: < 300MB for lightweight decoder

---

## Feature 3: Hierarchical Router & Operations

**Branch:** `feature/v0.2-03-api-hier-ops`

### Goal
Implement full hierarchical API: `/encode_h`, `/decode_h`, `/manipulate_h` with router weights.

### Implementation
- [ ] HierarchicalEncoder: use TextEncoder5D from #1
- [ ] Router confidence per child: softmax over cosine sims
- [ ] `expand_threshold`: only expand if max child confidence > threshold
- [ ] `/encode_h`: return tree with all nodes normalized
- [ ] `/decode_h`: traverse tree top-down, collect reasoning
- [ ] `/manipulate_h`: surgical edits on specified paths
- [ ] Path format: `"dim1/dim1.3"` (dimension / child index)
- [ ] Validate paths, return 422 on invalid

### Acceptance
- [ ] Depths 0/1/2/3 work without errors
- [ ] Trees are serializable to JSON
- [ ] Path manipulation is reversible (round-trip)
- [ ] All nodes L2-normalized
- [ ] Bad paths → 422 Unprocessable Entity

### Tests to Add
```python
def test_hier_encode_depth_0():
    enc = HierarchicalEncoder(TextEncoder5D())
    tree = enc.encode_hierarchical("test", max_depth=0)
    assert len(tree.children) == 0

def test_hier_encode_expand_threshold():
    enc = HierarchicalEncoder(TextEncoder5D())
    tree1 = enc.encode_hierarchical("test", expand_threshold=0.1)
    tree2 = enc.encode_hierarchical("test", expand_threshold=0.9)
    # tree1 should have more children

def test_manipulate_path_invalid():
    dec = HierarchicalDecoder()
    tree = TreeNode(value=[0.1]*5)
    try:
        dec.manipulate_path(tree, "invalid_path", [0.1]*5)
        assert False
    except ValueError:
        pass
```

---

## Feature 4: Loss Functions for Training

**Branch:** `feature/v0.2-04-losses-hier`

### Goal
Implement training losses: orthogonality, sparsity, router entropy.

### Implementation
- [ ] `ortho_loss(U)`: penalize non-orthogonal columns of 5D projection matrix
- [ ] `l1_sparsity(W)`: L1 norm on router weights (encourage sparse routing)
- [ ] `router_entropy(logits)`: entropy of router softmax (encourage confident routing)
- [ ] `combined_loss = w1*ortho + w2*l1 + w3*entropy`
- [ ] All losses return scalar, differentiable

### Acceptance
- [ ] Gradients non-zero and finite (not NaN/Inf)
- [ ] Losses decrease during synthetic gradient steps
- [ ] Orthogonality loss = 0 for orthonormal matrix
- [ ] Entropy loss = 0 for degenerate (one-hot) distribution

### Tests to Add
```python
def test_ortho_loss_orthonormal():
    U = np.linalg.qr(np.random.randn(5, 5))[0]  # orthonormal
    loss = ortho_loss(torch.tensor(U, dtype=torch.float32))
    assert loss.item() < 0.01

def test_router_entropy_one_hot():
    logits = torch.tensor([[10.0, -10.0, -10.0]], dtype=torch.float32)
    loss = router_entropy(logits)
    assert loss.item() < 0.01

def test_l1_sparsity_all_zeros():
    W = torch.zeros(10, 5)
    loss = l1_sparsity(W)
    assert loss.item() == 0.0
```

---

## Feature 5: Knowledge Distillation from Teacher

**Branch:** `feature/v0.2-05-distill-teacher`

### Goal
Distill from teacher embeddings (1536D e.g., OpenAI) into 5D projection.

### Implementation
- [ ] Teacher encoder API: configurable (e.g., `sentence-transformers/all-mpnet-base-v2`)
- [ ] Linear projection: 1536D → 5D
- [ ] Loss: cosine similarity between teacher and student (after L2 norm)
- [ ] Training script: `scripts/distill_teacher.py` with argparse
- [ ] Example: distill on 100 sentences from `samples/golden_samples.json`
- [ ] Save model checkpoint to `checkpoints/encoder_distilled.pt`

### Acceptance
- [ ] Gradient flow through entire pipeline (no NaN)
- [ ] Loss decreases over 100 steps on synthetic data
- [ ] Inference time stays < 80ms (via TextEncoder5D)

### Tests to Add
```python
def test_distill_gradient_flow():
    teacher = SentenceTransformer(...)
    student = TextEncoder5D()
    optimizer = torch.optim.Adam(student.parameters())

    x = "test sentence"
    teacher_emb = teacher.encode(x)  # 1536D
    student_emb = student.encode(x)  # 5D
    loss = cosine_loss(teacher_emb, student_emb)
    loss.backward()
    assert any(p.grad is not None for p in student.parameters())
```

---

## Feature 6: Metrics (H-Coherence, H-Stability)

**Branch:** `feature/v0.2-06-metrics-hier`

### Goal
Implement interpretability metrics for hierarchical trees.

### Implementation
- [ ] `h_coherence(tree) → float`: NPMI/UMass on top-k terms per node
- [ ] `h_stability(tree1, tree2) → float`: ARI/NMI between two tree routings
- [ ] Range: [0, 1] (higher = better coherence/stability)
- [ ] Docstrings with formulas (NPMI, UMass, ARI, NMI)
- [ ] API endpoint: `GET /metrics` returns sample metrics

### Acceptance
- [ ] Constant tree → h_coherence = 1.0
- [ ] Random tree → h_coherence < 0.5
- [ ] Identical trees → h_stability = 1.0
- [ ] All metrics in [0, 1] range

### Tests to Add
```python
def test_h_coherence_constant_tree():
    # All nodes have identical embeddings
    tree = TreeNode(value=[0.0]*5, children=[...])
    metric = h_coherence(tree)
    assert metric > 0.9

def test_h_stability_identical():
    tree1 = encode_hierarchical("test")
    tree2 = encode_hierarchical("test")
    metric = h_stability(tree1, tree2)
    assert metric > 0.9
```

---

## Feature 7: Benchmarking & Profiling

**Branch:** `feature/v0.2-07-benchmarks`

### Goal
Add performance benchmarks and publish results.

### Implementation
- [ ] `scripts/bench_encode.py`: measure `/encode` latency (p50/p95)
- [ ] `scripts/bench_decode.py`: measure `/decode` latency
- [ ] `scripts/bench_hier.py`: measure hierarchical endpoints
- [ ] Results saved to `benchmarks/last.json`
- [ ] Make target: `make bench` runs all benchmarks
- [ ] CI integration: smoke test for benchmarks (must complete)

### Acceptance
- [ ] Benchmarks complete without errors
- [ ] Results JSON is parseable
- [ ] Latencies tracked over time (for regression detection)

### Tests to Add
```python
def test_bench_encode_latency():
    results = benchmark_encode(n_runs=100)
    assert results["p50_ms"] < 50
    assert results["p95_ms"] < 100

def test_bench_results_format():
    results = benchmark_encode()
    assert "p50_ms" in results
    assert "p95_ms" in results
    assert "memory_mb" in results
```

---

## Feature 8: Documentation, Demos, CLI

**Branch:** `feature/v0.2-08-docs-demos-cli`

### Goal
Add comprehensive docs, CLI interface, and Jupyter demo.

### Implementation
- [ ] CLI: `atlas encode "text"` → print 5D vector
- [ ] CLI: `atlas decode "0.1 0.2 0.3 0.4 0.5"` → print decoded text
- [ ] CLI: `atlas hierarchical encode "text"` → print tree JSON
- [ ] Demo: `examples/demo_hierarchical.ipynb` (Colab-compatible)
- [ ] Docs: `docs/Hierarchical Space.md` with math, examples, formulas
- [ ] Update README with CLI usage examples

### Acceptance
- [ ] CLI smoke: `atlas --help` returns 0
- [ ] CLI encode/decode work end-to-end
- [ ] Notebook runs without errors
- [ ] Docs have code examples and math formulas

### Tests to Add
```python
def test_cli_help():
    result = subprocess.run(["atlas", "--help"], capture_output=True)
    assert result.returncode == 0
    assert "encode" in result.stdout.decode()

def test_cli_encode():
    result = subprocess.run(["atlas", "encode", "test"], capture_output=True)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert len(data["vector"]) == 5
```

---

## 📋 PR Checklist (for All Features)

Before merging each PR:

- [ ] Tests passing (locally: `pytest`, in CI: green check)
- [ ] 0 deprecation warnings (`pytest -W error::DeprecationWarning`)
- [ ] Type hints for all functions (`mypy` passes, optional)
- [ ] Docstrings with examples
- [ ] SPDX license header in new files
- [ ] CHANGELOG.md updated with feature entry
- [ ] README.md links updated
- [ ] Latency benchmarks in PR description (if applicable)

---

## 🚀 Merge Order (Recommended)

1. #v0.2-01 (Encoder) → Foundation
2. #v0.2-02 (Decoder) → Depends on #1
3. #v0.2-03 (Hier-ops) → Depends on #1, #2
4. #v0.2-04 (Losses) → Independent
5. #v0.2-05 (Distill) → Depends on #1
6. #v0.2-06 (Metrics) → Independent
7. #v0.2-07 (Benchmarks) → After #1, #2, #3
8. #v0.2-08 (Docs/Demo) → After all above

---

## ⏱️ Timeline

- **Week 1:** #1, #2, #3 (core features)
- **Week 2:** #4, #5, #6 (losses, distill, metrics)
- **Week 3:** #7, #8 (benchmarks, docs)
- **Week 4:** Integration, polish, v0.2.0-beta release

---

**Status:** Ready to branch! 🔥
