# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Hierarchical semantic space encoding/decoding (v0.2 MVP).

Minimal implementation for smoke tests:
- HierarchicalEncoder: text -> 5D vector tree (deterministic)
- HierarchicalDecoder: tree -> reasoning explanations
- manipulate_path: surgical edits on tree nodes
"""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TreeNode:
    """Node in hierarchical 5D semantic tree."""

    value: List[float]
    label: Optional[str] = "coarse"
    key: Optional[str] = None
    children: Optional[List["TreeNode"]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "value": self.value,
            "label": self.label,
            "key": self.key,
            "children": [c.to_dict() for c in (self.children or [])],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TreeNode":
        """Reconstruct from dict."""
        children = None
        if data.get("children"):
            children = [cls.from_dict(c) for c in data["children"]]
        return cls(
            value=data["value"],
            label=data.get("label"),
            key=data.get("key"),
            children=children,
        )


@dataclass
class EncodeHierarchicalRequest:
    """Request for hierarchical encoding."""

    text: str
    max_depth: int = 1
    expand_threshold: float = 0.2


@dataclass
class EncodeHierarchicalResponse:
    """Response from hierarchical encoding."""

    tree: TreeNode
    norm: bool = True
    schema_id: str = "atlas-hier-v0.2"


@dataclass
class ReasonItem:
    """Single reasoning component."""

    path: str
    weight: float
    label: Optional[str] = None
    evidence: Optional[List[str]] = None


@dataclass
class DecodeHierarchicalRequest:
    """Request for hierarchical decoding."""

    tree: TreeNode
    top_k: int = 3


@dataclass
class DecodeHierarchicalResponse:
    """Response from hierarchical decoding."""

    text: str
    reasoning: List[ReasonItem]
    explainable: bool = True


@dataclass
class PathEdit:
    """Single path edit for manipulation."""

    path: str
    value: List[float]


@dataclass
class ManipulateHierarchicalRequest:
    """Request for hierarchical path manipulation."""

    text: str
    edits: List[PathEdit]


@dataclass
class ManipulateHierarchicalResponse:
    """Response from hierarchical path manipulation."""

    original: Dict
    modified: Dict
    trace_id: Optional[str] = None


class HierarchicalEncoder:
    """MVP hierarchical encoder: deterministic text -> 5D tree."""

    def _seed5(self, text: str) -> List[float]:
        """Generate deterministic 5D vector from text (MVP stub).

        Uses text hash to generate reproducible vector, then L2-normalizes.
        """
        if not text:
            text = "atlas"
        h = sum(ord(c) for c in text)
        vals = [((h * (i + 3)) % 200) / 100 - 1 for i in range(5)]

        # L2-normalize to [-1, 1]
        norm = math.sqrt(sum(v * v for v in vals)) or 1.0
        return [v / norm for v in vals]

    def encode_hierarchical(self, text: str, max_depth: int = 1) -> TreeNode:
        """Encode text to hierarchical 5D tree.

        Args:
            text: Input text
            max_depth: Tree depth (0=root only, 1=root+children)

        Returns:
            TreeNode with value, children, etc.
        """
        root = TreeNode(value=self._seed5(text), label="coarse", key="root")

        if max_depth <= 0:
            return root

        # Create 5 children (one per dimension), shifted slightly
        children = []
        for i in range(5):
            child_val = root.value.copy()
            # Shift i-th dimension by ±0.2
            child_val[i] = max(-1.0, min(1.0, child_val[i] * 0.8 + 0.2))

            child = TreeNode(
                value=child_val,
                label=f"fine",
                key=f"dim{i+1}",
            )
            children.append(child)

        root.children = children
        return root


class HierarchicalDecoder:
    """MVP hierarchical decoder: 5D tree -> reasoning explanations."""

    def decode_hierarchical(self, tree: TreeNode, top_k: int = 3) -> Dict:
        """Decode tree to reasoning.

        Args:
            tree: Input TreeNode
            top_k: Number of top dimensions to explain

        Returns:
            Dict with text and reasoning items
        """
        if tree is None:
            return {"text": "ERROR", "reasoning": [], "explainable": False}

        # Generate reasoning items from top dimensions
        reasoning = []
        indexed_vals = [(i, tree.value[i]) for i in range(len(tree.value))]
        indexed_vals.sort(key=lambda x: abs(x[1]), reverse=True)

        for rank, (i, val) in enumerate(indexed_vals[:top_k]):
            reasoning.append(
                ReasonItem(
                    path=f"dim{i+1}",
                    weight=float(val),
                    label=f"dimension_{i+1}",
                    evidence=None,
                )
            )

        return {
            "text": "DECODED_TEXT_MVP",
            "reasoning": reasoning,
            "explainable": True,
        }

    def manipulate_path(self, tree: TreeNode, path: str, value: List[float]) -> TreeNode:
        """Apply surgical edit to tree node at path.

        Args:
            tree: Root node
            path: Node key ("root", "dim1", etc.)
            value: New 5D value

        Returns:
            Modified tree
        """
        if tree is None:
            return tree

        # Edit root
        if path in ("root", "", None):
            tree.value = value
            return tree

        # Edit child by key
        if tree.children:
            for child in tree.children:
                if child.key == path or (child.key and child.key.endswith(path)):
                    child.value = value
                    return tree

        return tree
