# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna
#
# Atlas - Semantic Space Control Panel
# Интерпретируемое семантическое пространство

"""Training subpackage for Atlas v0.2+"""

from .distill import (
    distill_loss,
    kl_distill_loss,
    combined_distill_loss,
    load_teacher_checkpoint,
    create_curriculum_schedule,
    curriculum_distill_step,
)
from .configs import (
    DistillationConfig,
    DEFAULT_OPENAI_CONFIG,
    CURRICULUM_CONFIG,
    FAST_CONFIG,
)

__all__ = [
    "distill_loss",
    "kl_distill_loss",
    "combined_distill_loss",
    "load_teacher_checkpoint",
    "create_curriculum_schedule",
    "curriculum_distill_step",
    "DistillationConfig",
    "DEFAULT_OPENAI_CONFIG",
    "CURRICULUM_CONFIG",
    "FAST_CONFIG",
]
