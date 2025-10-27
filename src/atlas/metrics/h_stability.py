"""
Atlas β — H-Stability Metric

Measures robustness of embeddings under perturbations.
Formula: stability = 1 - mean(drift) where drift = 1 - cos(v_orig, v_perturbed)

Stability thresholds (from h_metrics.yaml):
- max_drift: ≤0.08 (cos_sim ≥0.92 after perturbation)
- warning_drift: ≤0.06

⚠️ Safety: Read-only metric (no state mutation), config-driven thresholds.

Version: 0.2.0-beta
"""

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np

from atlas.configs import ConfigLoader


@dataclass
class HStabilityResult:
    """
    Result of H-Stability computation.
    
    Attributes:
        perturbation_type: Type of perturbation tested
        avg_drift: Average drift (1 - cos_sim)
        max_drift: Maximum drift observed
        num_samples: Number of vector pairs tested
        status: "healthy" | "warning" | "critical"
        drift_threshold: Max drift threshold from config
        warning_threshold: Warning drift threshold from config
    """
    perturbation_type: str
    avg_drift: float
    max_drift: float
    num_samples: int
    status: str
    drift_threshold: float
    warning_threshold: float


class HStabilityMetric:
    """
    H-Stability metric computation.
    
    Measures embedding robustness under perturbations:
    - Punctuation changes (low severity)
    - Case changes (low severity)
    - Tokenization changes (medium severity)
    - Character noise (medium severity)
    - Whitespace changes (low severity)
    
    Formula:
    - drift(v1, v2) = 1 - cos(v1, v2)
    - stability = 1 - mean(drift)
    
    ⚠️ Safety:
    - Read-only (no state mutation)
    - Config-driven thresholds
    - Deterministic (same vectors → same drift)
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize H-Stability metric.
        
        Args:
            config: Optional config dict (defaults to ConfigLoader)
        """
        self.config = config or ConfigLoader.get_metrics_config()
        self.h_stability_cfg = self.config["h_stability"]
        
        # Thresholds
        self.max_drift_threshold = self.h_stability_cfg["max_drift"]
        self.warning_drift_threshold = self.h_stability_cfg["warning_drift"]
    
    def compute_drift(
        self,
        original_vectors: np.ndarray,
        perturbed_vectors: np.ndarray,
        perturbation_type: str = "unknown",
    ) -> HStabilityResult:
        """
        Compute drift between original and perturbed embeddings.
        
        Args:
            original_vectors: Original embeddings (N, dim)
            perturbed_vectors: Perturbed embeddings (N, dim)
            perturbation_type: Name of perturbation (for reporting)
        
        Returns:
            HStabilityResult with drift stats and status
        
        Notes:
            - Vectors should be L2-normalized
            - drift = 1 - cos(v_orig, v_perturbed)
            - Lower drift = more stable
        
        Example:
            >>> orig = np.random.randn(100, 384)
            >>> pert = orig + np.random.randn(100, 384) * 0.05  # 5% noise
            >>> result = metric.compute_drift(orig, pert, "noise_5pct")
            >>> print(f"Avg drift: {result.avg_drift:.4f}, Status: {result.status}")
        """
        if original_vectors.shape != perturbed_vectors.shape:
            raise ValueError(
                f"Shape mismatch: {original_vectors.shape} vs {perturbed_vectors.shape}"
            )
        
        # Normalize vectors
        original_vectors = self._normalize(original_vectors)
        perturbed_vectors = self._normalize(perturbed_vectors)
        
        # Compute cosine similarities
        cos_sims = []
        for i in range(len(original_vectors)):
            cos_sim = np.dot(original_vectors[i], perturbed_vectors[i])
            cos_sims.append(cos_sim)
        
        cos_sims = np.array(cos_sims)
        
        # Compute drift
        drifts = 1.0 - cos_sims
        avg_drift = float(np.mean(drifts))
        max_drift_val = float(np.max(drifts))
        
        # Determine status
        if max_drift_val <= self.warning_drift_threshold:
            status = "healthy"
        elif max_drift_val <= self.max_drift_threshold:
            status = "warning"
        else:
            status = "critical"
        
        return HStabilityResult(
            perturbation_type=perturbation_type,
            avg_drift=avg_drift,
            max_drift=max_drift_val,
            num_samples=len(original_vectors),
            status=status,
            drift_threshold=self.max_drift_threshold,
            warning_threshold=self.warning_drift_threshold,
        )
    
    def compute_stability(
        self,
        original_vectors: np.ndarray,
        perturbed_vectors: np.ndarray,
        perturbation_type: str = "unknown",
    ) -> float:
        """
        Compute stability score (1 - avg_drift).
        
        Args:
            original_vectors: Original embeddings (N, dim)
            perturbed_vectors: Perturbed embeddings (N, dim)
            perturbation_type: Name of perturbation
        
        Returns:
            Stability score in [0, 1] (higher = more stable)
        
        Notes:
            - stability = 1 - mean(drift)
            - Perfect stability = 1.0 (no drift)
        """
        result = self.compute_drift(
            original_vectors, perturbed_vectors, perturbation_type
        )
        return 1.0 - result.avg_drift
    
    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        """
        L2-normalize vectors.
        
        Args:
            vectors: Input vectors (N, dim)
        
        Returns:
            Normalized vectors (N, dim)
        """
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-6)  # Avoid division by zero
        return vectors / norms


# ============================================================================
# Perturbation Helpers
# ============================================================================

def add_gaussian_noise(
    vectors: np.ndarray,
    noise_level: float = 0.05,
    seed: Optional[int] = None,
) -> np.ndarray:
    """
    Add Gaussian noise to vectors.
    
    Args:
        vectors: Input vectors (N, dim)
        noise_level: Stddev of noise relative to vector norm
        seed: Random seed for reproducibility
    
    Returns:
        Perturbed vectors (N, dim)
    
    Example:
        >>> orig = np.random.randn(100, 384)
        >>> pert = add_gaussian_noise(orig, noise_level=0.05, seed=42)
        >>> drift = 1 - np.mean([np.dot(o, p) for o, p in zip(orig, pert)])
        >>> print(f"Drift: {drift:.4f}")
    """
    if seed is not None:
        np.random.seed(seed)
    
    noise = np.random.randn(*vectors.shape).astype(vectors.dtype)
    noise *= noise_level
    
    perturbed = vectors + noise
    return perturbed


def compute_h_stability(
    original_vectors: np.ndarray,
    perturbed_vectors: np.ndarray,
    perturbation_type: str = "unknown",
) -> HStabilityResult:
    """
    Compute H-Stability for given perturbation.
    
    Args:
        original_vectors: Original embeddings (N, dim)
        perturbed_vectors: Perturbed embeddings (N, dim)
        perturbation_type: Name of perturbation tested
    
    Returns:
        HStabilityResult with drift stats and status
    
    Example:
        >>> orig = np.random.randn(100, 384)
        >>> pert = add_gaussian_noise(orig, noise_level=0.03, seed=42)
        >>> result = compute_h_stability(orig, pert, "gaussian_3pct")
        >>> print(f"Avg drift: {result.avg_drift:.4f}")
        >>> print(f"Max drift: {result.max_drift:.4f}")
        >>> print(f"Status: {result.status}")
    """
    metric = HStabilityMetric()
    return metric.compute_drift(original_vectors, perturbed_vectors, perturbation_type)
