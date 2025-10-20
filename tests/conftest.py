# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Pytest configuration and fixtures for Atlas tests.
"""

import pytest

from atlas.api import app as app_module
from atlas.hierarchical import HierarchicalDecoder, HierarchicalEncoder


@pytest.fixture(scope="session", autouse=True)
def initialize_hierarchical():
    """Initialize hierarchical encoder/decoder globally for all tests."""
    # Manually set global variables since TestClient doesn't trigger lifespan
    app_module.hierarchical_encoder = HierarchicalEncoder()
    app_module.hierarchical_decoder = HierarchicalDecoder()
    yield
    # Cleanup
    app_module.hierarchical_encoder = None
    app_module.hierarchical_decoder = None
