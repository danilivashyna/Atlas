# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Benchmark tests for Atlas Semantic Space.

These tests require pytest-benchmark to be installed.
They will be skipped in CI if pytest-benchmark is not available.
"""

import pytest

# Check if pytest-benchmark is available
try:
    from pytest_benchmark import plugin  # noqa: F401
    BENCHMARK_AVAILABLE = True
except ImportError:
    BENCHMARK_AVAILABLE = False

# Create a custom marker for benchmarks
benchmark_required = pytest.mark.skipif(
    not BENCHMARK_AVAILABLE,
    reason="pytest-benchmark not installed"
)

# Provide a dummy benchmark fixture if pytest-benchmark is not available
# This allows tests to be collected without errors
if not BENCHMARK_AVAILABLE:
    @pytest.fixture
    def benchmark():
        """Dummy benchmark fixture when pytest-benchmark is not installed."""
        pytest.skip("pytest-benchmark not installed")
