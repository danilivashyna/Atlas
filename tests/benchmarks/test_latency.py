# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Latency benchmarks for Atlas Semantic Space.

Tests encoder and decoder performance under different conditions.
"""

import pytest
from tests.benchmarks import benchmark_required
from atlas.hierarchical import HierarchicalEncoder, HierarchicalDecoder


@pytest.fixture
def encoder():
    """Fixture providing a hierarchical encoder instance."""
    return HierarchicalEncoder()


@pytest.fixture
def decoder():
    """Fixture providing a hierarchical decoder instance."""
    return HierarchicalDecoder()


@pytest.fixture
def sample_texts():
    """Fixture providing sample texts for benchmarking."""
    return [
        "Собака",
        "Любовь",
        "Машина",
        "Радость",
        "Страх",
        "Дом",
        "Дерево",
        "Жизнь",
        "Свобода",
        "Мир"
    ]


@pytest.mark.benchmark
@benchmark_required
def test_encode_latency_depth_0(benchmark, encoder, sample_texts):
    """
    Benchmark encoding latency at depth 0 (root level only).
    
    Measures the time to encode a single text into a flat 5D vector
    without hierarchical expansion.
    """
    def encode_single():
        return encoder.encode_hierarchical(
            sample_texts[0],
            max_depth=0,
            expand_threshold=0.2
        )
    
    result = benchmark(encode_single)
    assert result is not None
    assert result.value is not None


@pytest.mark.benchmark
@benchmark_required
def test_encode_latency_depth_1(benchmark, encoder, sample_texts):
    """
    Benchmark encoding latency at depth 1 (one level of expansion).
    
    Measures the time to encode with one level of hierarchical expansion,
    where some dimensions may have sub-branches.
    """
    def encode_single():
        return encoder.encode_hierarchical(
            sample_texts[0],
            max_depth=1,
            expand_threshold=0.2
        )
    
    result = benchmark(encode_single)
    assert result is not None
    assert result.value is not None


@pytest.mark.benchmark
@benchmark_required
def test_encode_latency_depth_2(benchmark, encoder, sample_texts):
    """
    Benchmark encoding latency at depth 2 (two levels of expansion).
    
    Measures the time to encode with two levels of hierarchical expansion,
    testing deeper semantic tree construction.
    """
    def encode_single():
        return encoder.encode_hierarchical(
            sample_texts[0],
            max_depth=2,
            expand_threshold=0.2
        )
    
    result = benchmark(encode_single)
    assert result is not None
    assert result.value is not None


@pytest.mark.benchmark
@benchmark_required
def test_decode_latency_simple(benchmark, encoder, decoder, sample_texts):
    """
    Benchmark decoding latency for simple trees.
    
    Measures the time to decode a hierarchical tree back to text
    with basic path reasoning.
    """
    # Pre-encode a tree
    tree = encoder.encode_hierarchical(sample_texts[0], max_depth=1, expand_threshold=0.2)
    
    def decode_single():
        return decoder.decode_hierarchical(tree, top_k=3, with_reasoning=True)
    
    result = benchmark(decode_single)
    assert result is not None
    assert "text" in result


@pytest.mark.benchmark
@benchmark_required
def test_decode_latency_with_reasoning(benchmark, encoder, decoder, sample_texts):
    """
    Benchmark decoding latency with detailed reasoning paths.
    
    Measures the overhead of computing path-wise reasoning explanations
    during decoding.
    """
    # Pre-encode a tree with depth
    tree = encoder.encode_hierarchical(sample_texts[0], max_depth=2, expand_threshold=0.2)
    
    def decode_with_reasoning():
        return decoder.decode_hierarchical(tree, top_k=5, with_reasoning=True)
    
    result = benchmark(decode_with_reasoning)
    assert result is not None
    assert "text" in result
    assert "reasoning" in result


@pytest.mark.benchmark
@benchmark_required
def test_decode_latency_without_reasoning(benchmark, encoder, decoder, sample_texts):
    """
    Benchmark decoding latency without reasoning.
    
    Measures baseline decoding performance when reasoning
    computation is disabled.
    """
    # Pre-encode a tree
    tree = encoder.encode_hierarchical(sample_texts[0], max_depth=1, expand_threshold=0.2)
    
    def decode_without_reasoning():
        return decoder.decode_hierarchical(tree, top_k=3, with_reasoning=False)
    
    result = benchmark(decode_without_reasoning)
    assert result is not None
    assert "text" in result


@pytest.mark.benchmark
@benchmark_required
def test_roundtrip_latency(benchmark, encoder, decoder, sample_texts):
    """
    Benchmark full encode-decode roundtrip latency.
    
    Measures end-to-end performance for a complete cycle:
    text -> tree -> text with reasoning.
    """
    def roundtrip():
        tree = encoder.encode_hierarchical(sample_texts[0], max_depth=1, expand_threshold=0.2)
        return decoder.decode_hierarchical(tree, top_k=3, with_reasoning=True)
    
    result = benchmark(roundtrip)
    assert result is not None
    assert "text" in result


@pytest.mark.benchmark
@benchmark_required
def test_batch_encode_latency(benchmark, encoder, sample_texts):
    """
    Benchmark batch encoding latency.
    
    Measures performance when encoding multiple texts,
    useful for throughput analysis.
    """
    def encode_batch():
        trees = []
        for text in sample_texts[:5]:  # Use first 5 texts
            tree = encoder.encode_hierarchical(text, max_depth=1, expand_threshold=0.2)
            trees.append(tree)
        return trees
    
    result = benchmark(encode_batch)
    assert result is not None
    assert len(result) == 5


@pytest.mark.benchmark
@benchmark_required
def test_varying_threshold_latency(benchmark, encoder, sample_texts):
    """
    Benchmark encoding with different expansion thresholds.
    
    Measures how expansion threshold affects encoding time,
    testing adaptive tree expansion behavior.
    """
    def encode_with_low_threshold():
        return encoder.encode_hierarchical(
            sample_texts[0],
            max_depth=2,
            expand_threshold=0.1  # Lower threshold = more expansion
        )
    
    result = benchmark(encode_with_low_threshold)
    assert result is not None
    assert result.value is not None
