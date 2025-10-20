# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Hierarchical Semantic Space - Matryoshka 5D Architecture

This module implements a hierarchical semantic space where each dimension
can recursively have child dimensions, forming a tree structure.
"""

from .decoder import HierarchicalDecoder
from .encoder import HierarchicalEncoder
from .models import (
    DecodeHierarchicalRequest,
    DecodeHierarchicalResponse,
    EncodeHierarchicalRequest,
    EncodeHierarchicalResponse,
    HierarchicalVector,
    ManipulateHierarchicalRequest,
    ManipulateHierarchicalResponse,
    PathEdit,
    PathReasoning,
    TreeNode,
)

__all__ = [
    "TreeNode",
    "HierarchicalVector",
    "EncodeHierarchicalRequest",
    "EncodeHierarchicalResponse",
    "DecodeHierarchicalRequest",
    "DecodeHierarchicalResponse",
    "ManipulateHierarchicalRequest",
    "ManipulateHierarchicalResponse",
    "PathReasoning",
    "PathEdit",
    "HierarchicalEncoder",
    "HierarchicalDecoder",
]
