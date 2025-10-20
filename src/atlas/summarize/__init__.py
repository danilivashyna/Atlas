# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Atlas Summarization Module

Length-controlled summarization that preserves 5D semantic ratios.
"""

from .proportional import summarize

__all__ = ["summarize"]
