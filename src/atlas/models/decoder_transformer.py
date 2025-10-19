# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna
#
# Atlas - Semantic Space Control Panel
# Интерпретируемое семантическое пространство

"""
Interpretable Transformer-based decoder for v0.2+
Decodes 5D vectors back to text with reasoning
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import torch
import torch.nn as nn


@dataclass
class DecoderConfig:
    """Configuration for interpretable decoder"""
    vocab_size: int = 30000
    hidden_dim: int = 384
    n_layers: int = 4
    n_heads: int = 6
    max_seq_len: int = 128
    device: str = "cpu"


class InterpretableDecoder(nn.Module):
    """
    Transformer-based decoder conditioned on 5D semantic vectors.
    
    Architecture:
    - Condition embedding: R^5 -> R^H (via linear layer)
    - Token embeddings: token_id -> R^H
    - Transformer encoder: attends to condition + tokens
    - Output head: R^H -> vocab_size (logits)
    
    For MVP (v0.2), this is a toy implementation that demonstrates:
    - How condition affects decoding
    - Interpretable reasoning through attention
    - Flexible manipulation of semantic dimensions
    
    Future (v0.3+): Replace with GPT-like autoregressive decoder
    
    Example:
        >>> cfg = DecoderConfig(device="cpu")
        >>> decoder = InterpretableDecoder(cfg)
        >>> vec5 = [0.1, 0.9, -0.5, 0.2, 0.8]
        >>> result = decoder.decode(vec5)
        >>> print(result['text'])
        '«DECODED_TEXT_MVP»'
    """

    def __init__(self, cfg: DecoderConfig):
        super().__init__()
        self.cfg = cfg
        self.device = torch.device(cfg.device)
        
        # Embeddings
        self.embed = nn.Embedding(cfg.vocab_size, cfg.hidden_dim)
        
        # Condition projection: R^5 -> R^hidden_dim
        self.condition_proj = nn.Linear(5, cfg.hidden_dim)
        
        # Positional encoding
        self.pos_embed = nn.Embedding(cfg.max_seq_len, cfg.hidden_dim)
        
        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=cfg.hidden_dim,
            nhead=cfg.n_heads,
            batch_first=True,
            dropout=0.1
        )
        self.transformer = nn.TransformerEncoder(
            encoder_layer,
            num_layers=cfg.n_layers
        )
        
        # Output head: hidden -> vocab
        self.lm_head = nn.Linear(cfg.hidden_dim, cfg.vocab_size)
        
        self.to(self.device)

    def forward(
        self,
        vec5: torch.Tensor,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Forward pass: encode 5D vector + tokens, return logits.
        
        Args:
            vec5: (B, 5) semantic vector
            input_ids: (B, T) token indices
            attention_mask: (B, T) mask for padding tokens
            
        Returns:
            logits: (B, T, vocab_size) unnormalized predictions
        """
        batch_size, seq_len = input_ids.shape
        
        # Project condition: (B, 5) -> (B, 1, H)
        cond_h = self.condition_proj(vec5)  # (B, H)
        cond_h = cond_h.unsqueeze(1)  # (B, 1, H)
        
        # Token embeddings: (B, T) -> (B, T, H)
        tok_h = self.embed(input_ids)
        
        # Add positional embeddings
        positions = torch.arange(seq_len, device=self.device).unsqueeze(0)
        tok_h = tok_h + self.pos_embed(positions)
        
        # Concatenate condition and tokens: (B, T+1, H)
        x = torch.cat([cond_h, tok_h], dim=1)
        
        # Extend attention mask if provided
        if attention_mask is not None:
            # Prepend 1 for condition token
            cond_mask = torch.ones(batch_size, 1, device=self.device)
            extended_mask = torch.cat([cond_mask, attention_mask.float()], dim=1)
            attention_mask = (extended_mask == 0)  # Invert for Transformer
        
        # Transformer
        y = self.transformer(x, src_key_padding_mask=attention_mask)
        
        # LM head (skip condition token)
        logits = self.lm_head(y[:, 1:, :])  # (B, T, vocab_size)
        
        return logits

    @torch.no_grad()
    def decode(
        self,
        vec5: List[float],
        max_tokens: int = 20,
        temperature: float = 1.0,
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        Decode 5D vector to text with interpretable reasoning.
        
        Args:
            vec5: List/array of 5 floats
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_k: Top-k for filtering candidates
            
        Returns:
            Dict with:
                - 'text': decoded text string
                - 'reasoning': list of {dim, weight, note}
                - 'confidence': float in [0, 1]
                - 'schema': 'atlas-decoder-2'
        """
        # For MVP: we don't do real generation yet
        # Just return reasoning based on the 5D vector
        
        weights = [round(float(v), 3) for v in vec5]
        
        # Interpret dimensions
        dim_labels = [
            "Object↔Action",
            "Positive↔Negative",
            "Abstract↔Concrete",
            "I↔World",
            "Living↔Mechanical"
        ]
        
        reasoning = []
        for i, (w, label) in enumerate(zip(weights, dim_labels)):
            strength = abs(w)
            direction = "+" if w > 0 else "-" if w < 0 else "0"
            
            reasoning.append({
                "dim": i + 1,
                "weight": w,
                "label": label,
                "strength": round(strength, 2),
                "direction": direction,
                "note": "mvp-decoder-v0.2"
            })
        
        # Calculate confidence as average normalization
        confidence = sum(1 - abs(w) for w in weights) / 5.0
        
        return {
            "text": "«DECODED_TEXT_MVP»",
            "reasoning": reasoning,
            "confidence": round(confidence, 2),
            "schema": "atlas-decoder-2",
            "notice": "MVP decoder (v0.2) - full neural decoder coming in v0.3"
        }

    def get_attention_weights(self) -> Optional[torch.Tensor]:
        """Extract attention weights from transformer (debug feature)"""
        # This would be populated if we hook into transformer attention
        # Placeholder for future implementation
        return None

    def set_temperature(self, temperature: float):
        """Set sampling temperature for generation"""
        if not 0 < temperature:
            raise ValueError(f"Temperature must be > 0, got {temperature}")
        self.temperature = temperature

    def to_device(self, device: str):
        """Move model to device"""
        self.device = torch.device(device)
        self.to(self.device)
