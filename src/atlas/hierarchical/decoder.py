# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Hierarchical Decoder - Decodes hierarchical tree to text with path-wise reasoning
"""

from typing import Any, Dict, List

import numpy as np

from .models import PathReasoning, TreeNode


class HierarchicalDecoder:
    """
    Decoder that reconstructs text from hierarchical tree with path explanations.

    Implements path-wise attention: decoder reads only active branches.
    """

    def __init__(self, base_decoder=None):
        """
        Initialize hierarchical decoder.

        Args:
            base_decoder: Base decoder to use (defaults to SimpleInterpretableDecoder)
        """
        # Use base decoder if provided, otherwise import default
        if base_decoder is None:
            from atlas.decoder import SimpleInterpretableDecoder

            self.base_decoder = SimpleInterpretableDecoder()
        else:
            self.base_decoder = base_decoder

    def decode_hierarchical(
        self, tree: TreeNode, top_k: int = 3, with_reasoning: bool = True
    ) -> Dict[str, Any]:
        """
        Decode hierarchical tree to text with path-wise reasoning.

        Args:
            tree: Hierarchical tree structure
            top_k: Number of top contributing paths to return
            with_reasoning: Whether to include path reasoning

        Returns:
            Dictionary with 'text' and optionally 'reasoning' (list of PathReasoning)
        """
        # Extract all paths and their contributions
        paths = self._extract_paths(tree)

        # Sort by weight and take top_k
        paths.sort(key=lambda x: x["weight"], reverse=True)
        top_paths = paths[:top_k]

        # Decode using weighted combination of path vectors
        combined_vector = self._combine_paths(paths)

        # Use base decoder to get text
        text = self.base_decoder.decode(combined_vector)

        result = {"text": text}

        if with_reasoning:
            # Convert to PathReasoning objects
            reasoning = []
            for path_info in top_paths:
                reasoning.append(
                    PathReasoning(
                        path=path_info["path"],
                        weight=path_info["weight"],
                        label=path_info["label"],
                        evidence=self._extract_evidence(path_info["vector"], text),
                    )
                )
            result["reasoning"] = reasoning

        return result

    def _extract_paths(
        self, node: TreeNode, parent_path: str = "", accumulated_weight: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        Recursively extract all paths from tree with their weights.

        Args:
            node: Current node
            parent_path: Path to parent
            accumulated_weight: Product of weights from root

        Returns:
            List of path dictionaries
        """
        paths = []

        # Current node path
        current_path = parent_path if parent_path == "" else f"{parent_path}/{node.key}"
        if node.key and node.key != "root":
            current_path = node.key if not parent_path else f"{parent_path}/{node.key}"

        # Add current node as a path
        node_weight = (node.weight or 1.0) * accumulated_weight
        paths.append(
            {
                "path": current_path or "root",
                "weight": node_weight,
                "label": node.label or "unknown",
                "vector": np.array(node.value),
            }
        )

        # Recursively extract from children
        if node.children:
            for child in node.children:
                child_paths = self._extract_paths(
                    child, parent_path=current_path or "", accumulated_weight=node_weight
                )
                paths.extend(child_paths)

        return paths

    def _combine_paths(self, paths: List[Dict[str, Any]]) -> np.ndarray:
        """
        Combine multiple path vectors using weighted average.

        Args:
            paths: List of path dictionaries

        Returns:
            Combined vector
        """
        if not paths:
            return np.zeros(5)

        # Weighted sum
        combined = np.zeros(5)
        total_weight = 0.0

        for path_info in paths:
            weight = path_info["weight"]
            vector = path_info["vector"]
            combined += vector * weight
            total_weight += weight

        # Normalize by total weight
        if total_weight > 0:
            combined /= total_weight

        # Clip to valid range
        combined = np.clip(combined, -1.0, 1.0)

        return combined

    def _extract_evidence(self, vector: np.ndarray, text: str) -> List[str]:
        """
        Extract evidence (supporting features) for a vector.

        For MVP, returns simple dimension descriptions.
        In full implementation, this would use attention mechanisms.

        Args:
            vector: Path vector
            text: Decoded text

        Returns:
            List of evidence strings
        """
        from atlas.dimensions import DimensionMapper, SemanticDimension

        mapper = DimensionMapper()
        evidence = []

        # Find most significant dimensions
        abs_values = np.abs(vector)
        top_dims = np.argsort(abs_values)[-2:]  # Top 2 dimensions

        for dim_idx in top_dims:
            dim = SemanticDimension(dim_idx)
            info = mapper.get_dimension_info(dim)
            value = vector[dim_idx]
            interpretation = mapper.interpret_value(dim, value)
            evidence.append(f"{info.name}: {interpretation}")

        return evidence

    def manipulate_path(self, tree: TreeNode, path: str, new_value: List[float]) -> TreeNode:
        """
        Manipulate a specific path in the tree.

        Args:
            tree: Original tree
            path: Path to manipulate (e.g., 'dim2/dim2.4')
            new_value: New 5D value for that path

        Returns:
            Modified tree (copy)
        """
        # Create deep copy of tree
        import copy

        modified_tree = copy.deepcopy(tree)

        # Navigate to the path and update
        self._update_node_at_path(modified_tree, path.split("/"), new_value)

        return modified_tree

    def _update_node_at_path(
        self, node: TreeNode, path_parts: List[str], new_value: List[float]
    ) -> bool:
        """
        Recursively find and update node at path.

        Args:
            node: Current node
            path_parts: Remaining path parts
            new_value: New value to set

        Returns:
            True if updated, False if path not found
        """
        if not path_parts:
            # Reached target node
            node.value = new_value
            return True

        # Check if current node matches first part
        current_part = path_parts[0]
        if node.key == current_part:
            if len(path_parts) == 1:
                # This is the target
                node.value = new_value
                return True
            else:
                # Continue to children
                if node.children:
                    for child in node.children:
                        if self._update_node_at_path(child, path_parts[1:], new_value):
                            return True

        # Try children even if current doesn't match (for root)
        if node.children:
            for child in node.children:
                if self._update_node_at_path(child, path_parts, new_value):
                    return True

        return False
