"""
Z-Space Shim - Thin adapter for FAB integration

Provides deterministic node selection from Z-Space slices without tight coupling.
Compatible with existing FAB infrastructure (score-based selection in Phase 1).

Design:
- Stateless functions (no class state pollution)
- Deterministic (same seed → same selection)
- Budget-aware (respects stream/global caps)
- Minimal API surface (single entry point)

Future:
- Phase 2: Vec-based MMR diversity (replace score ranking)
- Phase 3: Edge-aware selection (graph structure)
"""

import random
from typing import Optional

from .contracts import ZSliceLite


class ZSpaceShim:
    """
    Thin adapter layer between FAB and Z-Space slice representation.
    
    Phase 1: Score-based selection (compatible with existing FAB)
    Phase 2: Vec-based MMR diversity (future enhancement)
    
    All methods are stateless - no instance state required.
    """
    
    @staticmethod
    def select_topk_for_stream(
        z: ZSliceLite,
        k: int,
        rng: Optional[random.Random] = None
    ) -> list[str]:
        """
        Select top-k node IDs for stream from Z-Space slice.
        
        Phase 1 (current): Score-based ranking with deterministic tie-breaking.
        Phase 2 (future): Vec-based MMR diversity on embeddings.
        
        Args:
            z: Z-Space slice with nodes, edges, quotas
            k: Number of nodes to select (stream budget)
            rng: Optional seeded RNG for deterministic tie-breaking.
                 If None, uses z.seed for reproducibility.
        
        Returns:
            List of node IDs (length ≤ k, deterministic order)
        
        Determinism guarantee:
            Same z.seed + same k → identical node IDs in identical order
        
        Example:
            >>> z_slice = {
            ...     "nodes": [
            ...         {"id": "n1", "score": 0.95},
            ...         {"id": "n2", "score": 0.87},
            ...         {"id": "n3", "score": 0.92}
            ...     ],
            ...     "seed": "test-123",
            ...     # ... other fields
            ... }
            >>> ZSpaceShim.select_topk_for_stream(z_slice, k=2)
            ['n1', 'n3']  # Top-2 by score, deterministic
        """
        nodes = z["nodes"]
        
        # Empty or zero budget edge case
        if not nodes or k <= 0:
            return []
        
        # Initialize RNG for deterministic tie-breaking
        if rng is None:
            rng = random.Random(z["seed"])
        
        # Phase 1: Score-based selection (compatible with existing FAB)
        # Sort by score descending, then by ID for deterministic tie-breaking
        sorted_nodes = sorted(
            nodes,
            key=lambda n: (-n["score"], n["id"])  # Deterministic sort
        )
        
        # Take top-k (respecting budget)
        selected = sorted_nodes[:k]
        
        # Return IDs only (FAB expects list[str])
        return [node["id"] for node in selected]
    
    @staticmethod
    def select_topk_for_global(
        z: ZSliceLite,
        k: int,
        exclude_ids: set[str],
        rng: Optional[random.Random] = None
    ) -> list[str]:
        """
        Select top-k node IDs for global pool (excluding stream nodes).
        
        Phase 1: Score-based ranking with deterministic tie-breaking.
        
        Args:
            z: Z-Space slice with nodes
            k: Number of nodes to select (global budget)
            exclude_ids: Node IDs already in stream (to exclude)
            rng: Optional seeded RNG for tie-breaking
        
        Returns:
            List of node IDs (length ≤ k, no overlap with exclude_ids)
        
        Example:
            >>> z_slice = {"nodes": [...], "seed": "test"}
            >>> stream_ids = ZSpaceShim.select_topk_for_stream(z_slice, k=2)
            >>> global_ids = ZSpaceShim.select_topk_for_global(
            ...     z_slice, k=3, exclude_ids=set(stream_ids)
            ... )
            >>> assert set(global_ids) & set(stream_ids) == set()  # No overlap
        """
        nodes = z["nodes"]
        
        if not nodes or k <= 0:
            return []
        
        # Initialize RNG
        if rng is None:
            rng = random.Random(z["seed"])
        
        # Filter out stream nodes
        candidates = [n for n in nodes if n["id"] not in exclude_ids]
        
        if not candidates:
            return []
        
        # Phase 1: Score-based selection
        sorted_candidates = sorted(
            candidates,
            key=lambda n: (-n["score"], n["id"])  # Deterministic
        )
        
        # Take top-k from remaining candidates
        selected = sorted_candidates[:k]
        
        return [node["id"] for node in selected]
    
    @staticmethod
    def validate_slice(z: ZSliceLite) -> tuple[bool, str]:
        """
        Validate Z-Space slice structure and constraints.
        
        Checks:
        - Required fields present (nodes, edges, quotas, seed, zv)
        - Nodes have valid scores [0.0, 1.0]
        - No duplicate node IDs
        - Edges reference existing nodes
        
        Args:
            z: Z-Space slice to validate
        
        Returns:
            (is_valid, error_message)
            - (True, "") if valid
            - (False, "error description") if invalid
        
        Example:
            >>> z_slice = {...}
            >>> valid, error = ZSpaceShim.validate_slice(z_slice)
            >>> if not valid:
            ...     raise ValueError(f"Invalid Z-slice: {error}")
        """
        # Check required fields
        required_fields = {"nodes", "edges", "quotas", "seed", "zv"}
        missing = required_fields - set(z.keys())
        if missing:
            return False, f"Missing required fields: {missing}"
        
        # Check nodes structure
        nodes = z["nodes"]
        if not isinstance(nodes, list):
            return False, "nodes must be a list"
        
        # Validate node scores and collect IDs
        node_ids = set()
        for i, node in enumerate(nodes):
            if "id" not in node or "score" not in node:
                return False, f"Node {i} missing 'id' or 'score'"
            
            node_id = node["id"]
            if node_id in node_ids:
                return False, f"Duplicate node ID: {node_id}"
            node_ids.add(node_id)
            
            score = node["score"]
            if not (0.0 <= score <= 1.0):
                return False, f"Node {node_id} score {score} out of range [0.0, 1.0]"
        
        # Validate edges reference existing nodes
        edges = z["edges"]
        if not isinstance(edges, list):
            return False, "edges must be a list"
        
        for i, edge in enumerate(edges):
            if "src" not in edge or "dst" not in edge:
                return False, f"Edge {i} missing 'src' or 'dst'"
            
            src, dst = edge["src"], edge["dst"]
            if src not in node_ids:
                return False, f"Edge {i} references unknown src: {src}"
            if dst not in node_ids:
                return False, f"Edge {i} references unknown dst: {dst}"
        
        # Validate quotas
        quotas = z["quotas"]
        required_quotas = {"tokens", "nodes", "edges", "time_ms"}
        missing_quotas = required_quotas - set(quotas.keys())
        if missing_quotas:
            return False, f"Missing quota fields: {missing_quotas}"
        
        # All checks passed
        return True, ""
