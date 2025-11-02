"""
Atlas β — HNSW Index Builder

Builds HNSW indices for sentence and paragraph levels using hnswlib.
Config-driven from indices/sent_hnsw.yaml and indices/para_hnsw.yaml.

Version: 0.2.0-beta
"""

import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import hnswlib
import numpy as np

from atlas.configs import ConfigLoader


class HNSWIndexBuilder:
    """
    Builder for HNSW indices (sentence/paragraph levels).

    Config-driven construction from YAML:
    - M, ef_construction, ef_search
    - batch_size, num_threads
    - normalization parameters
    - storage paths

    ⚠️ Safety: Deterministic construction (seed-based), reproducible builds.
    """

    def __init__(self, level: str, config: Optional[Dict] = None):
        """
        Initialize HNSW builder.

        Args:
            level: "sentence" or "paragraph"
            config: Optional config dict (defaults to ConfigLoader)

        Raises:
            ValueError: If level not in {sentence, paragraph}
        """
        if level not in ("sentence", "paragraph"):
            raise ValueError(f"HNSW level must be 'sentence' or 'paragraph', got: {level}")

        self.level = level
        self.config = config or ConfigLoader.get_index_config(level)

        # Extract HNSW params
        hnsw_cfg = self.config["hnsw"]
        self.M = hnsw_cfg["M"]
        self.ef_construction = hnsw_cfg["ef_construction"]
        self.ef_search = hnsw_cfg["ef_search"]
        self.seed = hnsw_cfg["seed"]

        # Extract build params
        build_cfg = self.config["building"]
        self.batch_size = build_cfg["batch_size"]
        self.num_threads = build_cfg["num_threads"]

        # Vector params
        self.dim = self.config["vector_dim"]
        self.metric = self.config["metric"]

        # Storage
        storage_cfg = self.config["storage"]
        self.path_template = storage_cfg["path_template"]

        # Index instance (created on build)
        self.index: Optional[hnswlib.Index] = None
        self.num_elements = 0

    def build(
        self,
        vectors: np.ndarray,
        ids: Optional[List[int]] = None,
        normalize: bool = True,
    ) -> hnswlib.Index:
        """
        Build HNSW index from vectors.

        Args:
            vectors: (N, dim) array of embeddings
            ids: Optional list of IDs (defaults to 0..N-1)
            normalize: L2-normalize vectors before indexing

        Returns:
            Built hnswlib.Index instance

        Raises:
            ValueError: If vectors shape doesn't match config dim

        Notes:
            - Deterministic: uses seed from config
            - Batched construction for memory efficiency
            - Reproducible: same vectors + seed → same index
        """
        N, D = vectors.shape
        if D != self.dim:
            raise ValueError(f"Vector dim {D} doesn't match config dim {self.dim}")

        # Normalize if requested
        if normalize:
            vectors = self._normalize_vectors(vectors)

        # Default IDs
        if ids is None:
            ids = list(range(N))

        # Create index
        self.index = hnswlib.Index(space="ip", dim=self.dim)  # inner product (cosine if normalized)
        self.index.init_index(
            max_elements=N,
            M=self.M,
            ef_construction=self.ef_construction,
            random_seed=self.seed,
        )

        # Set num threads
        self.index.set_num_threads(self.num_threads)

        # Build in batches
        for start_idx in range(0, N, self.batch_size):
            end_idx = min(start_idx + self.batch_size, N)
            batch_vectors = vectors[start_idx:end_idx]
            batch_ids = ids[start_idx:end_idx]

            self.index.add_items(batch_vectors, batch_ids)

        # Set ef for search
        self.index.set_ef(self.ef_search)

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
            RuntimeError: If index not built yet

        Notes:
            - Checksum used in MANIFEST validation
            - Deterministic: same index → same checksum
        """
        if self.index is None:
            raise RuntimeError("Index not built yet. Call build() first.")

        # Determine path
        if path is None:
            path = Path(self.path_template)
        else:
            path = Path(path)

        # Create directories
        path.parent.mkdir(parents=True, exist_ok=True)

        # Save index
        self.index.save_index(str(path))

        # Compute SHA256
        sha256 = self._compute_sha256(path)

        return path, sha256

    def load(self, path: Path) -> hnswlib.Index:
        """
        Load index from disk.

        Args:
            path: Path to saved index file

        Returns:
            Loaded hnswlib.Index instance

        Notes:
            - Sets ef_search from config
            - Validates index dimensions match config
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Index file not found: {path}")

        # Create index
        self.index = hnswlib.Index(space="ip", dim=self.dim)

        # Load from disk
        self.index.load_index(str(path))

        # Set ef for search
        self.index.set_ef(self.ef_search)
        self.index.set_num_threads(self.num_threads)

        self.num_elements = self.index.get_current_count()

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
            Tuple of (labels, distances) arrays
            - labels: (Q, k) array of neighbor IDs
            - distances: (Q, k) array of distances (1 - cosine_sim if normalized)

        Raises:
            RuntimeError: If index not loaded/built

        Notes:
            - Deterministic: same query → same results (for fixed index)
            - ef_search controls recall/speed tradeoff
        """
        if self.index is None:
            raise RuntimeError("Index not loaded. Call load() or build() first.")

        # Normalize if requested
        if normalize:
            query_vectors = self._normalize_vectors(query_vectors)

        # Search
        labels, distances = self.index.knn_query(query_vectors, k=k)

        return labels, distances

    def _normalize_vectors(self, vectors: np.ndarray) -> np.ndarray:
        """
        L2-normalize vectors.

        Args:
            vectors: (N, dim) array

        Returns:
            L2-normalized (N, dim) array

        Notes:
            - Clips outliers before normalization (from config)
            - Adds tolerance to avoid division by zero
        """
        norm_cfg = self.config["normalization"]
        clip_value = norm_cfg["clip_value"]
        tolerance = norm_cfg["tolerance"]

        # Clip outliers
        vectors = np.clip(vectors, -clip_value, clip_value)

        # L2 normalize
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.maximum(norms, float(tolerance))  # Avoid division by zero

        return vectors / norms

    def _compute_sha256(self, path: Path) -> str:
        """
        Compute SHA256 checksum of index file.

        Args:
            path: Path to index file

        Returns:
            Hex-encoded SHA256 checksum

        Notes:
            - Used in MANIFEST validation
            - Deterministic: same file → same checksum
        """
        sha256_hash = hashlib.sha256()

        with open(path, "rb") as f:
            # Read in chunks for memory efficiency
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)

        return sha256_hash.hexdigest()

    def get_stats(self) -> Dict:
        """
        Get index statistics.

        Returns:
            Dict with num_elements, M, ef_search, etc.
        """
        if self.index is None:
            return {"built": False}

        return {
            "built": True,
            "level": self.level,
            "num_elements": self.num_elements,
            "dim": self.dim,
            "M": self.M,
            "ef_construction": self.ef_construction,
            "ef_search": self.ef_search,
            "seed": self.seed,
            "metric": self.metric,
        }


def create_hnsw_index(
    level: str,
    vectors: np.ndarray,
    ids: Optional[List[int]] = None,
    save_path: Optional[Path] = None,
) -> Tuple[hnswlib.Index, Path, str]:
    """
    Convenience function to build, save, and return HNSW index.

    Args:
        level: "sentence" or "paragraph"
        vectors: (N, dim) embeddings
        ids: Optional IDs (defaults to 0..N-1)
        save_path: Optional save path (defaults to config)

    Returns:
        Tuple of (index, saved_path, sha256_checksum)

    Example:
        >>> vectors = np.random.randn(1000, 384)
        >>> index, path, sha256 = create_hnsw_index("sentence", vectors)
        >>> print(f"Saved to {path}, SHA256: {sha256[:16]}...")
    """
    builder = HNSWIndexBuilder(level)
    index = builder.build(vectors, ids=ids, normalize=True)
    path, sha256 = builder.save(save_path)

    return index, path, sha256
