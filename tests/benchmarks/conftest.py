# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Pytest configuration for benchmark tests.
"""

import pytest

# Check if pytest-benchmark is available by trying to import the plugin
try:
    from pytest_benchmark import plugin  # noqa: F401
    BENCHMARK_AVAILABLE = True
except ImportError:
    BENCHMARK_AVAILABLE = False


# When pytest-benchmark is not available, we need to skip all benchmark tests
# by providing a dummy benchmark fixture that raises skip
@pytest.fixture
def benchmark(request):
    """
    Benchmark fixture that either uses pytest-benchmark or skips the test.
    
    When pytest-benchmark is not installed, this fixture will skip the test.
    When it is installed, pytest-benchmark will override this fixture.
    """
    if not BENCHMARK_AVAILABLE:
        pytest.skip("pytest-benchmark not installed")
    # If BENCHMARK_AVAILABLE is True, pytest-benchmark should provide the real fixture
    # This code path should not be reached
    raise RuntimeError("pytest-benchmark is installed but fixture not found")
