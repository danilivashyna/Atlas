"""
Path-aware router: routes text to semantic nodes via 5D cosine + hierarchical priors.

Scoring formula:
  score(n) = α * cosine(v(text), n.vec5) + β * n.weight + γ * child_bonus

Soft child activation uses softmax with temperature τ.
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional

import numpy as np

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

    def __init__(self, encoder, node_store, alpha=None, beta=None, gamma=None, tau=None):
        """
        Args:
            encoder: SemanticSpace with encode() method
            node_store: NodeStore with knn_nodes(), get_children() methods
            alpha: weight on cosine similarity (default from env: 0.7)
            beta: weight on node.weight prior (default from env: 0.2)
            gamma: weight on child_bonus (default from env: 0.1)
            tau: softmax temperature (default from env: 0.5)
        """
        self.encoder = encoder
        self.node_store = node_store

        # Load params from env or use provided values
        self.alpha = alpha or float(os.getenv("ATLAS_ROUTER_ALPHA", "0.7"))
        self.beta = beta or float(os.getenv("ATLAS_ROUTER_BETA", "0.2"))
        self.gamma = gamma or float(os.getenv("ATLAS_ROUTER_GAMMA", "0.1"))
        self.tau = tau or float(os.getenv("ATLAS_ROUTER_TAU", "0.5"))

        logger.debug(
            f"PathRouter initialized: α={self.alpha}, β={self.beta}, "
            f"γ={self.gamma}, τ={self.tau}"
        )

    def route(self, text: str, top_k: int = 3) -> list[PathScore]:
        """
        Route text to top-k nodes via 5D encoding + scoring.

        Args:
            text: input text
            top_k: number of top nodes to return

        Returns:
            list[PathScore] sorted by score descending
        """
        try:
            # Encode text to 5D
            vec = self.encoder.encode(text)
            if vec is None:
                logger.warning("Encoder returned None for text: %s", text[:50])
                return []

            # Fetch all nodes from store (or use knn if available)
            nodes = self.node_store.get_all_nodes()
            if not nodes:
                logger.info("No nodes in store; returning empty route")
                return []

            scores = []
            for node in nodes:
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
            vec = self.encoder.encode(text)
            if vec is None:
                logger.warning("Encoder returned None for text: %s", text[:50])
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
        Compute score for a single node.

        score = α * cosine_similarity + β * node.weight + γ * child_bonus

        Args:
            vec: 5D input vector
            node: node dict with 'vec5' and 'weight' fields

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

        score = self.alpha * cosine_norm + self.beta * weight + self.gamma * child_bonus
        return float(score)

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
