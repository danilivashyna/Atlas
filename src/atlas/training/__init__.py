# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna
#
# Atlas - Semantic Space Control Panel
# Интерпретируемое семантическое пространство

"""Training subpackage for Atlas v0.2+"""

from .distill import distill_loss
from .losses import orthogonality_loss, l1_sparsity_loss, router_entropy_loss

__all__ = [
    "distill_loss",
    "orthogonality_loss",
    "l1_sparsity_loss",
    "router_entropy_loss",
]
