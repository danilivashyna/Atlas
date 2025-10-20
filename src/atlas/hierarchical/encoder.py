# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Hierarchical Encoder - Encodes text into hierarchical tree structure

Implements a gating-tree (Mixture-of-Experts style) where each parent node
routes attention to 5 child nodes, with dynamic depth expansion.
"""

from typing import List, Optional, Union

import numpy as np

from .models import TreeNode


class HierarchicalEncoder:
    """
    Encoder that compresses text into hierarchical 5D semantic tree.

    Architecture:
    - Level 0: 5 "main handles" (coarse semantics)
    - Level 1+: Each handle has 5 sub-dimensions (fine semantics)
    - Dynamic depth: Expands lazily based on router confidence
    """

    def __init__(self, base_encoder=None, dimension: int = 5):
        """
        Initialize hierarchical encoder.

        Args:
            base_encoder: Base encoder to use (defaults to SimpleSemanticEncoder)
            dimension: Number of dimensions per level (default: 5)
        """
        self.dimension = dimension

        # Use base encoder if provided, otherwise import default
        if base_encoder is None:
            from atlas.encoder import SimpleSemanticEncoder

            self.base_encoder = SimpleSemanticEncoder()
        else:
            self.base_encoder = base_encoder

    def encode_hierarchical(
        self, text: Union[str, List[str]], max_depth: int = 1, expand_threshold: float = 0.2
    ) -> TreeNode:
        """
        Encode text into hierarchical tree structure.

        Args:
            text: Input text or list of texts
            max_depth: Maximum depth to expand (0 = root only)
            expand_threshold: Confidence threshold for expanding children

        Returns:
            TreeNode with hierarchical structure
        """
        if isinstance(text, list):
            # For now, handle single text; batch support can be added later
            text = text[0] if text else ""

        # Encode at root level using base encoder
        root_vector = self.base_encoder.encode_text(text)

        # Create root node
        root = TreeNode(
            value=root_vector.tolist(), label="coarse", key="root", weight=1.0, children=None
        )

        # Expand children if max_depth > 0
        if max_depth > 0:
            root.children = self._expand_children(
                root_vector,
                text,
                current_depth=0,
                max_depth=max_depth,
                expand_threshold=expand_threshold,
                parent_key="root",
            )

        return root

    def _expand_children(
        self,
        parent_vector: np.ndarray,
        text: str,
        current_depth: int,
        max_depth: int,
        expand_threshold: float,
        parent_key: str,
    ) -> Optional[List[TreeNode]]:
        """
        Recursively expand children nodes.

        Args:
            parent_vector: Parent node's vector
            text: Original text (for context)
            current_depth: Current depth in tree
            max_depth: Maximum depth to expand
            expand_threshold: Threshold for expansion
            parent_key: Parent node's key

        Returns:
            List of 5 child nodes or None if not expanded
        """
        if current_depth >= max_depth:
            return None

        # Calculate router weights (confidence for each dimension)
        router_weights = self._compute_router_weights(parent_vector)

        # Check if we should expand (at least one dimension above threshold)
        if np.max(router_weights) < expand_threshold:
            return None

        children = []
        for i in range(self.dimension):
            # Generate child vector using local perturbation
            child_vector = self._generate_child_vector(
                parent_vector, dimension_index=i, router_weight=router_weights[i]
            )

            # Create child key
            child_key = f"{parent_key}/dim{i+1}" if parent_key != "root" else f"dim{i+1}"

            # Create child node
            child = TreeNode(
                value=child_vector.tolist(),
                label=self._get_dimension_label(i, child_vector),
                key=child_key,
                weight=float(router_weights[i]),
                children=None,
            )

            # Recursively expand if weight is high enough
            if router_weights[i] >= expand_threshold and current_depth + 1 < max_depth:
                child.children = self._expand_children(
                    child_vector,
                    text,
                    current_depth=current_depth + 1,
                    max_depth=max_depth,
                    expand_threshold=expand_threshold,
                    parent_key=child_key,
                )

            children.append(child)

        return children

    def _compute_router_weights(self, vector: np.ndarray) -> np.ndarray:
        """
        Compute router weights for each dimension.

        For MVP, use simple heuristic based on absolute values.
        In full implementation, this would be a learned gating network.

        Args:
            vector: Parent vector

        Returns:
            Router weights (confidence) for each dimension
        """
        # Use absolute values as proxy for importance
        abs_values = np.abs(vector)

        # Normalize to [0, 1] range using softmax-like approach
        # Add small epsilon to avoid division by zero
        weights = abs_values / (np.sum(abs_values) + 1e-8)

        return weights

    def _generate_child_vector(
        self, parent_vector: np.ndarray, dimension_index: int, router_weight: float
    ) -> np.ndarray:
        """
        Generate child vector for a specific dimension.

        For MVP, use local perturbation around parent.
        In full implementation, this would be a learned MLP/Transformer head.

        Args:
            parent_vector: Parent's 5D vector
            dimension_index: Which dimension to focus on (0-4)
            router_weight: Router confidence for this dimension

        Returns:
            Child's 5D vector
        """
        # Start with parent vector
        child = parent_vector.copy()

        # Add local perturbation focused on specific dimension
        # The perturbation is stronger for dimensions with higher parent values
        perturbation = np.random.randn(self.dimension) * 0.1 * router_weight

        # Emphasize the focused dimension
        perturbation[dimension_index] *= 2.0

        # Add perturbation and clip to valid range
        child = child + perturbation
        child = np.clip(child, -1.0, 1.0)

        return child

    def _get_dimension_label(self, dimension_index: int, vector: np.ndarray) -> str:
        """
        Get semantic label for a dimension based on its vector.

        Args:
            dimension_index: Dimension index (0-4)
            vector: Child vector

        Returns:
            Human-readable label
        """
        # Import dimension mapper for labels
        from atlas.dimensions import DimensionMapper, SemanticDimension

        mapper = DimensionMapper()
        dim = SemanticDimension(dimension_index)
        info = mapper.get_dimension_info(dim)

        # Get interpretation for the specific value
        value = vector[dimension_index]
        interpretation = mapper.interpret_value(dim, value)

        return f"{info.name} ({interpretation})"

    def flatten_tree(self, tree: TreeNode) -> np.ndarray:
        """
        Flatten hierarchical tree to a single vector.

        This allows compatibility with flat vector operations.

        Args:
            tree: Hierarchical tree

        Returns:
            Flattened vector (weighted combination of all nodes)
        """
        # Start with root vector
        flat = np.array(tree.value) * (tree.weight or 1.0)

        # Add weighted contributions from children
        if tree.children:
            for child in tree.children:
                child_flat = self.flatten_tree(child)
                flat += child_flat * (child.weight or 0.0)

        # Normalize
        flat = np.clip(flat, -1.0, 1.0)

        return flat
