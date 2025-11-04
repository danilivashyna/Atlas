"""
Tests for AURIS Phase C Canary Gate (orbis_self.canary_exp).

Validates:
- Environment variable parsing (AURIS_SELF, AURIS_SELF_CANARY)
- Sampling logic (0%, 5%, 25%, 100%)
- Edge cases (negative, >1.0, invalid strings)
- Thread safety (not explicit, but random.random() is thread-safe)

Phase: C (experimental)
"""

import os
import pytest


def test_canary_disabled_by_default(monkeypatch):
    """AURIS_SELF=off → should_activate_self() always False."""
    monkeypatch.delenv("AURIS_SELF", raising=False)
    monkeypatch.delenv("AURIS_SELF_CANARY", raising=False)

    # Force reimport to reset global config
    import importlib
    import orbis_self.canary_exp

    importlib.reload(orbis_self.canary_exp)

    from orbis_self.canary_exp import should_activate_self

    # 100 samples should all be False
    assert all(not should_activate_self() for _ in range(100))


def test_canary_enabled_zero_percent(monkeypatch):
    """AURIS_SELF=on but CANARY=0.0 → always False."""
    monkeypatch.setenv("AURIS_SELF", "on")
    monkeypatch.setenv("AURIS_SELF_CANARY", "0.0")

    import importlib
    import orbis_self.canary_exp

    importlib.reload(orbis_self.canary_exp)

    from orbis_self.canary_exp import should_activate_self

    assert all(not should_activate_self() for _ in range(100))


def test_canary_full_activation(monkeypatch):
    """AURIS_SELF=on, CANARY=1.0 → always True."""
    monkeypatch.setenv("AURIS_SELF", "on")
    monkeypatch.setenv("AURIS_SELF_CANARY", "1.0")

    import importlib
    import orbis_self.canary_exp

    importlib.reload(orbis_self.canary_exp)

    from orbis_self.canary_exp import should_activate_self

    assert all(should_activate_self() for _ in range(100))


def test_canary_5_percent_sampling(monkeypatch):
    """AURIS_SELF=on, CANARY=0.05 → ~5% True (with margin)."""
    monkeypatch.setenv("AURIS_SELF", "on")
    monkeypatch.setenv("AURIS_SELF_CANARY", "0.05")

    import importlib
    import orbis_self.canary_exp

    importlib.reload(orbis_self.canary_exp)

    from orbis_self.canary_exp import should_activate_self

    # Sample 1000 calls
    activations = sum(should_activate_self() for _ in range(1000))
    rate = activations / 1000

    # Allow 2-8% (50% margin for randomness)
    assert 0.02 <= rate <= 0.08, f"Expected ~5%, got {rate:.1%}"


def test_canary_25_percent_sampling(monkeypatch):
    """AURIS_SELF=on, CANARY=0.25 → ~25% True."""
    monkeypatch.setenv("AURIS_SELF", "on")
    monkeypatch.setenv("AURIS_SELF_CANARY", "0.25")

    import importlib
    import orbis_self.canary_exp

    importlib.reload(orbis_self.canary_exp)

    from orbis_self.canary_exp import should_activate_self

    activations = sum(should_activate_self() for _ in range(1000))
    rate = activations / 1000

    # Allow 20-30% range
    assert 0.20 <= rate <= 0.30, f"Expected ~25%, got {rate:.1%}"


def test_canary_clamping_negative(monkeypatch):
    """CANARY=-0.5 → clamped to 0.0 (always False)."""
    monkeypatch.setenv("AURIS_SELF", "on")
    monkeypatch.setenv("AURIS_SELF_CANARY", "-0.5")

    import importlib
    import orbis_self.canary_exp

    importlib.reload(orbis_self.canary_exp)

    from orbis_self.canary_exp import should_activate_self, get_canary_percentage

    assert get_canary_percentage() == 0.0
    assert all(not should_activate_self() for _ in range(100))


def test_canary_clamping_above_one(monkeypatch):
    """CANARY=1.5 → clamped to 1.0 (always True)."""
    monkeypatch.setenv("AURIS_SELF", "on")
    monkeypatch.setenv("AURIS_SELF_CANARY", "1.5")

    import importlib
    import orbis_self.canary_exp

    importlib.reload(orbis_self.canary_exp)

    from orbis_self.canary_exp import should_activate_self, get_canary_percentage

    assert get_canary_percentage() == 1.0
    assert all(should_activate_self() for _ in range(100))


def test_canary_invalid_string_defaults_to_5_percent(monkeypatch):
    """CANARY='invalid' → defaults to 0.05 (5%)."""
    monkeypatch.setenv("AURIS_SELF", "on")
    monkeypatch.setenv("AURIS_SELF_CANARY", "not-a-number")

    import importlib
    import orbis_self.canary_exp

    importlib.reload(orbis_self.canary_exp)

    from orbis_self.canary_exp import get_canary_percentage

    # Should default to 5% on parse error
    assert get_canary_percentage() == 0.05


def test_canary_config_repr(monkeypatch):
    """CanaryConfig.__repr__() includes status and percentage."""
    monkeypatch.setenv("AURIS_SELF", "on")
    monkeypatch.setenv("AURIS_SELF_CANARY", "0.25")

    import importlib
    import orbis_self.canary_exp

    importlib.reload(orbis_self.canary_exp)

    from orbis_self.canary_exp import get_config

    config = get_config()
    repr_str = repr(config)

    assert "enabled" in repr_str
    assert "25" in repr_str or "0.25" in repr_str


def test_canary_status_helpers(monkeypatch):
    """is_canary_enabled(), canary_status(), canary_sampling_rate()."""
    monkeypatch.setenv("AURIS_SELF", "on")
    monkeypatch.setenv("AURIS_SELF_CANARY", "0.05")

    import importlib
    import orbis_self.canary_exp

    importlib.reload(orbis_self.canary_exp)

    from orbis_self.canary_exp import (
        is_canary_enabled,
        canary_status,
        canary_sampling_rate,
    )

    assert is_canary_enabled() is True
    assert "canary" in canary_status().lower()
    assert "5" in canary_status()  # "5%" in status string
    assert canary_sampling_rate() == 0.05


def test_canary_disabled_status(monkeypatch):
    """AURIS_SELF=off → status shows disabled."""
    monkeypatch.setenv("AURIS_SELF", "off")

    import importlib
    import orbis_self.canary_exp

    importlib.reload(orbis_self.canary_exp)

    from orbis_self.canary_exp import (
        is_canary_enabled,
        canary_status,
        canary_sampling_rate,
    )

    assert is_canary_enabled() is False
    assert "disabled" in canary_status().lower()
    assert canary_sampling_rate() == 0.0


def test_canary_fail_closed_on_exception(monkeypatch):
    """If random.random() raises exception, should_activate_self() → False."""
    monkeypatch.setenv("AURIS_SELF", "on")
    monkeypatch.setenv("AURIS_SELF_CANARY", "0.5")

    import importlib
    import orbis_self.canary_exp

    importlib.reload(orbis_self.canary_exp)

    # Patch random.random to raise exception
    import random

    def broken_random():
        raise RuntimeError("Simulated random failure")

    original_random = random.random
    random.random = broken_random

    from orbis_self.canary_exp import should_activate_self

    try:
        # Should fail closed (return False on exception)
        assert should_activate_self() is False
    finally:
        # Restore original random.random
        random.random = original_random
