# [WIP] feat(encoder): TextEncoder5D with BERT integration

## Goal
Replace MVP `_seed5()` stub with real BERT-based TextEncoder5D using `sentence-transformers/all-MiniLM-L6-v2`.

## Changes
- [x] Created `src/atlas/encoders/` module with TextEncoder5D class
- [x] Added BERT model lazy loading (singleton) with CPU-only inference
- [x] Implemented 5D projection from 384D MiniLM embeddings
- [x] Added comprehensive unit tests (12 tests)
- [x] Added sentence-transformers to requirements.txt
- [x] Fallback to MVP encoding if transformers unavailable

## Implementation Details

### TextEncoder5D Class
- **Input**: Text string
- **Output**: 5D float list (L2-normalized)
- **Model**: `sentence-transformers/all-MiniLM-L6-v2` (384D embeddings)
- **Projection**: 384D → 5D via deterministic dimensionality reduction
- **Caching**: LRU-style in-memory cache for repeated queries
- **Lazy Loading**: Model loaded on first `encode()` call
- **Fallback**: MVP deterministic encoding if BERT unavailable

### Dimensionality Reduction
Current approach (placeholder, can be improved):
- Divide 384D embeddings into 5 groups
- Take mean of each group → 5D vector
- Production approach: Train PCA or linear projection matrix

### Performance Target
- p50 latency: < 30ms (CPU, warm start)
- p95 latency: < 80ms (CPU, warm start)
- Memory: < 500MB (model + tokenizer)

## Tests
- 12 unit tests covering:
  - 5D output shape validation
  - L2-normalization checks
  - Determinism (same text → same vector)
  - Different text divergence
  - Edge cases (empty, very long, unicode)
  - NaN/Inf validation
  - Caching behavior
  - Performance benchmarks (marked as `@pytest.mark.slow`)

## Status
- [x] Code complete (skeleton + full impl)
- [x] Tests written and passing
- [ ] Benchmarks verified (need warmup data)
- [ ] Integration with `/encode` endpoint
- [ ] Documentation updated
- [ ] Code review ready

## Breaking Changes
None - fully backward compatible with MVP.

## Related Issue
#v0.2-01-encoder-bert

## Checklist
- [ ] Pydantic v2 compatible (ConfigDict)
- [ ] No deprecation warnings
- [ ] SPDX headers on all files
- [ ] Type hints complete
- [ ] Docstrings with examples
- [ ] All tests passing locally
- [ ] CI green (GitHub Actions)
- [ ] CHANGELOG.md updated
- [ ] README.md examples added
