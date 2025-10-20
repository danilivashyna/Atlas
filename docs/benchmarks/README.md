# Atlas Benchmarks

Performance and quality benchmarks for the Atlas Semantic Space.

## Overview

The benchmark suite measures three key aspects of the Atlas system:

1. **Latency** (`test_latency.py`): Speed of encoding/decoding operations
2. **Reconstruction** (`test_reconstruction.py`): Quality of semantic preservation
3. **Interpretability** (`test_interpretability.py`): Quality of explanations and reasoning

## Requirements

Benchmarks require `pytest-benchmark` to be installed:

```bash
pip install pytest-benchmark
```

If `pytest-benchmark` is not installed, benchmark tests will be automatically skipped.

## Running Benchmarks

### Run All Benchmarks

```bash
pytest tests/benchmarks/ -v
```

### Run Specific Benchmark Suite

```bash
# Latency benchmarks only
pytest tests/benchmarks/test_latency.py -v

# Reconstruction benchmarks only
pytest tests/benchmarks/test_reconstruction.py -v

# Interpretability benchmarks only
pytest tests/benchmarks/test_interpretability.py -v
```

### Generate Benchmark Report

```bash
# Run with benchmark statistics
pytest tests/benchmarks/ -v --benchmark-only

# Save benchmark results to JSON
pytest tests/benchmarks/ --benchmark-json=output.json

# Compare with previous results
pytest tests/benchmarks/ --benchmark-compare=output.json
```

### Performance Options

```bash
# Increase benchmark rounds for more accurate results
pytest tests/benchmarks/ --benchmark-min-rounds=10

# Set maximum time per benchmark
pytest tests/benchmarks/ --benchmark-max-time=2.0

# Disable garbage collection during benchmarks
pytest tests/benchmarks/ --benchmark-disable-gc

# Show histogram of results
pytest tests/benchmarks/ --benchmark-histogram=histogram
```

## Benchmark Categories

### Latency Benchmarks

Measures operation speed:

- **Encoding latency**: Time to encode single/batch texts
- **Decoding latency**: Time to decode vectors to text
- **Hierarchical latency**: Time for hierarchical encoding/decoding
- **Roundtrip latency**: Complete encode-decode cycles

**Key metrics:**
- Mean execution time (µs/ms)
- Standard deviation
- Min/max times
- Operations per second

### Reconstruction Benchmarks

Measures semantic quality:

- **Encoding consistency**: Determinism and stability
- **Semantic preservation**: Meaning retention through encoding
- **Hierarchical reconstruction**: Tree structure quality
- **Distance preservation**: Metric space properties

**Key metrics:**
- Consistency scores (True/False)
- Distance metrics
- Similarity scores
- Structural validity

### Interpretability Benchmarks

Measures explanation quality:

- **Dimension interpretability**: Reasoning completeness
- **Hierarchical interpretability**: Path extraction quality
- **Manipulation interpretability**: Effect observability
- **Explanation quality**: Consistency and usefulness

**Key metrics:**
- Reasoning coverage (all dimensions)
- Path validity
- Explanation consistency
- Manipulation effects

## CI/CD Integration

In CI environments without `pytest-benchmark`, tests are automatically skipped:

```bash
# Regular test run (benchmarks skipped if no pytest-benchmark)
pytest tests/ -v
```

To explicitly skip benchmarks:

```bash
pytest tests/ -v --ignore=tests/benchmarks/
```

## Sample Output

### Latency Benchmark Output

```
test_encode_single_text
  Mean: 12.5 ms
  StdDev: 0.8 ms
  Min: 11.2 ms
  Max: 15.3 ms
```

### Reconstruction Benchmark Output

```
test_encoding_determinism: PASSED (consistency: True)
test_similar_texts_similar_vectors: PASSED (similarity: 0.75)
test_triangle_inequality: PASSED (valid: True)
```

### Interpretability Benchmark Output

```
test_decode_with_reasoning_completeness: PASSED (all_dims: True)
test_path_extraction_completeness: PASSED (paths_valid: True)
test_explanation_consistency: PASSED (consistent: True)
```

## Understanding Results

### Good Performance Indicators

- **Latency < 50ms** for single operations
- **Latency < 500ms** for batch operations (50 items)
- **Consistency = True** for all reconstruction tests
- **Similarity > 0.5** for related concepts
- **All dimensions covered** in reasoning

### Performance Baselines

Typical expected performance (on modern CPU):

| Operation | Expected Time |
|-----------|--------------|
| Single text encode | 5-20 ms |
| Batch encode (10 texts) | 30-100 ms |
| Single vector decode | 1-5 ms |
| Hierarchical encode (depth=1) | 10-30 ms |
| Hierarchical decode | 5-15 ms |
| Path manipulation | 1-5 ms |

## Troubleshooting

### Benchmarks Not Running

If you see "pytest-benchmark not installed", install it:

```bash
pip install pytest-benchmark
```

### Slow Benchmarks

To speed up benchmark runs:

```bash
# Reduce rounds
pytest tests/benchmarks/ --benchmark-min-rounds=1

# Skip warmup
pytest tests/benchmarks/ --benchmark-warmup=off
```

### Memory Issues

For large batch benchmarks:

```bash
# Run benchmarks serially
pytest tests/benchmarks/ -n 0
```

## Contributing

When adding new benchmarks:

1. Use `@skip_if_no_benchmark` decorator
2. Follow naming convention: `test_<feature>_<aspect>`
3. Include assertions to verify correctness
4. Document expected performance in comments
5. Group related benchmarks in classes

Example:

```python
from .conftest import skip_if_no_benchmark

@skip_if_no_benchmark
class TestNewFeature:
    """Benchmark new feature."""
    
    def test_feature_speed(self, benchmark):
        """Benchmark feature execution speed."""
        result = benchmark(my_function)
        assert result is not None  # Verify correctness
```

## References

- [pytest-benchmark documentation](https://pytest-benchmark.readthedocs.io/)
- [Atlas Documentation](../../DOCUMENTATION.md)
- [Performance Tuning Guide](../../docs/NFR.md)
