# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna
#
# Atlas - Semantic Space Control Panel
# Интерпретируемое семантическое пространство

"""Training subpackage for Atlas v0.2+"""

from .distill import distill_loss

__all__ = ["distill_loss"]
