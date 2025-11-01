# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Pytest configuration and fixtures for Atlas tests.
"""

import os
import random
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


@pytest.fixture(autouse=True)
def _stable_env(monkeypatch):
    """PR#5.6: Stabilize test environment for deterministic runs."""
    # Disable .pyc to prevent bytecode cache from affecting test order
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    # Fix random seed for reproducibility
    random.seed(1337)


@pytest.fixture
def fab_clean():
    """PR#5.6: Clean FABCore for AIMD/META tests (policy/CB/A/B disabled)."""
    from orbis_fab.core import FABCore
    def _mk(**kw):
        base = dict(policy_enabled=False, z_cb_cooldown_ticks=0, ab_shadow_enabled=False)
        base.update(kw)
        return FABCore(**base)
    return _mk


@pytest.fixture
def fab_zspace():
    """PR#5.6: Z-Space-only FABCore (no A/B, CB, policy interference)."""
    from orbis_fab.core import FABCore
    def _mk(**kw):
        base = dict(
            selector="z-space",
            policy_enabled=False,
            ab_shadow_enabled=False,
            ab_ratio=1.0,
            z_cb_cooldown_ticks=0
        )
        base.update(kw)
        return FABCore(**base)
    return _mk

