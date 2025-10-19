# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Pydantic models for API request/response validation
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
import uuid
from datetime import datetime


class EncodeRequest(BaseModel):
    """Request model for /encode endpoint"""
    text: str = Field(..., min_length=1, max_length=10000, description="Text to encode")
    lang: Optional[str] = Field(None, pattern="^(ru|en)$", description="Language hint: 'ru' or 'en'")
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError("Text cannot be empty or whitespace only")
        return v


class EncodeResponse(BaseModel):
    """Response model for /encode endpoint"""
    vector: List[float] = Field(..., min_length=5, max_length=5, description="5D semantic vector")
    norm: bool = Field(True, description="Whether vector is normalized to [-1, 1]")
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Request trace ID")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z", description="ISO 8601 timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "vector": [-0.462, 0.0, 0.462, 0.0, 0.462],
                "norm": True,
                "trace_id": "req_abc123def456",
                "timestamp": "2025-01-19T12:34:56.789Z"
            }
        }


class DecodeRequest(BaseModel):
    """Request model for /decode endpoint"""
    vector: List[float] = Field(..., min_length=5, max_length=5, description="5D semantic vector to decode")
    top_k: int = Field(3, ge=1, le=10, description="Number of top reasoning dimensions to return")
    
    @field_validator('vector')
    @classmethod
    def validate_vector(cls, v):
        if len(v) != 5:
            raise ValueError("Vector must have exactly 5 dimensions")
        # Check for NaN/Inf
        import math
        if any(math.isnan(x) or math.isinf(x) for x in v):
            raise ValueError("Vector cannot contain NaN or Inf values")
        # Warn if values outside [-1, 1]
        if any(abs(x) > 1.0 for x in v):
            # Just a warning, we'll clip values
            pass
        return v


class DimensionReasoning(BaseModel):
    """Reasoning for a single dimension"""
    dim: int = Field(..., ge=0, le=4, description="Dimension index (0-4)")
    weight: float = Field(..., description="Weight/importance of this dimension")
    label: str = Field(..., description="Human-readable dimension label")
    evidence: List[str] = Field(default_factory=list, description="Supporting evidence (words/features)")


class DecodeResponse(BaseModel):
    """Response model for /decode endpoint"""
    text: str = Field(..., description="Decoded text")
    reasoning: List[DimensionReasoning] = Field(default_factory=list, description="Dimension reasoning")
    explainable: bool = Field(True, description="Whether reasoning is available")
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Request trace ID")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z", description="ISO 8601 timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "Собака",
                "reasoning": [
                    {
                        "dim": 2,
                        "weight": 0.9,
                        "label": "живость/движение",
                        "evidence": ["бежать", "лай"]
                    },
                    {
                        "dim": 4,
                        "weight": 0.8,
                        "label": "домашнее",
                        "evidence": ["дома", "хозяин"]
                    }
                ],
                "explainable": True,
                "trace_id": "req_xyz789abc012",
                "timestamp": "2025-01-19T12:34:56.789Z"
            }
        }


class ExplainRequest(BaseModel):
    """Request model for /explain endpoint"""
    text: str = Field(..., min_length=1, max_length=10000, description="Text to explain")
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError("Text cannot be empty or whitespace only")
        return v


class DimensionExplanation(BaseModel):
    """Explanation of a dimension's contribution"""
    i: int = Field(..., ge=0, le=4, description="Dimension index")
    label: str = Field(..., description="Dimension semantic label")
    score: float = Field(..., description="Dimension value")
    examples: List[str] = Field(default_factory=list, description="Example words for this dimension")


class ExplainResponse(BaseModel):
    """Response model for /explain endpoint"""
    vector: List[float] = Field(..., min_length=5, max_length=5, description="Encoded 5D vector")
    dims: List[DimensionExplanation] = Field(..., description="Per-dimension explanations")
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Request trace ID")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z", description="ISO 8601 timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "vector": [-0.462, 0.0, 0.462, 0.0, 0.462],
                "dims": [
                    {
                        "i": 0,
                        "label": "объект/действие",
                        "score": -0.462,
                        "examples": ["собака", "кот", "дерево"]
                    },
                    {
                        "i": 2,
                        "label": "конкретность",
                        "score": 0.462,
                        "examples": ["собака", "дом", "машина"]
                    }
                ],
                "trace_id": "req_aaa111bbb222",
                "timestamp": "2025-01-19T12:34:56.789Z"
            }
        }


class ErrorResponse(BaseModel):
    """Error response model"""
    error: bool = Field(True, description="Always true for error responses")
    error_type: str = Field(..., description="Error type (ValueError, RuntimeError, etc.)")
    message: str = Field(..., description="Human-readable error message")
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Request trace ID for debugging")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z", description="ISO 8601 timestamp")
    debug_info: Optional[Dict[str, Any]] = Field(None, description="Additional debug information")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": True,
                "error_type": "ValueError",
                "message": "Input text cannot be empty",
                "trace_id": "req_err123",
                "timestamp": "2025-01-19T12:34:56.789Z",
                "debug_info": {
                    "input_length": 0,
                    "expected_length": "> 0"
                }
            }
        }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field("ok", description="Service status")
    version: str = Field("0.1.0", description="Atlas version")
    model_loaded: bool = Field(True, description="Whether model is loaded and ready")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class MetricsResponse(BaseModel):
    """Metrics response (Prometheus-compatible)"""
    requests_total: int = Field(0, description="Total number of requests")
    requests_by_endpoint: Dict[str, int] = Field(default_factory=dict, description="Requests per endpoint")
    avg_latency_ms: Dict[str, float] = Field(default_factory=dict, description="Average latency per endpoint")
    errors_total: int = Field(0, description="Total number of errors")
