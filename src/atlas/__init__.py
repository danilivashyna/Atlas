# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Atlas - Semantic Space Control Panel

A 5-dimensional interface between abstract meaning and concrete form.
Atlas doesn't just visualize vectors - it shows how meaning moves through space.
"""

__version__ = "0.1.0"

from .dimensions import DimensionMapper, SemanticDimension
from .encoder import SimpleSemanticEncoder
from .decoder import SimpleInterpretableDecoder
from .space import SemanticSpace

__all__ = [
    "SemanticSpace",
    "SimpleSemanticEncoder",
    "SimpleInterpretableDecoder",
    "DimensionMapper",
    "SemanticDimension",
]

# Optional imports
try:
    from .encoder import SemanticEncoder

    __all__.append("SemanticEncoder")
except ImportError:
    pass

try:
    from .decoder import InterpretableDecoder

    __all__.append("InterpretableDecoder")
except ImportError:
    pass
