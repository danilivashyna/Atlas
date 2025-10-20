# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Latency benchmarks for Atlas Semantic Space.

Measures encoding and decoding speed for:
- Single text encoding
- Batch text encoding
- Vector decoding
- Hierarchical encoding/decoding
"""

import pytest
import numpy as np
from .conftest import skip_if_no_benchmark


@skip_if_no_benchmark
class TestEncodingLatency:
    """Benchmark encoding latency."""

    def test_encode_single_text(self, benchmark, encoder):
        """Benchmark single text encoding."""
        text = "Собака"
        result = benchmark(encoder.encode_text, text)
        assert isinstance(result, np.ndarray)
        assert result.shape == (5,)

    def test_encode_short_text(self, benchmark, encoder):
        """Benchmark short text encoding (5-10 words)."""
        text = "The quick brown fox jumps"
        result = benchmark(encoder.encode_text, text)
        assert isinstance(result, np.ndarray)
        assert result.shape == (5,)

    def test_encode_medium_text(self, benchmark, encoder):
        """Benchmark medium text encoding (20-30 words)."""
        text = " ".join(["word"] * 25)
        result = benchmark(encoder.encode_text, text)
        assert isinstance(result, np.ndarray)
        assert result.shape == (5,)

    def test_encode_batch_texts(self, benchmark, encoder, sample_texts):
        """Benchmark batch text encoding."""
        result = benchmark(encoder.encode_text, sample_texts)
        assert isinstance(result, np.ndarray)
        assert result.shape == (len(sample_texts), 5)

    def test_encode_large_batch(self, benchmark, encoder):
        """Benchmark large batch encoding (50 texts)."""
        texts = ["Test text"] * 50
        result = benchmark(encoder.encode_text, texts)
        assert isinstance(result, np.ndarray)
        assert result.shape == (50, 5)


@skip_if_no_benchmark
class TestDecodingLatency:
    """Benchmark decoding latency."""

    def test_decode_single_vector(self, benchmark, decoder):
        """Benchmark single vector decoding."""
        vector = np.array([0.1, 0.8, -0.5, 0.2, 0.7])
        result = benchmark(decoder.decode, vector)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_decode_with_reasoning(self, benchmark, decoder):
        """Benchmark decoding with reasoning explanation."""
        vector = np.array([0.1, 0.8, -0.5, 0.2, 0.7])
        result = benchmark(decoder.decode_with_reasoning, vector)
        assert isinstance(result, dict)
        assert 'text' in result
        assert 'reasoning' in result

    def test_decode_multiple_vectors(self, benchmark, decoder, sample_vectors):
        """Benchmark batch vector decoding."""
        def decode_batch():
            return [decoder.decode(v) for v in sample_vectors[:5]]
        
        result = benchmark(decode_batch)
        assert len(result) == 5
        assert all(isinstance(text, str) for text in result)


@skip_if_no_benchmark
class TestHierarchicalLatency:
    """Benchmark hierarchical encoding/decoding latency."""

    def test_hierarchical_encode_depth0(self, benchmark, hierarchical_encoder):
        """Benchmark hierarchical encoding at depth 0."""
        text = "Собака"
        result = benchmark(
            hierarchical_encoder.encode_hierarchical,
            text,
            max_depth=0
        )
        assert result is not None
        assert len(result.value) == 5

    def test_hierarchical_encode_depth1(self, benchmark, hierarchical_encoder):
        """Benchmark hierarchical encoding at depth 1."""
        text = "Собака"
        result = benchmark(
            hierarchical_encoder.encode_hierarchical,
            text,
            max_depth=1
        )
        assert result is not None
        assert len(result.value) == 5

    def test_hierarchical_encode_depth2(self, benchmark, hierarchical_encoder):
        """Benchmark hierarchical encoding at depth 2."""
        text = "Machine learning"
        result = benchmark(
            hierarchical_encoder.encode_hierarchical,
            text,
            max_depth=2
        )
        assert result is not None
        assert len(result.value) == 5

    def test_hierarchical_decode(self, benchmark, hierarchical_encoder, hierarchical_decoder):
        """Benchmark hierarchical decoding."""
        # Pre-encode a tree
        tree = hierarchical_encoder.encode_hierarchical("Собака", max_depth=1)
        
        result = benchmark(
            hierarchical_decoder.decode_hierarchical,
            tree,
            top_k=3,
            with_reasoning=False
        )
        assert 'text' in result

    def test_hierarchical_decode_with_reasoning(
        self, benchmark, hierarchical_encoder, hierarchical_decoder
    ):
        """Benchmark hierarchical decoding with reasoning."""
        tree = hierarchical_encoder.encode_hierarchical("Собака", max_depth=1)
        
        result = benchmark(
            hierarchical_decoder.decode_hierarchical,
            tree,
            top_k=3,
            with_reasoning=True
        )
        assert 'text' in result
        assert 'reasoning' in result

    def test_path_manipulation(self, benchmark, hierarchical_encoder, hierarchical_decoder):
        """Benchmark path manipulation in hierarchical tree."""
        tree = hierarchical_encoder.encode_hierarchical("Собака", max_depth=1)
        new_value = [0.9, 0.8, 0.7, 0.6, 0.5]
        
        result = benchmark(
            hierarchical_decoder.manipulate_path,
            tree,
            "root",
            new_value
        )
        assert result is not None
        assert result.value[0] == 0.9


@skip_if_no_benchmark
class TestRoundtripLatency:
    """Benchmark complete encode-decode roundtrip latency."""

    def test_simple_roundtrip(self, benchmark, encoder, decoder):
        """Benchmark simple encode-decode roundtrip."""
        def roundtrip():
            text = "Собака"
            vector = encoder.encode_text(text)
            decoded = decoder.decode(vector)
            return decoded
        
        result = benchmark(roundtrip)
        assert isinstance(result, str)

    def test_hierarchical_roundtrip(
        self, benchmark, hierarchical_encoder, hierarchical_decoder
    ):
        """Benchmark hierarchical encode-decode roundtrip."""
        def roundtrip():
            text = "Machine learning"
            tree = hierarchical_encoder.encode_hierarchical(text, max_depth=1)
            result = hierarchical_decoder.decode_hierarchical(tree, with_reasoning=False)
            return result['text']
        
        result = benchmark(roundtrip)
        assert isinstance(result, str)
