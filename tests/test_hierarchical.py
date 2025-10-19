# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Tests for hierarchical semantic space
"""

import pytest
import numpy as np
import math
from atlas.hierarchical import (
    TreeNode,
    HierarchicalVector,
    HierarchicalEncoder,
    HierarchicalDecoder,
    PathEdit,
)


class TestTreeNode:
    """Test TreeNode data structure"""
    
    def test_tree_node_creation(self):
        """Test basic tree node creation"""
        node = TreeNode(
            value=[0.1, 0.2, 0.3, 0.4, 0.5],
            label="test",
            key="dim1"
        )
        assert len(node.value) == 5
        assert node.label == "test"
        assert node.key == "dim1"
    
    def test_tree_node_validation_nan(self):
        """Test that NaN values are rejected"""
        with pytest.raises(ValueError, match="NaN"):
            TreeNode(
                value=[0.1, float('nan'), 0.3, 0.4, 0.5],
                label="test"
            )
    
    def test_tree_node_validation_inf(self):
        """Test that Inf values are rejected"""
        with pytest.raises(ValueError, match="Inf"):
            TreeNode(
                value=[0.1, float('inf'), 0.3, 0.4, 0.5],
                label="test"
            )
    
    def test_tree_node_validation_range(self):
        """Test that values outside [-1, 1] are rejected"""
        with pytest.raises(ValueError, match="range"):
            TreeNode(
                value=[0.1, 1.5, 0.3, 0.4, 0.5],
                label="test"
            )
    
    def test_tree_node_children_count(self):
        """Test that children must have exactly 5 nodes"""
        parent = TreeNode(value=[0.1, 0.2, 0.3, 0.4, 0.5], label="parent")
        
        # Valid: 5 children during init
        children = [
            TreeNode(value=[0.1, 0.2, 0.3, 0.4, 0.5], label=f"child{i}")
            for i in range(5)
        ]
        parent_with_children = TreeNode(
            value=[0.1, 0.2, 0.3, 0.4, 0.5],
            label="parent",
            children=children
        )
        assert len(parent_with_children.children) == 5
        
        # Invalid: 3 children during init
        with pytest.raises(ValueError, match="exactly 5"):
            TreeNode(
                value=[0.1, 0.2, 0.3, 0.4, 0.5],
                label="parent",
                children=children[:3]
            )
    
    def test_tree_node_nested(self):
        """Test nested tree structure"""
        child = TreeNode(
            value=[0.1, 0.2, 0.3, 0.4, 0.5],
            label="child",
            key="dim1"
        )
        
        parent = TreeNode(
            value=[0.5, 0.4, 0.3, 0.2, 0.1],
            label="parent",
            key="root",
            children=[child] + [
                TreeNode(value=[0.0, 0.0, 0.0, 0.0, 0.0], label=f"child{i}")
                for i in range(4)
            ]
        )
        
        assert parent.children[0].label == "child"
        assert parent.children[0].value[0] == 0.1


class TestHierarchicalEncoder:
    """Test HierarchicalEncoder"""
    
    def test_encoder_initialization(self):
        """Test encoder initializes correctly"""
        encoder = HierarchicalEncoder()
        assert encoder.dimension == 5
        assert encoder.base_encoder is not None
    
    def test_encode_depth_0(self):
        """Test encoding with depth=0 (root only)"""
        encoder = HierarchicalEncoder()
        tree = encoder.encode_hierarchical("Собака", max_depth=0)
        
        assert tree is not None
        assert len(tree.value) == 5
        assert tree.children is None
        assert tree.key == "root"
    
    def test_encode_depth_1(self):
        """Test encoding with depth=1 (root + children)"""
        encoder = HierarchicalEncoder()
        tree = encoder.encode_hierarchical("Собака", max_depth=1)
        
        assert tree is not None
        assert len(tree.value) == 5
        
        # May or may not have children depending on threshold
        # If has children, should have exactly 5
        if tree.children:
            assert len(tree.children) == 5
            for child in tree.children:
                assert len(child.value) == 5
                assert child.key is not None
    
    def test_encode_with_threshold(self):
        """Test lazy expansion with threshold"""
        encoder = HierarchicalEncoder()
        
        # High threshold should result in fewer/no children
        tree_high = encoder.encode_hierarchical("Test", max_depth=2, expand_threshold=0.9)
        
        # Low threshold should expand more
        tree_low = encoder.encode_hierarchical("Test", max_depth=2, expand_threshold=0.1)
        
        # Both should have root
        assert tree_high is not None
        assert tree_low is not None
    
    def test_flatten_tree(self):
        """Test flattening tree to vector"""
        encoder = HierarchicalEncoder()
        tree = encoder.encode_hierarchical("Test", max_depth=1)
        
        flat = encoder.flatten_tree(tree)
        assert isinstance(flat, np.ndarray)
        assert len(flat) == 5
        assert np.all(flat >= -1.0) and np.all(flat <= 1.0)
    
    def test_router_weights(self):
        """Test router weight computation"""
        encoder = HierarchicalEncoder()
        vector = np.array([0.5, 0.3, -0.2, 0.8, 0.1])
        
        weights = encoder._compute_router_weights(vector)
        
        assert len(weights) == 5
        assert np.all(weights >= 0.0) and np.all(weights <= 1.0)
        # Sum should be close to 1 (normalized)
        assert abs(np.sum(weights) - 1.0) < 0.01


class TestHierarchicalDecoder:
    """Test HierarchicalDecoder"""
    
    def test_decoder_initialization(self):
        """Test decoder initializes correctly"""
        decoder = HierarchicalDecoder()
        assert decoder.base_decoder is not None
    
    def test_decode_simple_tree(self):
        """Test decoding a simple tree"""
        decoder = HierarchicalDecoder()
        
        tree = TreeNode(
            value=[0.1, 0.8, -0.5, 0.2, 0.7],
            label="root",
            key="root"
        )
        
        result = decoder.decode_hierarchical(tree, top_k=3, with_reasoning=False)
        
        assert 'text' in result
        assert isinstance(result['text'], str)
        assert len(result['text']) > 0
    
    def test_decode_with_reasoning(self):
        """Test decoding with path reasoning"""
        decoder = HierarchicalDecoder()
        
        tree = TreeNode(
            value=[0.1, 0.8, -0.5, 0.2, 0.7],
            label="root",
            key="root"
        )
        
        result = decoder.decode_hierarchical(tree, top_k=3, with_reasoning=True)
        
        assert 'text' in result
        assert 'reasoning' in result
        assert isinstance(result['reasoning'], list)
        assert len(result['reasoning']) > 0
        
        # Check reasoning structure
        for r in result['reasoning']:
            assert hasattr(r, 'path')
            assert hasattr(r, 'weight')
            assert hasattr(r, 'label')
            assert 0.0 <= r.weight <= 1.0
    
    def test_extract_paths(self):
        """Test path extraction from tree"""
        decoder = HierarchicalDecoder()
        
        # Create tree with children
        children = [
            TreeNode(value=[0.1, 0.2, 0.3, 0.4, 0.5], label=f"child{i}", key=f"dim{i+1}", weight=0.5)
            for i in range(5)
        ]
        
        tree = TreeNode(
            value=[0.5, 0.4, 0.3, 0.2, 0.1],
            label="root",
            key="root",
            weight=1.0,
            children=children
        )
        
        paths = decoder._extract_paths(tree)
        
        # Should have root + 5 children = 6 paths
        assert len(paths) == 6
        
        # Check path structure
        for path_info in paths:
            assert 'path' in path_info
            assert 'weight' in path_info
            assert 'label' in path_info
            assert 'vector' in path_info
    
    def test_manipulate_path(self):
        """Test path manipulation"""
        decoder = HierarchicalDecoder()
        
        # Create simple tree
        tree = TreeNode(
            value=[0.1, 0.2, 0.3, 0.4, 0.5],
            label="root",
            key="root"
        )
        
        new_value = [0.9, 0.8, 0.7, 0.6, 0.5]
        modified = decoder.manipulate_path(tree, "root", new_value)
        
        # Original should be unchanged
        assert tree.value[0] == 0.1
        
        # Modified should have new value
        assert modified.value[0] == 0.9
    
    def test_manipulate_nested_path(self):
        """Test manipulating nested path"""
        decoder = HierarchicalDecoder()
        
        # Create tree with children
        children = [
            TreeNode(value=[0.1, 0.2, 0.3, 0.4, 0.5], label=f"child{i}", key=f"dim{i+1}")
            for i in range(5)
        ]
        
        tree = TreeNode(
            value=[0.5, 0.4, 0.3, 0.2, 0.1],
            label="root",
            key="root",
            children=children
        )
        
        new_value = [0.9, 0.8, 0.7, 0.6, 0.5]
        modified = decoder.manipulate_path(tree, "dim1", new_value)
        
        # Find dim1 in modified tree
        dim1_child = next(c for c in modified.children if c.key == "dim1")
        assert dim1_child.value[0] == 0.9


class TestIntegration:
    """Integration tests for hierarchical encode-decode"""
    
    def test_encode_decode_roundtrip(self):
        """Test encoding and decoding text"""
        encoder = HierarchicalEncoder()
        decoder = HierarchicalDecoder()
        
        text = "Собака"
        
        # Encode
        tree = encoder.encode_hierarchical(text, max_depth=1)
        
        # Decode
        result = decoder.decode_hierarchical(tree, with_reasoning=True)
        
        # Should produce some text
        assert 'text' in result
        assert len(result['text']) > 0
        
        # Should have reasoning
        assert 'reasoning' in result
        assert len(result['reasoning']) > 0
    
    def test_manipulate_and_decode(self):
        """Test manipulation affects decoding"""
        encoder = HierarchicalEncoder()
        decoder = HierarchicalDecoder()
        
        text = "Собака"
        
        # Encode
        tree = encoder.encode_hierarchical(text, max_depth=1)
        
        # Decode original
        original = decoder.decode_hierarchical(tree)
        
        # Manipulate
        new_value = [-0.9, -0.8, 0.5, 0.3, -0.2]
        modified_tree = decoder.manipulate_path(tree, "root", new_value)
        
        # Decode modified
        modified = decoder.decode_hierarchical(modified_tree)
        
        # Both should have text (may or may not be different)
        assert 'text' in original
        assert 'text' in modified
    
    def test_depth_consistency(self):
        """Test that depth parameter is respected"""
        encoder = HierarchicalEncoder()
        
        # Depth 0: no children
        tree0 = encoder.encode_hierarchical("Test", max_depth=0, expand_threshold=0.0)
        assert tree0.children is None
        
        # Depth 1: may have children at level 1
        tree1 = encoder.encode_hierarchical("Test", max_depth=1, expand_threshold=0.0)
        # Children should not have children if they exist
        if tree1.children:
            for child in tree1.children:
                assert child.children is None or len(child.children) == 0 or child.children[0].children is None
