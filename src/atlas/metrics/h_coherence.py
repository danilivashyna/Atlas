"""
Atlas β — H-Coherence Metric

Measures semantic alignment between adjacent hierarchical levels.
Formula: coherence(L1, L2) = mean(cos(v_L1_i, v_L2_parent(i))) for all i

Coherence targets (from h_metrics.yaml):
- sent → para: ≥0.78 (warning: 0.70, critical: 0.65)
- para → doc: ≥0.80 (warning: 0.72, critical: 0.68)

⚠️ Safety: Read-only metric (no state mutation), config-driven thresholds.

Version: 0.2.0-beta
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from atlas.configs import ConfigLoader


@dataclass
class HCoherenceResult:
    """
    Result of H-Coherence computation.

    Attributes:
        level_pair: Tuple of (lower_level, upper_level)
        coherence: Average cosine similarity
        num_samples: Number of vector pairs measured
        status: "healthy" | "warning" | "critical"
        target: Target threshold from config
        warning: Warning threshold from config
        critical: Critical threshold from config
    """
    level_pair: Tuple[str, str]
    coherence: float
    num_samples: int
    status: str
    target: float
    warning: float
    critical: float


class HCoherenceMetric:
    """
    H-Coherence metric computation.

    Measures alignment between hierarchical levels:
    - Sentence → Paragraph: Do sentence embeddings align with their paragraph?
    - Paragraph → Document: Do paragraph embeddings align with their document?

    ⚠️ Safety:
    - Read-only (no state mutation)
    - Config-driven thresholds
    - Deterministic (same vectors → same coherence)
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize H-Coherence metric.

        Args:
            config: Optional config dict (defaults to ConfigLoader)
        """
        self.config = config or ConfigLoader.get_metrics_config()
        self.h_coherence_cfg = self.config["h_coherence"]

    def compute_sent_to_para(
        self,
        sent_vectors: np.ndarray,
        para_vectors: np.ndarray,
        sent_to_para_map: List[int],
    ) -> HCoherenceResult:
        """
        Compute H-Coherence for sentence → paragraph.

        Args:
            sent_vectors: Sentence-level embeddings (N, dim)
            para_vectors: Paragraph-level embeddings (M, dim)
            sent_to_para_map: Mapping sent_idx → para_idx (length N)

        Returns:
            HCoherenceResult with coherence score and status

        Notes:
            - Vectors should be L2-normalized
            - coherence = mean(cos(sent_i, para_parent(i)))

        Example:
            >>> sent_vecs = np.random.randn(100, 384)  # 100 sentences
            >>> para_vecs = np.random.randn(20, 384)   # 20 paragraphs
            >>> mapping = [i // 5 for i in range(100)]  # 5 sents per para
            >>> result = metric.compute_sent_to_para(sent_vecs, para_vecs, mapping)
            >>> print(f"Coherence: {result.coherence:.3f}, Status: {result.status}")
        """
        # Get thresholds from config
        cfg = self.h_coherence_cfg["sent_to_para"]
        target = cfg["target"]
        warning = cfg["warning"]
        critical = cfg["critical"]

        # Normalize vectors
        sent_vectors = self._normalize(sent_vectors)
        para_vectors = self._normalize(para_vectors)

        # Compute coherence
        coherences = []
        for sent_idx, para_idx in enumerate(sent_to_para_map):
            if para_idx < 0 or para_idx >= len(para_vectors):
                continue  # Skip invalid mappings

            sent_vec = sent_vectors[sent_idx]
            para_vec = para_vectors[para_idx]

            cos_sim = np.dot(sent_vec, para_vec)
            coherences.append(cos_sim)

        # Average coherence
        avg_coherence = float(np.mean(coherences))

        # Determine status
        if avg_coherence >= target:
            status = "healthy"
        elif avg_coherence >= warning:
            status = "warning"
        else:
            status = "critical"

        return HCoherenceResult(
            level_pair=("sentence", "paragraph"),
            coherence=avg_coherence,
            num_samples=len(coherences),
            status=status,
            target=target,
            warning=warning,
            critical=critical,
        )

    def compute_para_to_doc(
        self,
        para_vectors: np.ndarray,
        doc_vectors: np.ndarray,
        para_to_doc_map: List[int],
    ) -> HCoherenceResult:
        """
        Compute H-Coherence for paragraph → document.

        Args:
            para_vectors: Paragraph-level embeddings (N, dim)
            doc_vectors: Document-level embeddings (M, dim)
            para_to_doc_map: Mapping para_idx → doc_idx (length N)

        Returns:
            HCoherenceResult with coherence score and status

        Notes:
            - Vectors should be L2-normalized
            - coherence = mean(cos(para_i, doc_parent(i)))
        """
        # Get thresholds from config
        cfg = self.h_coherence_cfg["para_to_doc"]
        target = cfg["target"]
        warning = cfg["warning"]
        critical = cfg["critical"]

        # Normalize vectors
        para_vectors = self._normalize(para_vectors)
        doc_vectors = self._normalize(doc_vectors)

        # Compute coherence
        coherences = []
        for para_idx, doc_idx in enumerate(para_to_doc_map):
            if doc_idx < 0 or doc_idx >= len(doc_vectors):
                continue  # Skip invalid mappings

            para_vec = para_vectors[para_idx]
            doc_vec = doc_vectors[doc_idx]

            cos_sim = np.dot(para_vec, doc_vec)
            coherences.append(cos_sim)

        # Average coherence
        avg_coherence = float(np.mean(coherences))

        # Determine status
        if avg_coherence >= target:
            status = "healthy"
        elif avg_coherence >= warning:
            status = "warning"
        else:
            status = "critical"

        return HCoherenceResult(
            level_pair=("paragraph", "document"),
            coherence=avg_coherence,
            num_samples=len(coherences),
            status=status,
            target=target,
            warning=warning,
            critical=critical,
        )

    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        """
        L2-normalize vectors.

        Args:
            vectors: Input vectors (N, dim)

        Returns:
            Normalized vectors (N, dim)

        Notes:
            - Handles zero vectors (returns unchanged)
            - Same as HNSW normalization
        """
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-6)  # Avoid division by zero
        return vectors / norms


def compute_h_coherence(
    sent_vectors: np.ndarray,
    para_vectors: np.ndarray,
    doc_vectors: np.ndarray,
    sent_to_para_map: List[int],
    para_to_doc_map: List[int],
) -> Tuple[HCoherenceResult, HCoherenceResult]:
    """
    Compute H-Coherence for both level pairs.

    Args:
        sent_vectors: Sentence embeddings (N, 384)
        para_vectors: Paragraph embeddings (M, 384)
        doc_vectors: Document embeddings (K, 768)
        sent_to_para_map: Mapping sent_idx → para_idx
        para_to_doc_map: Mapping para_idx → doc_idx

    Returns:
        Tuple of (sent_to_para_result, para_to_doc_result)

    Example:
        >>> sent_vecs = np.random.randn(100, 384)
        >>> para_vecs = np.random.randn(20, 384)
        >>> doc_vecs = np.random.randn(5, 768)
        >>> sent_map = [i // 5 for i in range(100)]  # 5 sents per para
        >>> para_map = [i // 4 for i in range(20)]   # 4 paras per doc
        >>> sp_result, pd_result = compute_h_coherence(
        ...     sent_vecs, para_vecs, doc_vecs, sent_map, para_map
        ... )
        >>> print(f"Sent→Para: {sp_result.coherence:.3f}")
        >>> print(f"Para→Doc: {pd_result.coherence:.3f}")
    """
    metric = HCoherenceMetric()

    sent_to_para_result = metric.compute_sent_to_para(
        sent_vectors, para_vectors, sent_to_para_map
    )

    para_to_doc_result = metric.compute_para_to_doc(
        para_vectors, doc_vectors, para_to_doc_map
    )

    return sent_to_para_result, para_to_doc_result
