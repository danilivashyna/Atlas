# Atlas Benchmarks

This directory contains benchmark tests for the Atlas Semantic Space project. Benchmarks measure performance, reconstruction quality, and interpretability across different components and configurations.

## Overview

The benchmark suite includes three main categories:

1. **Latency Benchmarks** (`test_latency.py`) - Measure encoding, decoding, and roundtrip performance
2. **Reconstruction Benchmarks** (`test_reconstruction.py`) - Evaluate encode-decode quality and semantic fidelity
3. **Interpretability Benchmarks** (`test_interpretability.py`) - Assess explanation quality and reasoning completeness

## Prerequisites

Benchmarks require `pytest-benchmark` to be installed:

```bash
pip install pytest-benchmark
```

The benchmarks are designed to be **skipped automatically** in CI/CD environments where `pytest-benchmark` is not installed. This means regular tests will continue to pass even without the benchmark package.

## Running Benchmarks

### Run All Benchmarks

```bash
# Run all benchmark tests
pytest tests/benchmarks/ --benchmark-only

# Run with verbose output
pytest tests/benchmarks/ --benchmark-only -v

# Save benchmark results to a file
pytest tests/benchmarks/ --benchmark-only --benchmark-json=benchmark_results.json
```

### Run Specific Benchmark Categories

```bash
# Run only latency benchmarks
pytest tests/benchmarks/test_latency.py --benchmark-only

# Run only reconstruction benchmarks
pytest tests/benchmarks/test_reconstruction.py --benchmark-only

# Run only interpretability benchmarks
pytest tests/benchmarks/test_interpretability.py --benchmark-only
```

### Run Specific Benchmark Tests

```bash
# Run a specific test
pytest tests/benchmarks/test_latency.py::test_encode_latency_depth_0 --benchmark-only

# Run tests matching a pattern
pytest tests/benchmarks/ -k "depth_1" --benchmark-only
```

## Benchmark Options

`pytest-benchmark` provides many useful options:

```bash
# Compare with previous benchmark results
pytest tests/benchmarks/ --benchmark-only --benchmark-compare

# Save a baseline for future comparisons
pytest tests/benchmarks/ --benchmark-only --benchmark-save=baseline

# Generate a histogram
pytest tests/benchmarks/ --benchmark-only --benchmark-histogram=histogram

# Adjust calibration (number of warmup runs)
pytest tests/benchmarks/ --benchmark-only --benchmark-warmup=on --benchmark-warmup-iterations=10

# Disable garbage collection during benchmarks for more stable results
pytest tests/benchmarks/ --benchmark-only --benchmark-disable-gc

# Set minimum rounds and time
pytest tests/benchmarks/ --benchmark-only --benchmark-min-rounds=5 --benchmark-min-time=0.1
```

## Understanding Results

Benchmark results include several statistics:

- **Min**: Fastest execution time
- **Max**: Slowest execution time
- **Mean**: Average execution time
- **StdDev**: Standard deviation (consistency measure)
- **Median**: Middle value when sorted
- **IQR**: Interquartile range (spread of middle 50%)
- **Outliers**: Number of outliers detected
- **Rounds**: Number of times the test was run

Example output:
```
test_encode_latency_depth_0 (0001_baseline)
------------------------------------------------ benchmark: 1 tests ------------------------------------------------
Name (time in ms)                     Min       Max      Mean  StdDev    Median     IQR  Outliers     OPS  Rounds
--------------------------------------------------------------------------------------------------------------------
test_encode_latency_depth_0       5.2341    6.1234    5.4567  0.1234    5.4321  0.0891       2;2  183.22      20
--------------------------------------------------------------------------------------------------------------------
```

## Benchmark Categories

### 1. Latency Benchmarks

Measures performance characteristics:

- **Encoding at different depths** (0, 1, 2) - How tree depth affects encoding time
- **Decoding with/without reasoning** - Overhead of generating explanations
- **Roundtrip performance** - Full encode-decode cycle timing
- **Batch operations** - Throughput for multiple texts
- **Threshold variations** - Impact of expansion threshold on performance

**Key Metrics:**
- P50/P95 latency for SLA monitoring
- Throughput (operations per second)
- Impact of configuration parameters

### 2. Reconstruction Benchmarks

Evaluates quality of encode-decode cycles:

- **Accuracy at different depths** - How well text is reconstructed
- **Consistency** - Whether multiple runs produce identical results
- **Semantic similarity** - Cosine similarity between original and reconstructed embeddings
- **Manipulation effects** - How semantic edits affect reconstruction
- **Batch quality** - Average quality across diverse texts

**Key Metrics:**
- Cosine similarity scores
- Consistency rate (determinism)
- Preservation rate (concept retention)

### 3. Interpretability Benchmarks

Assesses explanation quality:

- **Reasoning path generation** - Performance of creating explanations
- **Path completeness** - How complete and informative paths are
- **Dimension interpretations** - Quality of semantic dimension descriptions
- **Explanation consistency** - Determinism of explanations
- **Top-k coverage** - How well top paths explain the output

**Key Metrics:**
- Number of reasoning paths generated
- Completeness rate of explanations
- Informativeness (explanation length/detail)
- Consistency across runs

## Integration with CI/CD

The benchmarks automatically skip when `pytest-benchmark` is not installed:

```python
# Tests are marked with @benchmark_required
# This automatically skips if pytest-benchmark is missing
@pytest.mark.benchmark
@benchmark_required
def test_encode_latency_depth_0(benchmark, encoder, sample_texts):
    # Test implementation
    pass
```

In CI environments without pytest-benchmark:
```bash
$ pytest tests/
...
tests/benchmarks/test_latency.py::test_encode_latency_depth_0 SKIPPED (pytest-benchmark not installed)
...
```

Regular tests continue to pass, while benchmark tests are skipped gracefully.

## Best Practices

1. **Warm-up your system**: Run benchmarks multiple times; the first run may be slower
2. **Minimize background processes**: Close unnecessary applications
3. **Use consistent hardware**: Compare results only on the same machine
4. **Save baselines**: Track performance over time with `--benchmark-save`
5. **Compare carefully**: Use `--benchmark-compare` to detect regressions
6. **Document changes**: When making optimizations, document expected improvements

## Performance Targets

Current performance targets (subject to change):

- **Encoding (depth=1)**: < 10ms per text (P95)
- **Decoding**: < 5ms per tree (P95)
- **Roundtrip**: < 15ms total (P95)
- **Reconstruction similarity**: > 0.5 cosine similarity
- **Explanation completeness**: > 90% of paths complete

## Troubleshooting

### Benchmarks are skipped

If benchmarks are being skipped, install pytest-benchmark:
```bash
pip install pytest-benchmark
```

### Results are inconsistent

Try:
- Running more rounds: `--benchmark-min-rounds=10`
- Disabling GC: `--benchmark-disable-gc`
- Increasing warmup: `--benchmark-warmup-iterations=10`

### Benchmarks are too slow

Reduce the number of rounds:
```bash
pytest tests/benchmarks/ --benchmark-only --benchmark-min-rounds=3
```

## Contributing

When adding new benchmarks:

1. Follow the existing structure (latency/reconstruction/interpretability)
2. Always use the `@benchmark_required` decorator
3. Mark tests with `@pytest.mark.benchmark`
4. Include docstrings explaining what is being measured
5. Add assertions to validate results
6. Update this README with the new benchmark description

## Further Reading

- [pytest-benchmark documentation](https://pytest-benchmark.readthedocs.io/)
- [Atlas Hierarchical Implementation](../HIERARCHICAL_IMPLEMENTATION.md)
- [Atlas Interpretability Metrics](../INTERPRETABILITY_METRICS.md)
