# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Pytest configuration for benchmark tests.
"""

import pytest

# Check if pytest-benchmark is available
pytest_benchmark_available = False
try:
    import pytest_benchmark
    pytest_benchmark_available = True
except ImportError:
    pass

# Skip marker for tests requiring pytest-benchmark
skip_if_no_benchmark = pytest.mark.skipif(
    not pytest_benchmark_available,
    reason="pytest-benchmark not installed"
)


@pytest.fixture(scope="module")
def encoder():
    """Create encoder instance for benchmarks."""
    from atlas.encoder import SimpleSemanticEncoder
    return SimpleSemanticEncoder()


@pytest.fixture(scope="module")
def decoder():
    """Create decoder instance for benchmarks."""
    from atlas.decoder import SimpleInterpretableDecoder
    return SimpleInterpretableDecoder()


@pytest.fixture(scope="module")
def hierarchical_encoder():
    """Create hierarchical encoder for benchmarks."""
    from atlas.hierarchical import HierarchicalEncoder
    return HierarchicalEncoder()


@pytest.fixture(scope="module")
def hierarchical_decoder():
    """Create hierarchical decoder for benchmarks."""
    from atlas.hierarchical import HierarchicalDecoder
    return HierarchicalDecoder()


@pytest.fixture(scope="module")
def sample_texts():
    """Sample texts in multiple languages for benchmarking."""
    return [
        "Собака",
        "Любовь",
        "Машина",
        "Жизнь",
        "Страх",
        "The quick brown fox jumps over the lazy dog",
        "Machine learning is transforming technology",
        "Natural language processing enables understanding",
        "Deep neural networks learn patterns",
        "Semantic spaces represent meaning",
    ]


@pytest.fixture(scope="module")
def sample_vectors(encoder, sample_texts):
    """Pre-encoded vectors for benchmarking decode operations."""
    import numpy as np
    return [encoder.encode_text(text) for text in sample_texts]
