"""
# SPDX-License-Identifier: AGPL-3.0-or-later

Encoder implementations for Atlas.

- TextEncoder5D: BERT-based text encoder producing 5D vectors
- Other encoders as needed
"""

from .text_encoder_5d import TextEncoder5D

__all__ = ["TextEncoder5D"]
