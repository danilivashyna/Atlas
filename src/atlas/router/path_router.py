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

    def route_iter(
        self,
        text: str,
        top_k: int = 3,
        beam: Optional[int] = None,
        depth: Optional[int] = None,
        conf: Optional[float] = None,
        use_ann: bool = True,
    ) -> dict:
        """
        Iterative routing with beam search and confidence stopping.

        Returns trace dict with final results, iterations, stopped_reason, conf.
        """
        import time

        start_time = time.time()

        # Params from args or env
        beam = beam or int(os.getenv("ATLAS_ROUTER_BEAM", "5"))
        depth = depth or int(os.getenv("ATLAS_ROUTER_DEPTH", "2"))
        conf_thresh = conf or float(os.getenv("ATLAS_ROUTER_CONF", "0.85"))
        k_mult = float(os.getenv("ATLAS_ROUTER_K_MULT", "3.0"))

        try:
            vec = self._get_vec5_with_cache(text)
            if vec.size != 5:
                return {"final": [], "iterations": [], "stopped_reason": "empty", "conf": 0.0}

            K = int(top_k * k_mult)
            if use_ann and self.ann_index:
                ann_results = self.ann_index.search(vec, top_k=K)
                candidate_paths = {r[0] for r in ann_results}
                C0 = [
                    n for n in self.node_store.get_all_nodes() if n.get("path") in candidate_paths
                ]
            else:
                C0 = self.node_store.get_all_nodes()

            logger.debug(f"route_iter[d=0]: {len(C0)} candidates")

            S0 = [self._score_node(vec, n) for n in C0]
            B0 = self._softmax_top([(C0[i]["path"], S0[i]) for i in range(len(C0))], beam)

            iterations = [
                {"candidates": len(C0), "beam": [{"path": p, "p": p_val} for p, p_val in B0]}
            ]
            current_beam = B0
            stopped_reason = "depth"

            for d in range(1, depth + 1):
                # Gather children + optional reticulum neighbors
                new_candidates = []
                for path, _ in current_beam:
                    children = self.node_store.get_children(path)
                    new_candidates.extend(children)
                    # Optional: add reticulum neighbors
                    try:
                        neighbors = self.node_store.neighbors_from_node(path, top_k=5)
                        # For simplicity, skip reticulum for now
                    except:
                        pass

                if not new_candidates:
                    stopped_reason = "empty"
                    break

                # Score new candidates
                S_new = [self._score_node(vec, n) for n in new_candidates]
                B_new = self._softmax_top(
                    [(new_candidates[i]["path"], S_new[i]) for i in range(len(new_candidates))],
                    beam,
                )

                # Check confidence
                max_p = max(p for _, p in B_new) if B_new else 0.0
                if max_p >= conf_thresh:
                    stopped_reason = "confidence"
                    current_beam = B_new
                    iterations.append(
                        {
                            "candidates": len(new_candidates),
                            "beam": [{"path": p, "p": p_val} for p, p_val in B_new],
                        }
                    )
                    break

                current_beam = B_new
                iterations.append(
                    {
                        "candidates": len(new_candidates),
                        "beam": [{"path": p, "p": p_val} for p, p_val in B_new],
                    }
                )
                logger.debug(
                    f"route_iter[d={d}]: {len(new_candidates)} candidates → beam {len(B_new)}"
                )

            # Final: top-k from last beam
            final_scores = []
            for path, p in current_beam[:top_k]:
                node = next((n for n in self.node_store.get_all_nodes() if n["path"] == path), None)
                if node:
                    final_scores.append(
                        PathScore(
                            path=path, score=p, label=node.get("label"), meta=node.get("meta")
                        )
                    )

            latency = time.time() - start_time
            metrics_ns().observe_hist("router_beam_confidence", max_p if current_beam else 0.0)
            metrics_ns().observe_hist("router_beam_time_ms", latency * 1000)
            metrics_ns().inc_counter(
                "router_beam_iterations_total", labels={"stopped_reason": stopped_reason}
            )

            return {
                "final": [
                    {"path": ps.path, "score": ps.score, "label": ps.label, "meta": ps.meta}
                    for ps in final_scores
                ],
                "iterations": iterations,
                "stopped_reason": stopped_reason,
                "conf": max_p if current_beam else 0.0,
            }

        except Exception as e:
            logger.error(f"route_iter() failed: {e}")
            return {"final": [], "iterations": [], "stopped_reason": "error", "conf": 0.0}

    def _softmax_top(self, scored: list[tuple[str, float]], beam: int) -> list[tuple[str, float]]:
        """Softmax top-beam from scored list."""
        if not scored:
            return []
        scores = np.array([s for _, s in scored])
        logits = scores / self.tau
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / np.sum(exp_logits)
        top_indices = np.argsort(probs)[-beam:][::-1]
        return [(scored[i][0], float(probs[i])) for i in top_indices]

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

    def feedback(
        self,
        node_path: str,
        outcome: str,
        text: Optional[str] = None,
        content_id: Optional[str] = None,
        version: Optional[int] = None,
    ) -> None:
        """
        Apply feedback to node and related entities.
        """
        sgn = 1.0 if outcome == "positive" else -1.0
        eps_w = 0.01  # weight epsilon
        eps_l = 0.01  # link epsilon
        alpha = 0.02  # EMA alpha for vec5

        # Find node
        nodes = [n for n in self.node_store.get_all_nodes() if n["path"] == node_path]
        if not nodes:
            logger.warning(f"feedback: node {node_path} not found")
            return
        node = nodes[0]

        # Update node weight
        old_weight = node.get("weight", 0.5)
        new_weight = max(0.0, min(1.0, old_weight + sgn * eps_w))
        node["weight"] = round(new_weight, 4)
        self.node_store.write_node(
            node["path"],
            node.get("parent"),
            node["vec5"],
            node.get("label"),
            new_weight,
            node.get("meta"),
        )

        # Update ancestors with decay
        current_parent = node.get("parent")
        decay_factor = 0.5
        depth = 1
        while current_parent and depth <= 5:
            parent_nodes = [
                n for n in self.node_store.get_all_nodes() if n["path"] == current_parent
            ]
            if parent_nodes:
                pnode = parent_nodes[0]
                p_old_weight = pnode.get("weight", 0.5)
                p_new_weight = max(0.0, min(1.0, p_old_weight + sgn * eps_w * decay_factor))
                pnode["weight"] = round(p_new_weight, 4)
                self.node_store.write_node(
                    pnode["path"],
                    pnode.get("parent"),
                    pnode["vec5"],
                    pnode.get("label"),
                    p_new_weight,
                    pnode.get("meta"),
                )
                current_parent = pnode.get("parent")
                decay_factor *= 0.5
                depth += 1
            else:
                break

        # Update link score if content_id
        if content_id is not None:
            # Find latest link_version
            links = self.node_store.get_link_versions(content_id)
            if links:
                latest = max(links, key=lambda l: l["version"])
                old_score = latest["score"]
                new_score = max(0.0, min(1.0, old_score + sgn * eps_l))
                self.node_store.write_link_version(
                    latest["node_path"],
                    content_id,
                    latest["version"],
                    new_score,
                    latest.get("kind"),
                    latest.get("meta"),
                )

        # Update node vec5 with EMA if text
        if text:
            vec = self._get_vec5_with_cache(text)
            if vec.size == 5:
                old_vec = np.array(node["vec5"])
                new_vec = (1 - alpha) * old_vec + alpha * vec
                node["vec5"] = [round(float(x), 4) for x in new_vec]
                self.node_store.write_node(
                    node["path"],
                    node.get("parent"),
                    node["vec5"],
                    node.get("label"),
                    node["weight"],
                    node.get("meta"),
                )

        metrics_ns().inc_counter("feedback_total", labels={"outcome": outcome})
        metrics_ns().inc_counter("feedback_weight_updates_total")
        if content_id:
            metrics_ns().inc_counter("feedback_link_updates_total")
        if text:
            metrics_ns().inc_counter("feedback_vec_updates_total")

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
