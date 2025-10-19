# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna
#
# Atlas - Semantic Space Control Panel
# Интерпретируемое семантическое пространство

"""
BERT-based neural encoder for v0.2+
Encodes text into 5D semantic space using sentence transformers
"""

from dataclasses import dataclass
from typing import List, Optional
import torch
import torch.nn as nn

try:
    from transformers import AutoTokenizer, AutoModel
except ImportError:
    AutoTokenizer = None
    AutoModel = None


@dataclass
class BertEncoderConfig:
    """Configuration for BERT encoder"""
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    proj_dim: int = 5
    proj_ortho: bool = True
    device: str = "cpu"
    normalize: bool = True


class TextEncoder5D(nn.Module):
    """
    BERT-based encoder that projects text into 5D semantic space.
    
    Features:
    - Uses pre-trained sentence transformers (HuggingFace)
    - Projects hidden states to 5D space
    - Optional orthogonal projection matrix
    - L2 normalization support
    
    Example:
        >>> cfg = BertEncoderConfig(device="cpu")
        >>> encoder = TextEncoder5D(cfg)
        >>> vec = encoder.encode("Собака")
        >>> len(vec)
        5
        >>> abs(sum(v**2 for v in vec)**0.5 - 1.0) < 1e-5  # normalized
        True
    """

    def __init__(self, cfg: BertEncoderConfig):
        super().__init__()
        
        if AutoTokenizer is None or AutoModel is None:
            raise ImportError(
                "transformers library is required for BERT encoder. "
                "Install with: pip install transformers"
            )
        
        self.cfg = cfg
        self.device = torch.device(cfg.device)
        
        # Load pre-trained model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(cfg.model_name)
        self.backbone = AutoModel.from_pretrained(cfg.model_name)
        
        # Get hidden dimension from backbone
        hidden_dim = self.backbone.config.hidden_size
        
        # Projection layer: hidden_dim -> 5D
        self.proj = nn.Linear(hidden_dim, cfg.proj_dim, bias=False)
        
        # Move to device
        self.backbone.to(self.device)
        self.proj.to(self.device)
        
        # Freeze backbone (inference-only for MVP)
        self.backbone.eval()
        for param in self.backbone.parameters():
            param.requires_grad = False

    @torch.no_grad()
    def encode(self, text: str, truncate: bool = True, max_length: int = 256) -> List[float]:
        """
        Encode text into 5D semantic vector.
        
        Args:
            text: Input text string
            truncate: Whether to truncate to max_length
            max_length: Maximum token length
            
        Returns:
            List of 5 floats in [-1, 1] range (if normalized)
            
        Raises:
            ValueError: If text is empty
        """
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty")
        
        # Tokenize
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=truncate,
            max_length=max_length,
            padding=True
        )
        
        # Move to device
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Forward pass through BERT
        with torch.no_grad():
            outputs = self.backbone(**inputs)
        
        # Use [CLS] token (first token)
        cls_embedding = outputs.last_hidden_state[:, 0, :]  # (1, hidden_dim)
        
        # Project to 5D
        vec_5d = self.proj(cls_embedding).squeeze(0)  # (5,)
        
        # Normalize if requested
        if self.cfg.normalize:
            vec_5d = vec_5d / (vec_5d.norm(p=2) + 1e-9)
        
        # Clamp to [-1, 1]
        vec_5d = torch.clamp(vec_5d, -1.0, 1.0)
        
        return vec_5d.detach().cpu().tolist()

    def forward(self, text: str) -> List[float]:
        """Alias for encode()"""
        return self.encode(text)

    @property
    def projection_matrix(self) -> torch.Tensor:
        """Get projection matrix for analysis"""
        return self.proj.weight.detach()

    def set_device(self, device: str):
        """Move model to device (cpu/cuda)"""
        self.device = torch.device(device)
        self.backbone.to(self.device)
        self.proj.to(self.device)
