"""
Approximate Nearest Neighbor (ANN) index for fast kNN search over nodes.

Supports multiple backends:
  - inproc: In-memory numpy + partial sort (no external deps)
  - faiss: FAISS IndexFlatIP for fast similarity search (requires faiss-cpu/gpu)
  - off: Disabled (returns None, falls back to full scan in router)

Build from node vectors, query with embedding vector.
Saves/loads from disk for persistence.
"""

import logging
import os
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ANNSearchResult:
    """Result from ANN query: node path and similarity score."""

    path: str
    score: float  # [0, 1] for IP, [-1, 1] for cosine


class NodeANN:
    """
    Abstract base for ANN backends.
    """

    def build(self, nodes: List[dict]) -> None:
        """Build index from node list: [{"path": "...", "vec5": [...]}]."""
        raise NotImplementedError

    def query(self, vec: np.ndarray, top_k: int) -> List[ANNSearchResult]:
        """Query index with embedding vector. Returns top_k results."""
        raise NotImplementedError

    def save(self, path: str) -> None:
        """Save index to disk."""
        raise NotImplementedError

    def load(self, path: str) -> None:
        """Load index from disk."""
        raise NotImplementedError

    @property
    def backend_name(self) -> str:
        """Backend identifier."""
        raise NotImplementedError

    @property
    def index_size(self) -> int:
        """Number of vectors in index."""
        raise NotImplementedError


class InprocessANN(NodeANN):
    """
    Lightweight in-process ANN using numpy.
    Stores vectors and paths, performs linear search with partial sort.
    """

    def __init__(self):
        self.vectors = None  # (n_nodes, 5) float32
        self.paths = []  # path strings
        self._index_size = 0

    def build(self, nodes: List[dict]) -> None:
        """Build index from nodes."""
        if not nodes:
            self.vectors = np.array([], dtype=np.float32).reshape(0, 5)
            self.paths = []
            self._index_size = 0
            logger.info("Inprocess ANN: built empty index")
            return

        vecs = []
        paths = []
        for node in nodes:
            vec = np.array(node["vec5"], dtype=np.float32)
            if vec.shape != (5,):
                logger.warning(f"Invalid vec5 shape for {node['path']}: {vec.shape}")
                continue
            vecs.append(vec)
            paths.append(node["path"])

        if vecs:
            self.vectors = np.array(vecs, dtype=np.float32)  # (n, 5)
            self.paths = paths
            self._index_size = len(paths)
            logger.info(f"Inprocess ANN: built index with {self._index_size} vectors")
        else:
            self.vectors = np.array([], dtype=np.float32).reshape(0, 5)
            self.paths = []
            self._index_size = 0

    def query(self, vec: np.ndarray, top_k: int) -> List[ANNSearchResult]:
        """Query with vector. Returns top_k by inner product (IP/cosine)."""
        if self.vectors is None or len(self.vectors) == 0:
            return []

        # Ensure vec is float32, shape (5,)
        vec = np.asarray(vec, dtype=np.float32)
        if vec.shape != (5,):
            logger.warning(f"Query vec shape mismatch: {vec.shape}")
            return []

        # Compute inner product (cosine-like score when vectors are normalized)
        scores = np.dot(self.vectors, vec)  # (n,)

        # Get top_k indices
        top_k = min(top_k, len(scores))
        top_indices = np.argsort(-scores)[:top_k]

        results = []
        for idx in top_indices:
            path = self.paths[idx]
            score = float(scores[idx])
            results.append(ANNSearchResult(path=path, score=score))

        return results

    def save(self, path: str) -> None:
        """Save vectors and paths to disk."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        np.save(path, {"vectors": self.vectors, "paths": self.paths}, allow_pickle=True)
        logger.info(f"Inprocess ANN: saved index to {path}")

    def load(self, path: str) -> None:
        """Load vectors and paths from disk."""
        try:
            data = np.load(path, allow_pickle=True).item()
            self.vectors = data.get("vectors", np.array([], dtype=np.float32).reshape(0, 5))
            self.paths = data.get("paths", [])
            self._index_size = len(self.paths)
            logger.info(f"Inprocess ANN: loaded index from {path} ({self._index_size} vectors)")
        except Exception as e:
            logger.warning(f"Failed to load inprocess ANN from {path}: {e}")
            self.vectors = np.array([], dtype=np.float32).reshape(0, 5)
            self.paths = []
            self._index_size = 0

    @property
    def backend_name(self) -> str:
        return "inproc"

    @property
    def index_size(self) -> int:
        return self._index_size


class FAISSANNIndex(NodeANN):
    """
    FAISS-backed ANN using IndexFlatIP (inner product).
    Requires: pip install faiss-cpu or faiss-gpu
    """

    def __init__(self):
        self.index = None
        self.paths = []
        self._index_size = 0
        try:
            import faiss

            self.faiss = faiss
        except ImportError:
            logger.warning("FAISS not installed. Install with: pip install faiss-cpu")
            self.faiss = None

    def build(self, nodes: List[dict]) -> None:
        """Build FAISS IndexFlatIP from nodes."""
        if self.faiss is None:
            logger.error("FAISS not available")
            return

        if not nodes:
            logger.info("FAISS ANN: building empty index")
            self.index = self.faiss.IndexFlatIP(5)
            self.paths = []
            self._index_size = 0
            return

        vecs = []
        paths = []
        for node in nodes:
            vec = np.array(node["vec5"], dtype=np.float32)
            if vec.shape != (5,):
                logger.warning(f"Invalid vec5 shape for {node['path']}: {vec.shape}")
                continue
            vecs.append(vec)
            paths.append(node["path"])

        if vecs:
            vecs = np.array(vecs, dtype=np.float32)  # (n, 5)
            self.index = self.faiss.IndexFlatIP(5)
            self.index.add(vecs)
            self.paths = paths
            self._index_size = len(paths)
            logger.info(f"FAISS ANN: built index with {self._index_size} vectors")
        else:
            self.index = self.faiss.IndexFlatIP(5)
            self.paths = []
            self._index_size = 0

    def query(self, vec: np.ndarray, top_k: int) -> List[ANNSearchResult]:
        """Query FAISS index. Returns top_k."""
        if self.index is None or self._index_size == 0:
            return []

        vec = np.asarray(vec, dtype=np.float32).reshape(1, -1)
        if vec.shape != (1, 5):
            logger.warning(f"Query vec shape mismatch: {vec.shape}")
            return []

        top_k = min(top_k, self._index_size)
        distances, indices = self.index.search(vec, top_k)

        results = []
        for i, idx in enumerate(indices[0]):
            if idx < 0:  # Invalid index
                continue
            path = self.paths[int(idx)]
            score = float(distances[0][i])
            results.append(ANNSearchResult(path=path, score=score))

        return results

    def save(self, path: str) -> None:
        """Save FAISS index and paths to disk."""
        if self.faiss is None or self.index is None:
            logger.warning("FAISS ANN not available, skipping save")
            return

        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.faiss.write_index(self.index, path)

        # Save paths separately
        import json

        paths_file = path + ".paths.json"
        with open(paths_file, "w") as f:
            json.dump(self.paths, f)

        logger.info(f"FAISS ANN: saved index to {path}")

    def load(self, path: str) -> None:
        """Load FAISS index and paths from disk."""
        if self.faiss is None:
            logger.warning("FAISS not available, skipping load")
            return

        try:
            self.index = self.faiss.read_index(path)

            # Load paths
            import json

            paths_file = path + ".paths.json"
            with open(paths_file, "r") as f:
                self.paths = json.load(f)

            self._index_size = len(self.paths)
            logger.info(f"FAISS ANN: loaded index from {path} ({self._index_size} vectors)")
        except Exception as e:
            logger.warning(f"Failed to load FAISS ANN from {path}: {e}")
            self.index = None
            self.paths = []
            self._index_size = 0

    @property
    def backend_name(self) -> str:
        return "faiss"

    @property
    def index_size(self) -> int:
        return self._index_size


def get_ann_index(backend: str = "inproc") -> Optional[NodeANN]:
    """
    Factory for ANN index.

    Args:
        backend: 'inproc', 'faiss', or 'off'

    Returns:
        NodeANN instance or None if backend='off'
    """
    if backend == "off":
        logger.info("ANN backend set to 'off'")
        return None
    elif backend == "faiss":
        logger.info("Using FAISS ANN backend")
        return FAISSANNIndex()
    elif backend == "inproc":
        logger.info("Using inproc ANN backend")
        return InprocessANN()
    else:
        logger.warning(f"Unknown ANN backend '{backend}', defaulting to 'inproc'")
        return InprocessANN()
