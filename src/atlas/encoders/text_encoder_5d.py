# SPDX-License-Identifier: AGPL-3.0-or-later
"""
TextEncoder5D: BERT-based text encoder producing 5D vectors.

Uses sentence-transformers/all-MiniLM-L6-v2 for efficient semantic encoding.
Falls back to MVP deterministic encoding if transformers unavailable.

Example:
    >>> encoder = TextEncoder5D()
    >>> vec = encoder.encode("Hello, world!")
    >>> len(vec)
    5
    >>> import numpy as np
    >>> np.linalg.norm(vec)  # L2-normalized
    1.0
"""

from typing import List, Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Global singleton for lazy loading
_ENCODER_INSTANCE = None
_TRANSFORMERS_AVAILABLE = True


class TextEncoder5D:
    """
    BERT-based 5D text encoder using sentence-transformers/all-MiniLM-L6-v2.

    The encoder:
    - Lazily loads the BERT model on first encode call
    - Caches embeddings for repeated queries
    - Returns L2-normalized 5D vectors
    - Gracefully falls back to MVP if transformers unavailable
    - Targets p95 latency < 80ms on CPU (warm start)
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize TextEncoder5D.

        Args:
            model_name: HuggingFace model identifier for sentence embeddings.
                       Default: MiniLM (6.7M params, ~40ms latency CPU)
        """
        self.model_name = model_name
        self._model = None
        self._cache = {}

    def encode(self, text: str) -> List[float]:
        """
        Encode text to 5D vector (L2-normalized).

        Args:
            text: Input text to encode.

        Returns:
            List of 5 floats, L2-norm = 1.0.
            If BERT unavailable, returns MVP deterministic vector.

        Raises:
            ValueError: If text is None.
        """
        if text is None:
            raise ValueError("Text cannot be None")

        # Check cache
        if text in self._cache:
            return self._cache[text].copy()

        try:
            # Lazy load BERT model
            if self._model is None:
                self._load_model()

            # Encode with BERT
            vector = self._encode_with_bert(text)

        except Exception as e:
            # Fallback to MVP
            logger.warning(f"BERT encoding failed: {e}. Using MVP fallback.")
            vector = self._encode_mvp(text)

        # Ensure L2-normalized
        vector = np.array(vector, dtype=np.float32)
        norm = np.linalg.norm(vector)
        if norm > 1e-8:
            vector = vector / norm
        else:
            # Handle zero vector case (should not happen with BERT)
            vector = np.array([0.2, 0.2, 0.2, 0.2, 0.2], dtype=np.float32)

        # Cache result
        self._cache[text] = vector.copy()

        return vector.tolist()

    def _load_model(self):
        """Lazy load sentence-transformers model (singleton)."""
        global _ENCODER_INSTANCE, _TRANSFORMERS_AVAILABLE

        if not _TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers not available")

        try:
            from sentence_transformers import SentenceTransformer

            if _ENCODER_INSTANCE is None:
                logger.info(f"Loading BERT model: {self.model_name}")
                _ENCODER_INSTANCE = SentenceTransformer(self.model_name, device="cpu")  # Force CPU
                logger.info("BERT model loaded successfully")

            self._model = _ENCODER_INSTANCE

        except ImportError:
            _TRANSFORMERS_AVAILABLE = False
            raise ImportError(
                "sentence-transformers required. "
                "Install: pip install sentence-transformers torch"
            )

    def _encode_with_bert(self, text: str) -> np.ndarray:
        """
        Encode text using BERT (1536D → project to 5D).

        Args:
            text: Input text.

        Returns:
            5D numpy array (not normalized here).
        """
        # Get 384D embedding from MiniLM
        embedding = self._model.encode([text], convert_to_numpy=True)  # (1, 384)
        embedding = embedding[0]  # (384,)

        # Project 384D → 5D using deterministic PCA-like reduction
        # For now, use dimensionality reduction via covariance matrix
        # In production, train a linear projection matrix

        # Simple approach: take top 5 principal components via sampling
        vector_5d = self._reduce_to_5d(embedding)

        return vector_5d

    def _reduce_to_5d(self, vec: np.ndarray) -> np.ndarray:
        """
        Reduce 384D embedding to 5D via deterministic projection.

        This is a placeholder; in production, use PCA or learned projection.

        Args:
            vec: 384D numpy array.

        Returns:
            5D numpy array.
        """
        # Simple deterministic approach: group dimensions and average
        # Divide 384D into 5 groups of ~77D each, take mean and variance

        chunks = np.array_split(vec, 5)
        result = np.array([np.mean(chunk) for chunk in chunks], dtype=np.float32)

        return result

    def _encode_mvp(self, text: str) -> np.ndarray:
        """
        MVP fallback: deterministic 5D encoding without BERT.

        Args:
            text: Input text.

        Returns:
            5D numpy array (deterministic, based on text hash).
        """
        # Hash-based deterministic vector
        import hashlib

        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        np.random.seed(hash_val % (2**32))  # Deterministic seed
        vector = np.random.randn(5).astype(np.float32)

        return vector


__all__ = ["TextEncoder5D"]
