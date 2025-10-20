# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Benchmark tests for Atlas Semantic Space.

These tests measure performance characteristics:
- latency: encoding/decoding speed
- reconstruction: quality of encode-decode roundtrips  
- interpretability: reasoning and manipulation speed

Requires pytest-benchmark to be installed. Tests are skipped in CI if not available.
"""
