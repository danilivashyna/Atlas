# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
TextEncoder5D - MiniLM 384D → 5D text encoder with PCA projection.

This module provides text encoding functionality that:
1. Uses sentence-transformers/all-MiniLM-L6-v2 (384D embeddings)
2. Projects embeddings to 5D space using PCA
3. Normalizes output to [-1, 1] range

Falls back to SimpleSemanticEncoder if sentence-transformers is not available.
"""

from typing import Union, List, Optional
import numpy as np
import warnings

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from sklearn.decomposition import PCA
    SKLEARN_AVAILABLE = True
except ImportError:
    PCA = None
    SKLEARN_AVAILABLE = False

# Import fallback encoder
try:
    from atlas.encoder import SimpleSemanticEncoder
    FALLBACK_AVAILABLE = True
except ImportError:
    SimpleSemanticEncoder = None
    FALLBACK_AVAILABLE = False


class TextEncoder5D:
    """
    Text encoder that compresses text into 5-dimensional semantic space.
    
    Uses sentence-transformers MiniLM model (384D) and projects to 5D
    using PCA. Output is normalized to [-1, 1] range.
    
    If sentence-transformers is not available or model loading fails,
    falls back to SimpleSemanticEncoder.
    
    Example:
        >>> encoder = TextEncoder5D()
        >>> vector = encoder.encode("Hello world")
        >>> len(vector)
        5
        >>> all(-1 <= v <= 1 for v in vector)
        True
    """
    
    def __init__(
        self, 
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        dimension: int = 5,
        normalize_method: str = "tanh",  # "tanh" or "unit_norm"
        pca_samples: int = 1000,
        device: Optional[str] = None,
        use_fallback: bool = True
    ):
        """
        Initialize the text encoder.
        
        Args:
            model_name: Sentence transformer model to use
            dimension: Target dimension (default: 5)
            normalize_method: "tanh" for [-1, 1] or "unit_norm" for L2 normalization
            pca_samples: Number of samples to initialize PCA (if needed)
            device: Device to use (cpu/cuda), None for auto
            use_fallback: If True, use SimpleSemanticEncoder as fallback
        """
        self.model_name = model_name
        self.dimension = dimension
        self.normalize_method = normalize_method
        self.device = device
        self.model = None
        self.embedding_dim = None
        self.pca = None
        self._pca_fitted = False
        self._pca_samples = pca_samples
        self._sample_cache = []
        self._using_fallback = False
        self._fallback_encoder = None
        
        # Try to load sentence transformer model
        if SENTENCE_TRANSFORMERS_AVAILABLE and SKLEARN_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name, device=device)
                self.embedding_dim = self.model.get_sentence_embedding_dimension()
                self.pca = PCA(n_components=dimension, random_state=42)
            except Exception as e:
                if use_fallback:
                    warnings.warn(
                        f"Failed to load sentence-transformers model: {e}. "
                        f"Falling back to SimpleSemanticEncoder.",
                        RuntimeWarning
                    )
                    self._using_fallback = True
                else:
                    raise
        else:
            if use_fallback:
                warnings.warn(
                    "sentence-transformers or scikit-learn not available. "
                    "Falling back to SimpleSemanticEncoder.",
                    RuntimeWarning
                )
                self._using_fallback = True
            else:
                if not SENTENCE_TRANSFORMERS_AVAILABLE:
                    raise ImportError(
                        "sentence-transformers is required for TextEncoder5D. "
                        "Install with: pip install sentence-transformers"
                    )
                if not SKLEARN_AVAILABLE:
                    raise ImportError(
                        "scikit-learn is required for TextEncoder5D. "
                        "Install with: pip install scikit-learn"
                    )
        
        # Initialize fallback encoder if needed
        if self._using_fallback:
            if FALLBACK_AVAILABLE:
                self._fallback_encoder = SimpleSemanticEncoder()
            else:
                raise ImportError(
                    "Fallback encoder (SimpleSemanticEncoder) not available. "
                    "Cannot initialize TextEncoder5D."
                )
    
    def _fit_pca_if_needed(self, embeddings: np.ndarray):
        """
        Fit PCA on collected samples if not already fitted.
        
        Args:
            embeddings: Embeddings to add to sample cache
        """
        if self._using_fallback or self._pca_fitted:
            return
        
        # Add to cache
        if len(embeddings.shape) == 1:
            embeddings = embeddings.reshape(1, -1)
        
        self._sample_cache.extend(embeddings)
        
        # Fit PCA when we have enough samples
        if len(self._sample_cache) >= min(self._pca_samples, 100):
            # Take a subset for fitting
            samples = np.array(self._sample_cache[:self._pca_samples])
            self.pca.fit(samples)
            self._pca_fitted = True
            self._sample_cache = []  # Clear cache
    
    def encode_text(
        self, 
        text: Union[str, List[str]], 
        normalize: bool = True,
        batch_size: int = 32
    ) -> np.ndarray:
        """
        Encode text into 5D semantic space.
        
        Args:
            text: Input text or list of texts
            normalize: Whether to normalize vectors
            batch_size: Batch size for encoding
            
        Returns:
            5D semantic vector(s) as numpy array
            
        Raises:
            ValueError: If text is empty or None
        """
        # Use fallback encoder if available
        if self._using_fallback:
            return self._fallback_encoder.encode_text(text)
        
        # Validate input
        if isinstance(text, str):
            if not text or not text.strip():
                raise ValueError("Input text cannot be empty")
            texts = [text]
            single_input = True
        else:
            if not text:
                raise ValueError("Input text list cannot be empty")
            if any(not t or not t.strip() for t in text):
                raise ValueError("Input text list contains empty strings")
            texts = text
            single_input = False
        
        # Get embeddings from sentence transformer
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=False
        )
        
        # Ensure 2D shape
        if len(embeddings.shape) == 1:
            embeddings = embeddings.reshape(1, -1)
        
        # Fit PCA if needed (lazy initialization)
        self._fit_pca_if_needed(embeddings)
        
        # Project to 5D using PCA
        if self._pca_fitted:
            vectors_5d = self.pca.transform(embeddings)
        else:
            # If PCA not fitted yet, use random projection as fallback
            # This ensures we always return something, even for first few samples
            random_proj = np.random.randn(self.embedding_dim, self.dimension)
            random_proj = random_proj / np.linalg.norm(random_proj, axis=0, keepdims=True)
            vectors_5d = embeddings @ random_proj
        
        # Normalize output
        if normalize:
            if self.normalize_method == "tanh":
                # Scale to [-1, 1] using tanh
                vectors_5d = np.tanh(vectors_5d)
            elif self.normalize_method == "unit_norm":
                # L2 normalization
                norms = np.linalg.norm(vectors_5d, axis=1, keepdims=True)
                vectors_5d = vectors_5d / (norms + 1e-9)
            else:
                raise ValueError(f"Unknown normalize_method: {self.normalize_method}")
        
        # Return single vector or batch
        return vectors_5d[0] if single_input else vectors_5d
    
    def encode(self, text: Union[str, List[str]], **kwargs) -> np.ndarray:
        """
        Alias for encode_text for compatibility.
        
        Args:
            text: Input text or list of texts
            **kwargs: Additional arguments passed to encode_text
            
        Returns:
            5D semantic vector(s)
        """
        return self.encode_text(text, **kwargs)
    
    def __call__(self, text: Union[str, List[str]], **kwargs) -> np.ndarray:
        """
        Make encoder callable.
        
        Args:
            text: Input text or list of texts
            **kwargs: Additional arguments passed to encode_text
            
        Returns:
            5D semantic vector(s)
        """
        return self.encode_text(text, **kwargs)
    
    @property
    def is_fitted(self) -> bool:
        """Check if PCA projection is fitted."""
        if self._using_fallback:
            return True  # Fallback encoder is always "fitted"
        return self._pca_fitted
    
    @property
    def using_fallback(self) -> bool:
        """Check if using fallback encoder."""
        return self._using_fallback
    
    def get_projection_matrix(self) -> Optional[np.ndarray]:
        """
        Get the PCA projection matrix.
        
        Returns:
            PCA components matrix if fitted, None otherwise
        """
        if self._using_fallback:
            return None
        if self._pca_fitted:
            return self.pca.components_
        return None
