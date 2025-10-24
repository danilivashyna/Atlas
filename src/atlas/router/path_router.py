"""
Path-aware router: routes text to semantic nodes via 5D cosine + hierarchical priors.

Scoring formula (v0.5+):
  score(n) = α * cosine_norm + β * weight + γ * child_bonus + δ * prior_path

  where:
    cosine_norm = (cosine(text_vec, node.vec5) + 1) / 2  ∈ [0, 1]
    weight = node.weight ∈ [0, 1]
    child_bonus = I(best_child_scores_higher_than_node)
    prior_path = Σ(weight(parent^d) * decay^d) for d=1..D  (inherited weight with decay)

Soft child activation uses softmax with temperature τ.
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional

import numpy as np

from atlas.metrics.mensum import metrics_ns
from atlas.router.ann_index import get_query_cache

logger = logging.getLogger(__name__)


@dataclass
class PathScore:
    """Route result: path and score"""

    path: str
    score: float
    label: Optional[str] = None
    meta: Optional[dict] = None


@dataclass
class ChildActivation:
    """Soft-activated child: path and probability"""

    path: str
    p: float


class PathRouter:
    """
    Routes 5D vectors to hierarchical nodes with scoring and soft activation.

    Depends on:
    - encoder (SemanticSpace) to convert text → 5D vector
    - node_store (get_node_store()) to fetch nodes and their relationships
    """

    def __init__(
        self,
        encoder,
        node_store,
        alpha=None,
        beta=None,
        gamma=None,
        delta=None,
        tau=None,
        decay=None,
        ann_index=None,
    ):
        """
        Args:
            encoder: SemanticSpace with encode() method
            node_store: NodeStore with knn_nodes(), get_children(), get_all_nodes() methods
            alpha: weight on cosine similarity (default from env: 0.7)
            beta: weight on node.weight prior (default from env: 0.15)
            gamma: weight on child_bonus (default from env: 0.1)
            delta: weight on inherited path prior (default from env: 0.05)  [NEW v0.5]
            tau: softmax temperature (default from env: 0.5)
            decay: exponential decay for inherited weights up tree (default from env: 0.85)  [NEW v0.5]
            ann_index: optional NodeANN instance for fast kNN (default: None, uses full scan)  [NEW v0.5]
        """
        self.encoder = encoder
        self.node_store = node_store
        self.ann_index = ann_index

        # Load params from env or use provided values
        self.alpha = alpha or float(os.getenv("ATLAS_ROUTER_ALPHA", "0.7"))
        self.beta = beta or float(os.getenv("ATLAS_ROUTER_BETA", "0.15"))
        self.gamma = gamma or float(os.getenv("ATLAS_ROUTER_GAMMA", "0.1"))
        self.delta = delta or float(os.getenv("ATLAS_ROUTER_DELTA", "0.05"))  # NEW
        self.tau = tau or float(os.getenv("ATLAS_ROUTER_TAU", "0.5"))
        self.decay = decay or float(os.getenv("ATLAS_ROUTER_DECAY", "0.85"))  # NEW

        # Hourglass/Beam parameters (v0.6+ stubs for future implementation)
        self.beam = int(os.getenv("ATLAS_ROUTER_BEAM", "4"))  # beam width for hourglass search
        self.depth = int(os.getenv("ATLAS_ROUTER_DEPTH", "3"))  # search depth
        self.conf_threshold = float(os.getenv("ATLAS_ROUTER_CONF", "0.85"))  # confidence threshold

        # Verify weights; if sum>0 and !=1 → hard-normalize
        weight_sum = self.alpha + self.beta + self.gamma + self.delta
        if weight_sum > 0 and abs(weight_sum - 1.0) > 1e-6:
            self.alpha /= weight_sum
            self.beta /= weight_sum
            self.gamma /= weight_sum
            self.delta /= weight_sum
            logger.info(
                "PathRouter: normalized weights to α=%.3f β=%.3f γ=%.3f δ=%.3f (sum=1.0)",
                self.alpha,
                self.beta,
                self.gamma,
                self.delta,
            )

        # Expose config as gauge for monitoring
        metrics_ns().set_gauge(
            "router_weights",
            1.0,
            labels={
                "alpha": f"{self.alpha:.3f}",
                "beta": f"{self.beta:.3f}",
                "gamma": f"{self.gamma:.3f}",
                "delta": f"{self.delta:.3f}",
                "tau": f"{self.tau:.3f}",
                "decay": f"{self.decay:.3f}",
            },
        )

        logger.debug(
            f"PathRouter initialized: α={self.alpha}, β={self.beta}, "
            f"γ={self.gamma}, δ={self.delta}, τ={self.tau}, decay={self.decay}"
        )

    def _get_vec5_with_cache(self, text: str) -> np.ndarray:
        """Get 5D vector for text with caching. Return empty array if encode() is None/bad."""
        size = int(os.getenv("ATLAS_QUERY_CACHE_SIZE", "2048"))
        ttl = float(os.getenv("ATLAS_QUERY_CACHE_TTL", "300"))
        cache = get_query_cache(size=size, ttl=ttl)

        def _compute():
            try:
                v = self.encoder.encode(text)
                if v is None:
                    return np.array([], dtype=np.float32)
                v = np.asarray(v, dtype=np.float32)
                return v if v.size == 5 else np.array([], dtype=np.float32)
            except Exception:
                return np.array([], dtype=np.float32)

        vec5, _hit = cache.get_or_compute(f"q:{text}", _compute)
        return vec5

    def route(self, text: str, top_k: int = 3, use_ann: bool = True) -> list[PathScore]:
        """
        Route text to top-k nodes via 5D encoding + path-aware scoring.

        Args:
            text: input text
            top_k: number of top nodes to return
            use_ann: if True and ann_index exists, use ANN for candidate selection (faster)  [NEW v0.5]

        Returns:
            list[PathScore] sorted by score descending
        """
        try:
            # Encode text to 5D
            vec = self._get_vec5_with_cache(text)
            if vec.size != 5:
                logger.debug("route(): empty/invalid vec5 — returning []")
                return []

            # Fetch candidate nodes: use ANN if available and enabled, else full scan
            if use_ann and self.ann_index is not None:
                # Get more candidates from ANN to ensure we score all relevant nodes
                ann_candidates = self.ann_index.search(vec, top_k=top_k * 3)
                candidate_paths = {r[0] for r in ann_candidates}
                candidate_nodes = [
                    n for n in self.node_store.get_all_nodes() if n.get("path") in candidate_paths
                ]
                logger.debug(
                    f"Using ANN: {len(candidate_nodes)} candidate nodes from {len(ann_candidates)} ANN results"
                )
            else:
                candidate_nodes = self.node_store.get_all_nodes()
            logger.debug("route(): %d candidate nodes", len(candidate_nodes))

            if not candidate_nodes:
                logger.info("No nodes in store; returning empty route")
                return []

            scores = []
            for node in candidate_nodes:
                score = self._score_node(vec, node)
                scores.append(
                    PathScore(
                        path=node["path"],
                        score=score,
                        label=node.get("label"),
                        meta=node.get("meta"),
                    )
                )

            # Sort descending, return top-k
            scores.sort(key=lambda x: x.score, reverse=True)
            return scores[:top_k]

        except Exception as e:
            logger.error(f"route() failed: {e}")
            return []

    def activate_child(self, path: str, text: str) -> list[ChildActivation]:
        """
        Soft-activate children of a node using softmax.

        Args:
            path: parent node path
            text: input text (for scoring children)

        Returns:
            list[ChildActivation] with probabilities summing ≈1.0
        """
        try:
            # Encode text
            vec = self._get_vec5_with_cache(text)
            if vec.size != 5:
                logger.debug("activate_child(): empty/invalid vec5 — returning []")
                return []

            # Get children of this node
            children = self.node_store.get_children(path)
            if not children:
                logger.info(f"No children for path: {path}")
                return []

            # Score each child
            child_scores = []
            for child in children:
                score = self._score_node(vec, child)
                child_scores.append((child["path"], score))

            # Apply softmax with temperature
            scores_arr = np.array([s[1] for s in child_scores])
            logits = scores_arr / self.tau  # temperature scaling
            exp_logits = np.exp(logits - np.max(logits))  # numerical stability
            probs = exp_logits / np.sum(exp_logits)

            result = [
                ChildActivation(path=path, p=float(prob))
                for (path, _), prob in zip(child_scores, probs)
            ]
            return sorted(result, key=lambda x: x.p, reverse=True)

        except Exception as e:
            logger.error(f"activate_child() failed: {e}")
            return []

    def _score_node(self, vec: np.ndarray, node: dict) -> float:
        """
        Compute score for a single node with path-aware priors.

        score = α * cosine_norm + β * weight + γ * child_bonus + δ * prior_path

        Args:
            vec: 5D input vector
            node: node dict with 'path', 'vec5', 'weight', 'parent' fields

        Returns:
            float score
        """
        # Extract node vector (5D)
        node_vec = np.array(node.get("vec5", [0.0] * 5), dtype=np.float32)

        # Cosine similarity: [-1..1] → normalize to [0..1]
        cosine_sim = self._cosine(vec, node_vec)
        cosine_norm = (cosine_sim + 1.0) / 2.0  # [-1,1] → [0,1]

        # Prior weight (0..1, default 0.5)
        weight = node.get("weight", 0.5)

        # Path-aware prior: inherited weights with exponential decay  [NEW v0.5]
        prior_path = self._compute_path_prior(node.get("path"), node.get("parent"))

        # Child bonus: check if any children score higher (fast heuristic)
        child_bonus = 0.0
        try:
            children = self.node_store.get_children(node["path"])
            if children:
                max_child_score = max(
                    self._cosine(vec, np.array(c.get("vec5", [0.0] * 5))) for c in children
                )
                child_bonus = (
                    max(0.0, min(1.0, max_child_score)) if max_child_score > cosine_sim else 0.0
                )
        except Exception:
            pass  # No child bonus if lookup fails

        score = (
            self.alpha * cosine_norm
            + self.beta * weight
            + self.gamma * child_bonus
            + self.delta * prior_path
        )
        return float(score)

    def _compute_path_prior(self, path: str, parent: Optional[str]) -> float:
        """
        Compute inherited weight from ancestors with exponential decay.

        prior_path = Σ(weight(parent^d) * decay^d) for d=1..D

        Args:
            path: current node path (e.g., 'dim2/dim2.4')
            parent: parent path (e.g., 'dim2'), or None for root

        Returns:
            float in [0, 1]
        """
        prior = 0.0
        current_parent = parent
        depth = 1

        while current_parent is not None and depth <= 10:  # Limit traversal depth
            try:
                # Get parent node to extract its weight
                parent_nodes = [
                    n for n in self.node_store.get_all_nodes() if n.get("path") == current_parent
                ]
                if parent_nodes:
                    parent_node = parent_nodes[0]
                    parent_weight = parent_node.get("weight", 0.5)
                    decay_factor = self.decay**depth
                    contribution = parent_weight * decay_factor
                    prior += contribution

                    # Move to parent's parent
                    current_parent = parent_node.get("parent")
                    depth += 1
                else:
                    break
            except Exception:
                break

        return float(min(prior, 1.0))  # Clamp to [0, 1]

    def route_iter(self, query: str, top_k: int = 5) -> dict:
        """
        Iterative hourglass-stencil routing stub (v0.6 placeholder).

        Currently: 1) calls standard route(), 2) wraps result in trace structure
        compatible with future multi-iteration logic.

        Args:
            query: Text query
            top_k: Top-k results to return

        Returns:
            Dict with keys:
            - 'iterations': list of iteration traces (currently 1 iteration)
            - 'final': list of PathScore results (same as route())
        """
        import time

        start_ts = time.time()

        # Call standard route
        items = self.route(query, top_k=top_k) or []

        # Record metrics
        try:
            elapsed_ms = (time.time() - start_ts) * 1000
            metrics_ns().inc_counter("router_route_iter_total")
            metrics_ns().observe_histogram("router_route_iter_latency_ms", elapsed_ms)
            metrics_ns().set_gauge(
                "router_beam_width",
                len(items),
                labels={"current": "yes", "max": str(self.beam)},
            )
        except Exception:
            pass

        # Wrap in trace structure for future compatibility
        return {
            "iterations": [
                {
                    "beam": [{"path": x.path, "score": x.score} for x in items],
                    "center_conf": 1.0 if items else 0.0,
                }
            ],
            "final": items,
        }

    @staticmethod
    def _cosine(v1: np.ndarray, v2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors. Returns [-1..1]."""
        v1 = np.asarray(v1, dtype=np.float32)
        v2 = np.asarray(v2, dtype=np.float32)

        mag1 = np.linalg.norm(v1)
        mag2 = np.linalg.norm(v2)

        if mag1 == 0 or mag2 == 0:
            return 0.0

        return float(np.dot(v1, v2) / (mag1 * mag2))
