"""
Atlas β — FAISS Index Builder

Builds FAISS IVF-PQ index for document level.
Config-driven from indices/doc_faiss.yaml.

Version: 0.2.0-beta
"""

import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import faiss
import numpy as np

from atlas.configs import ConfigLoader


class FAISSIndexBuilder:
    """
    Builder for FAISS IVF-PQ index (document level).

    IVF (Inverted File Index): Clusters vectors into nlist centroids
    PQ (Product Quantization): Compresses vectors into m×nbits codes

    Config-driven from doc_faiss.yaml:
    - nlist, nprobe (IVF params)
    - m, nbits (PQ params)
    - training_size, batch_size

    ⚠️ Safety: Deterministic training (if training data fixed), reproducible builds.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize FAISS IVF-PQ builder.

        Args:
            config: Optional config dict (defaults to ConfigLoader)
        """
        self.level = "document"
        self.config = config or ConfigLoader.get_index_config("document")

        # Extract IVF params
        ivf_cfg = self.config["ivf"]
        self.nlist = ivf_cfg["nlist"]
        self.nprobe = ivf_cfg["nprobe"]

        # Extract PQ params
        pq_cfg = self.config["pq"]
        self.m = pq_cfg["m"]
        self.nbits = pq_cfg["nbits"]

        # Extract build params
        build_cfg = self.config["building"]
        self.training_size = build_cfg["training_size"]
        self.batch_size = build_cfg["batch_size"]

        # Vector params
        self.dim = self.config["vector_dim"]
        self.metric = self.config["metric"]

        # Storage
        storage_cfg = self.config["storage"]
        self.path_template = storage_cfg["path_template"]

        # Index instance (created on build)
        self.index: Optional[faiss.IndexIVFPQ] = None
        self.num_elements = 0
        self.is_trained = False

    def build(
        self,
        vectors: np.ndarray,
        ids: Optional[List[int]] = None,
        training_vectors: Optional[np.ndarray] = None,
        normalize: bool = True,
    ) -> faiss.IndexIVFPQ:
        """
        Build FAISS IVF-PQ index.

        Args:
            vectors: (N, dim) array of document embeddings
            ids: Optional list of IDs (defaults to 0..N-1)
            training_vectors: Optional separate training set (defaults to sample from vectors)
            normalize: L2-normalize vectors before indexing

        Returns:
            Built faiss.IndexIVFPQ instance

        Raises:
            ValueError: If vectors shape doesn't match config dim

        Notes:
            - Two-stage: (1) train IVF/PQ codebooks, (2) add vectors
            - Training uses training_vectors or random sample from vectors
            - Deterministic if training_vectors fixed
        """
        N, D = vectors.shape
        if D != self.dim:
            raise ValueError(f"Vector dim {D} doesn't match config dim {self.dim}")

        # Normalize if requested
        if normalize:
            vectors = self._normalize_vectors(vectors)
            if training_vectors is not None:
                training_vectors = self._normalize_vectors(training_vectors)

        # Default IDs
        if ids is None:
            ids = np.arange(N, dtype=np.int64)
        else:
            ids = np.array(ids, dtype=np.int64)

        # Prepare training data
        if training_vectors is None:
            # Sample from vectors
            if N >= self.training_size:
                train_indices = np.random.choice(N, self.training_size, replace=False)
                training_vectors = vectors[train_indices]
            else:
                training_vectors = vectors

        # Create quantizer (flat L2 index for centroids)
        quantizer = faiss.IndexFlatL2(self.dim)

        # Create IVF-PQ index
        self.index = faiss.IndexIVFPQ(
            quantizer,
            self.dim,
            self.nlist,  # Number of centroids
            self.m,      # Number of subquantizers
            self.nbits,  # Bits per subquantizer
        )

        # Train index (learn IVF centroids + PQ codebooks)
        print(f"Training FAISS IVF-PQ with {len(training_vectors)} vectors...")
        self.index.train(training_vectors)
        self.is_trained = True

        # Add vectors to index
        print(f"Adding {N} vectors to index...")
        self.index.add_with_ids(vectors, ids)

        # Set nprobe for search
        self.index.nprobe = self.nprobe

        self.num_elements = N

        return self.index

    def save(self, path: Optional[Path] = None) -> Tuple[Path, str]:
        """
        Save index to disk and compute SHA256 checksum.

        Args:
            path: Optional save path (defaults to config path_template)

        Returns:
            Tuple of (saved_path, sha256_checksum)

        Raises:
            RuntimeError: If index not built/trained yet
        """
        if self.index is None or not self.is_trained:
            raise RuntimeError("Index not trained yet. Call build() first.")

        # Determine path
        if path is None:
            path = Path(self.path_template)
        else:
            path = Path(path)

        # Create directories
        path.parent.mkdir(parents=True, exist_ok=True)

        # Save index
        faiss.write_index(self.index, str(path))

        # Compute SHA256
        sha256 = self._compute_sha256(path)

        return path, sha256

    def load(self, path: Path) -> faiss.IndexIVFPQ:
        """
        Load index from disk.

        Args:
            path: Path to saved index file

        Returns:
            Loaded faiss.IndexIVFPQ instance

        Notes:
            - Sets nprobe from config
            - Validates index type is IVF-PQ
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Index file not found: {path}")

        # Load index
        index = faiss.read_index(str(path))

        # Validate type
        if not isinstance(index, faiss.IndexIVFPQ):
            raise TypeError(f"Expected IndexIVFPQ, got {type(index)}")

        self.index = index
        self.is_trained = True

        # Set nprobe for search
        self.index.nprobe = self.nprobe

        self.num_elements = self.index.ntotal

        return self.index

    def search(
        self,
        query_vectors: np.ndarray,
        k: int = 10,
        normalize: bool = True,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search index for nearest neighbors.

        Args:
            query_vectors: (Q, dim) array of query embeddings
            k: Number of neighbors to return
            normalize: L2-normalize queries before search

        Returns:
            Tuple of (distances, labels) arrays
            - distances: (Q, k) array of L2 distances
            - labels: (Q, k) array of neighbor IDs

        Raises:
            RuntimeError: If index not loaded/trained

        Notes:
            - nprobe controls recall/speed tradeoff
            - Higher nprobe = search more clusters = better recall
        """
        if self.index is None or not self.is_trained:
            raise RuntimeError("Index not loaded. Call load() or build() first.")

        # Normalize if requested
        if normalize:
            query_vectors = self._normalize_vectors(query_vectors)

        # Search
        distances, labels = self.index.search(query_vectors, k)

        return distances, labels

    def _normalize_vectors(self, vectors: np.ndarray) -> np.ndarray:
        """
        L2-normalize vectors.

        Args:
            vectors: (N, dim) array

        Returns:
            L2-normalized (N, dim) array
        """
        norm_cfg = self.config["normalization"]
        clip_value = norm_cfg["clip_value"]
        tolerance = norm_cfg["tolerance"]

        # Clip outliers
        vectors = np.clip(vectors, -clip_value, clip_value)

        # L2 normalize
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.maximum(norms, float(tolerance))

        return vectors / norms

    def _compute_sha256(self, path: Path) -> str:
        """Compute SHA256 checksum of index file."""
        sha256_hash = hashlib.sha256()

        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)

        return sha256_hash.hexdigest()

    def get_stats(self) -> Dict:
        """Get index statistics."""
        if self.index is None:
            return {"built": False}

        return {
            "built": True,
            "trained": self.is_trained,
            "level": self.level,
            "num_elements": self.num_elements,
            "dim": self.dim,
            "nlist": self.nlist,
            "nprobe": self.nprobe,
            "m": self.m,
            "nbits": self.nbits,
            "metric": self.metric,
        }


def create_faiss_index(
    vectors: np.ndarray,
    ids: Optional[List[int]] = None,
    training_vectors: Optional[np.ndarray] = None,
    save_path: Optional[Path] = None,
) -> Tuple[faiss.IndexIVFPQ, Path, str]:
    """
    Convenience function to build, save, and return FAISS IVF-PQ index.

    Args:
        vectors: (N, dim) document embeddings
        ids: Optional IDs (defaults to 0..N-1)
        training_vectors: Optional separate training set
        save_path: Optional save path (defaults to config)

    Returns:
        Tuple of (index, saved_path, sha256_checksum)

    Example:
        >>> vectors = np.random.randn(10000, 384).astype(np.float32)
        >>> index, path, sha256 = create_faiss_index(vectors)
        >>> print(f"Saved to {path}, SHA256: {sha256[:16]}...")
    """
    builder = FAISSIndexBuilder()
    index = builder.build(vectors, ids=ids, training_vectors=training_vectors, normalize=True)
    path, sha256 = builder.save(save_path)

    return index, path, sha256
