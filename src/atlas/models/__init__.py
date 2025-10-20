# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna
#
# Atlas - Semantic Space Control Panel
# Интерпретируемое семантическое пространство

"""Models subpackage for Atlas v0.2+"""

from .encoder_bert import BertEncoderConfig, TextEncoder5D

__all__ = ["TextEncoder5D", "BertEncoderConfig"]
