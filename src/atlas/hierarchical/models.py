# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Pydantic models for hierarchical semantic space (tree@v2 schema)
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime, timezone


class TreeNode(BaseModel):
    """
    Hierarchical tree node representing a semantic dimension and its children.

    This is the core data structure for the "matryoshka 5D" architecture,
    where each node can have 5 child nodes, recursively.
    """

    value: List[float] = Field(
        ..., min_length=5, max_length=5, description="5D semantic vector for this node level"
    )
    label: Optional[str] = Field(
        None, description="Human-readable label for this node (e.g., 'coarse', 'agent/action')"
    )
    children: Optional[List["TreeNode"]] = Field(
        None, max_length=5, description="Optional list of 5 child nodes for fine-grained semantics"
    )
    key: Optional[str] = Field(None, description="Dimension key (e.g., 'dim1', 'dim2.3')")
    weight: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Router weight/confidence for this branch (0-1)"
    )

    @field_validator("value")
    @classmethod
    def validate_value(cls, v):
        import math

        if any(math.isnan(x) or math.isinf(x) for x in v):
            raise ValueError("Vector values cannot contain NaN or Inf")
        if any(abs(x) > 1.0 for x in v):
            raise ValueError("Vector values must be in range [-1, 1]")
        return v

    @field_validator("children")
    @classmethod
    def validate_children(cls, v):
        if v is not None and len(v) != 5:
            raise ValueError("Children must have exactly 5 nodes (one per dimension)")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "value": [0.12, 0.88, -0.41, 0.05, 0.67],
                "label": "coarse",
                "key": "root",
                "weight": 1.0,
                "children": [
                    {
                        "key": "dim1",
                        "value": [0.2, -0.1, 0.6, -0.4, 0.3],
                        "label": "agent/action",
                        "weight": 0.8,
                    }
                ],
            }
        }
    )


class HierarchicalVector(BaseModel):
    """Complete hierarchical vector representation"""

    tree: TreeNode = Field(..., description="Root node of the hierarchical tree")
    norm: bool = Field(True, description="Whether vectors are normalized to [-1, 1]")
    max_depth: int = Field(1, ge=0, le=5, description="Maximum depth of the tree")
    schema_id: str = Field("atlas-hier-2", description="Schema version identifier")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
        description="ISO 8601 timestamp",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tree": {
                    "value": [0.12, 0.88, -0.41, 0.05, 0.67],
                    "label": "coarse",
                    "key": "root",
                },
                "norm": True,
                "max_depth": 1,
                "schema_id": "atlas-hier-2",
                "created_at": "2025-01-19T12:34:56.789Z",
            }
        }
    )


class EncodeHierarchicalRequest(BaseModel):
    """Request model for /encode_h endpoint"""

    text: str = Field(..., min_length=1, max_length=10000, description="Text to encode")
    max_depth: int = Field(1, ge=0, le=5, description="Maximum tree depth to expand")
    expand_threshold: float = Field(
        0.2, ge=0.0, le=1.0, description="Threshold for lazy expansion (router confidence)"
    )
    lang: Optional[str] = Field(None, pattern="^(ru|en)$", description="Language hint")

    @field_validator("text")
    @classmethod
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError("Text cannot be empty or whitespace only")
        return v


class EncodeHierarchicalResponse(BaseModel):
    """Response model for /encode_h endpoint"""

    tree: TreeNode = Field(..., description="Hierarchical semantic tree")
    norm: bool = Field(True, description="Whether vectors are normalized")
    max_depth: int = Field(..., description="Maximum depth reached")
    trace_id: str = Field(..., description="Request trace ID")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


class PathReasoning(BaseModel):
    """Reasoning contribution from a specific path in the tree"""

    path: str = Field(..., description="Path in tree (e.g., 'dim2/dim2.4')")
    weight: float = Field(..., ge=0.0, le=1.0, description="Contribution weight")
    label: str = Field(..., description="Semantic label for this path")
    evidence: List[str] = Field(
        default_factory=list, description="Supporting evidence (words/features)"
    )


class DecodeHierarchicalRequest(BaseModel):
    """Request model for /decode_h endpoint"""

    tree: TreeNode = Field(..., description="Hierarchical tree to decode")
    top_k: int = Field(3, ge=1, le=10, description="Number of top paths to return")


class DecodeHierarchicalResponse(BaseModel):
    """Response model for /decode_h endpoint"""

    text: str = Field(..., description="Decoded text")
    reasoning: List[PathReasoning] = Field(
        default_factory=list, description="Path-wise reasoning contributions"
    )
    explainable: bool = Field(True, description="Whether reasoning is available")
    trace_id: str = Field(..., description="Request trace ID")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "Собака",
                "reasoning": [
                    {
                        "path": "dim2/dim2.4",
                        "weight": 0.73,
                        "label": "домашнее-живое-позитив",
                        "evidence": ["дом", "позитив"],
                    }
                ],
                "explainable": True,
                "trace_id": "req_abc123",
                "timestamp": "2025-01-19T12:34:56.789Z",
            }
        }
    )


class PathEdit(BaseModel):
    """Single path edit for manipulation"""

    path: str = Field(..., description="Path to edit (e.g., 'dim2/dim2.4')")
    value: List[float] = Field(
        ..., min_length=5, max_length=5, description="New 5D value for this node"
    )

    @field_validator("value")
    @classmethod
    def validate_value(cls, v):
        import math

        if any(math.isnan(x) or math.isinf(x) for x in v):
            raise ValueError("Vector values cannot contain NaN or Inf")
        if any(abs(x) > 1.0 for x in v):
            raise ValueError("Vector values must be in range [-1, 1]")
        return v


class ManipulateHierarchicalRequest(BaseModel):
    """Request model for /manipulate_h endpoint"""

    text: str = Field(..., min_length=1, max_length=10000, description="Input text")
    edits: List[PathEdit] = Field(..., min_length=1, description="List of path edits")

    @field_validator("text")
    @classmethod
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError("Text cannot be empty or whitespace only")
        return v


class ManipulateHierarchicalResponse(BaseModel):
    """Response model for /manipulate_h endpoint"""

    original: Dict[str, Any] = Field(..., description="Original encoding and decoding")
    modified: Dict[str, Any] = Field(..., description="Modified encoding and decoding")
    trace_id: str = Field(..., description="Request trace ID")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


class NodeExplanation(BaseModel):
    """Explanation of a node's contribution in hierarchical tree"""

    path: str = Field(..., description="Path in tree (e.g., 'root', 'dim2/dim2.4')")
    label: str = Field(..., description="Semantic label for this node")
    value: List[float] = Field(..., min_length=5, max_length=5, description="5D vector at this node")
    weight: Optional[float] = Field(None, ge=0.0, le=1.0, description="Router weight/confidence")
    interpretation: Optional[str] = Field(None, description="Human-readable interpretation")


class ExplainHierarchicalRequest(BaseModel):
    """Request model for /explain_h endpoint"""

    text: str = Field(..., min_length=1, max_length=10000, description="Text to explain")
    max_depth: int = Field(1, ge=0, le=5, description="Maximum tree depth to expand")
    expand_threshold: float = Field(
        0.2, ge=0.0, le=1.0, description="Threshold for lazy expansion (router confidence)"
    )
    lang: Optional[str] = Field(None, pattern="^(ru|en)$", description="Language hint")

    @field_validator("text")
    @classmethod
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError("Text cannot be empty or whitespace only")
        return v


class ExplainHierarchicalResponse(BaseModel):
    """Response model for /explain_h endpoint"""

    tree: TreeNode = Field(..., description="Hierarchical semantic tree")
    nodes: List[NodeExplanation] = Field(..., description="Per-node explanations")
    trace_id: str = Field(..., description="Request trace ID")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tree": {
                    "value": [0.12, 0.88, -0.41, 0.05, 0.67],
                    "label": "coarse",
                    "key": "root",
                },
                "nodes": [
                    {
                        "path": "root",
                        "label": "coarse semantic vector",
                        "value": [0.12, 0.88, -0.41, 0.05, 0.67],
                        "weight": 1.0,
                        "interpretation": "High abstraction, positive sentiment",
                    },
                    {
                        "path": "dim2",
                        "label": "concrete/positive",
                        "value": [0.2, -0.1, 0.6, -0.4, 0.3],
                        "weight": 0.73,
                        "interpretation": "Concrete positive entity",
                    },
                ],
                "trace_id": "req_abc123",
                "timestamp": "2025-01-19T12:34:56.789Z",
            }
        }
    )
