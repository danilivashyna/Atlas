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
from math import sqrt
from typing import Optional, Sequence, List, Dict, Any

from .contracts import ZSliceLite


# ---- Vec utilities (Phase 2 / PR#4: Vec-MMR) ----

def _vec_norm(vec: Sequence[float]) -> float:
    """Calculate L2 norm of vector."""
    return sqrt(sum(v * v for v in vec)) if vec else 0.0


def _cosine_sim(a: Sequence[float], b: Sequence[float], na: float, nb: float) -> float:
    """
    Calculate cosine similarity between two vectors with precomputed norms.
    
    Args:
        a, b: Input vectors
        na, nb: Precomputed L2 norms of a and b
        
    Returns:
        Cosine similarity [0.0, 1.0], or 0.0 if either norm is zero
    """
    if not a or not b or na == 0.0 or nb == 0.0:
        return 0.0
    dot = 0.0
    L = min(len(a), len(b))
    for i in range(L):
        dot += a[i] * b[i]
    return dot / (na * nb)


def _mmr_greedy(
    candidates: List[Dict[str, Any]],
    k: int,
    lambda_diversity: float,
    rng
) -> List[str]:
    """
    Greedy MMR with cosine diversity and deterministic tie-breaks.
    
    MMR formula: score = λ * relevance + (1-λ) * diversity
    where diversity = 1 - max_cosine_sim_to_selected
    
    Args:
        candidates: Nodes with id, score, optional vec
        k: Number of nodes to select
        lambda_diversity: Weight for relevance vs diversity (0.7 = 70% relevance)
        rng: Random number generator (unused, kept for API compatibility)
        
    Returns:
        List of selected node IDs
        
    Fallback:
        If no vectors present, falls back to pure score-sort with id tie-breaks
    """
    if k <= 0 or not candidates:
        return []
    
    # Check for vec presence
    with_vec = [n for n in candidates if isinstance(n.get("vec"), (list, tuple)) and n.get("vec") and len(n.get("vec")) > 0]
    
    # Fallback: no vectors → pure score-sort
    if len(with_vec) == 0:
        ordered = [
            (n.get("id"), float(n.get("score", 0.0))) 
            for n in candidates 
            if n.get("id") is not None  # Filter out nodes without IDs
        ]
        ordered.sort(key=lambda p: (-p[1], p[0]))  # Deterministic: score desc, id asc
        return [str(i) for i, _ in ordered[:k]]  # Ensure str type for IDs
    
    # Precompute norms for all nodes with vectors
    norms: Dict[str, float] = {}
    for n in with_vec:
        vid = n.get("id")
        if vid is not None:  # Guard against None IDs
            norms[str(vid)] = _vec_norm(n.get("vec"))
    
    # Initialize: select first node (highest score, deterministic tie-break)
    ordered = sorted(with_vec, key=lambda n: (-float(n.get("score", 0.0)), str(n.get("id"))))
    selected: List[Dict[str, Any]] = []
    selected_ids: List[str] = []
    
    if ordered:
        first = ordered[0]
        selected.append(first)
        selected_ids.append(first.get("id"))
    
    remaining = [n for n in ordered if not selected_ids or n.get("id") != selected_ids[0]]
    
    # Greedy MMR iterations
    while len(selected_ids) < k and remaining:
        best_node = None
        best_score = float("-inf")
        
        for cand in remaining:
            c_score = float(cand.get("score", 0.0))
            c_id = cand.get("id")
            c_vec = cand.get("vec")
            nc = norms.get(c_id, _vec_norm(c_vec))
            
            # Max similarity to selected set
            max_sim = 0.0
            for s in selected:
                ns = norms.get(s.get("id"), _vec_norm(s.get("vec")))
                sim = _cosine_sim(c_vec, s.get("vec"), nc, ns)
                if sim > max_sim:
                    max_sim = sim
            
            # MMR value: λ * relevance + (1-λ) * diversity
            diversity_term = 1.0 - max_sim
            mmr_value = lambda_diversity * c_score + (1.0 - lambda_diversity) * diversity_term
            
            # Deterministic tie-break: if scores within epsilon, choose by id
            if mmr_value > best_score + 1e-12:
                best_score = mmr_value
                best_node = cand
            elif abs(mmr_value - best_score) <= 1e-12:
                if best_node is None or str(cand.get("id")) < str(best_node.get("id")):
                    best_node = cand
        
        if best_node is None:
            break
        
        selected.append(best_node)
        selected_ids.append(best_node.get("id"))
        remaining = [n for n in remaining if n.get("id") != best_node.get("id")]
    
    # Fill remaining slots with non-vec nodes (score-sorted)
    if len(selected_ids) < k:
        without_vec = [n for n in candidates if not (isinstance(n.get("vec"), (list, tuple)) and len(n.get("vec")) > 0)]
        rest_sorted = sorted(
            [(n.get("id"), float(n.get("score", 0.0))) for n in without_vec if n.get("id") not in selected_ids],
            key=lambda p: (-p[1], p[0])
        )
        for nid, _ in rest_sorted:
            selected_ids.append(nid)
            if len(selected_ids) >= k:
                break
    
    return selected_ids


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
        
        PR#4: Vec-based MMR diversity with cosine similarity (when vecs present).
        Fallback: Score-based ranking with deterministic tie-breaking (no vecs).
        
        Args:
            z: Z-Space slice with nodes, edges, quotas
            k: Number of nodes to select (stream budget)
            rng: Optional seeded RNG for deterministic tie-breaking.
                 If None, uses z.seed for reproducibility.
        
        Returns:
            List of node IDs (length ≤ k, deterministic order)
        
        Determinism guarantee:
            Same z.seed + same k → identical node IDs in identical order
            
        Vec-MMR behavior (PR#4):
            - If any node has vec field: use cosine MMR (λ=0.7)
            - Deterministic tie-breaks by node id (always)
            - No vecs: pure score-sort fallback
        
        Example:
            >>> z_slice = {
            ...     "nodes": [
            ...         {"id": "n1", "score": 0.95, "vec": [1.0, 0.0]},
            ...         {"id": "n2", "score": 0.87, "vec": [0.0, 1.0]},
            ...         {"id": "n3", "score": 0.92, "vec": [0.9, 0.1]}
            ...     ],
            ...     "seed": "test-123",
            ...     "quotas": {"nodes": 3}
            ... }
            >>> ZSpaceShim.select_topk_for_stream(z_slice, k=2)
            ['n1', 'n2']  # MMR selects diverse vectors (not just top scores)
        """
        nodes = list(z.get("nodes", []))
        
        # Empty or zero budget edge case
        if not nodes or k <= 0:
            return []
        
        # Initialize RNG for deterministic tie-breaking (API compatibility)
        if rng is None:
            rng = random.Random(z.get("seed", "default"))
        
        # Respect node quota (budget cap)
        cap = int(z.get("quotas", {}).get("nodes", len(nodes)))
        cap = max(0, min(cap, len(nodes)))
        pool = nodes[:cap]
        
        # PR#4: Check for vec presence → use MMR if available
        any_vec = any(
            isinstance(n.get("vec"), (list, tuple)) and n.get("vec") and len(n.get("vec", [])) > 0 
            for n in pool
        )
        
        if any_vec:
            # Vec-MMR path (cosine diversity) - cast to Any for compatibility
            pool_dicts = [dict(n) for n in pool]  # type: ignore
            return _mmr_greedy(pool_dicts, k=min(k, cap), lambda_diversity=0.7, rng=rng)
        
        # Fallback: Score-sort with deterministic tie-breaks
        ordered = sorted(
            [(n.get("id"), float(n.get("score", 0.0))) for n in pool],
            key=lambda p: (-p[1], p[0])  # score desc, id asc
        )
        return [i for i, _ in ordered[:k]]
    
    @staticmethod
    def select_topk_for_global(
        z: ZSliceLite,
        k: int,
        exclude_ids: set[str],
        rng: Optional[random.Random] = None
    ) -> list[str]:
        """
        Select top-k node IDs for global pool (excluding stream nodes).
        
        PR#4: Score-based ranking only (stream handles diversity via MMR).
        Always uses deterministic tie-breaking by id.
        
        Args:
            z: Z-Space slice with nodes
            k: Number of nodes to select (global budget)
            exclude_ids: Node IDs already in stream (to exclude)
            rng: Optional seeded RNG for API compatibility
        
        Returns:
            List of node IDs (length ≤ k, no overlap with exclude_ids)
            
        Note:
            Global pool does NOT use Vec-MMR - diversity responsibility
            is on stream window. Global provides high-relevance backfill.
        
        Example:
            >>> z_slice = {"nodes": [...], "seed": "test"}
            >>> stream_ids = ZSpaceShim.select_topk_for_stream(z_slice, k=2)
            >>> global_ids = ZSpaceShim.select_topk_for_global(
            ...     z_slice, k=3, exclude_ids=set(stream_ids)
            ... )
            >>> assert set(global_ids) & set(stream_ids) == set()  # No overlap
        """
        nodes = list(z.get("nodes", []))
        
        if not nodes or k <= 0:
            return []
        
        # Initialize RNG (API compatibility, unused in score-sort)
        if rng is None:
            rng = random.Random(z.get("seed", "default"))
        
        # Respect node quota
        cap = int(z.get("quotas", {}).get("nodes", len(nodes)))
        cap = max(0, min(cap, len(nodes)))
        
        # Filter out stream nodes (after quota cap)
        pool = [n for n in nodes[:cap] if n.get("id") not in exclude_ids]
        
        if not pool:
            return []
        
        # PR#4: Global uses score-sort only (no MMR)
        # Deterministic tie-breaks by id
        ordered = sorted(
            [(n.get("id"), float(n.get("score", 0.0))) for n in pool],
            key=lambda p: (-p[1], p[0])  # score desc, id asc
        )
        
        return [i for i, _ in ordered[:k]]
    
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
