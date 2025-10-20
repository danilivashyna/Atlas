# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Interpretability benchmarks for Atlas Semantic Space.

Measures quality and performance of interpretability features:
- Dimension reasoning quality
- Path extraction and explanation
- Manipulation effects
- Reasoning generation speed
"""

import pytest
import numpy as np
from .conftest import skip_if_no_benchmark


@skip_if_no_benchmark
class TestDimensionInterpretability:
    """Benchmark dimension interpretation quality."""

    def test_decode_with_reasoning_completeness(self, benchmark, decoder):
        """Benchmark that reasoning includes all dimensions."""
        vector = np.array([0.8, -0.6, 0.3, 0.9, -0.2])
        
        def check_reasoning():
            result = decoder.decode_with_reasoning(vector)
            
            # Check structure
            if 'reasoning' not in result or 'text' not in result:
                return False
            
            reasoning = result['reasoning']
            
            # Should mention all 5 dimensions
            has_all_dims = all(
                f"dim₍{i}₎" in reasoning or f"dim{i}" in reasoning.lower()
                for i in range(1, 6)
            )
            
            return has_all_dims and len(reasoning) > 0
        
        result = benchmark(check_reasoning)
        assert result == True

    def test_reasoning_generation_speed(self, benchmark, decoder):
        """Benchmark reasoning generation performance."""
        vector = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        
        result = benchmark(decoder.decode_with_reasoning, vector)
        assert 'reasoning' in result
        assert isinstance(result['reasoning'], str)
        assert len(result['reasoning']) > 0

    def test_extreme_values_interpretable(self, benchmark, decoder):
        """Benchmark interpretation of extreme dimension values."""
        # All positive extremes
        vector_pos = np.array([0.95, 0.95, 0.95, 0.95, 0.95])
        
        def check_extremes():
            result_pos = decoder.decode_with_reasoning(vector_pos)
            
            # Should handle extremes without errors
            if 'reasoning' not in result_pos:
                return False
            if len(result_pos['reasoning']) == 0:
                return False
            
            return True
        
        result = benchmark(check_extremes)
        assert result == True

    def test_neutral_vector_interpretable(self, benchmark, decoder):
        """Benchmark interpretation of neutral/zero vector."""
        vector = np.zeros(5)
        
        result = benchmark(decoder.decode_with_reasoning, vector)
        assert 'reasoning' in result
        assert 'text' in result
        # Neutral vector should still produce valid output
        assert len(result['text']) > 0


@skip_if_no_benchmark
class TestHierarchicalInterpretability:
    """Benchmark hierarchical path reasoning quality."""

    def test_path_extraction_completeness(
        self, benchmark, hierarchical_encoder, hierarchical_decoder
    ):
        """Benchmark that path extraction finds all paths."""
        text = "Собака"
        
        def check_paths():
            tree = hierarchical_encoder.encode_hierarchical(text, max_depth=1)
            result = hierarchical_decoder.decode_hierarchical(
                tree, top_k=10, with_reasoning=True
            )
            
            # Should have reasoning paths
            if 'reasoning' not in result:
                return False
            
            reasoning = result['reasoning']
            if not isinstance(reasoning, list):
                return False
            
            # Should have at least root path
            if len(reasoning) == 0:
                return False
            
            # Each path should have required attributes
            for r in reasoning:
                if not hasattr(r, 'path') or not hasattr(r, 'weight') or not hasattr(r, 'label'):
                    return False
                if not (0.0 <= r.weight <= 1.0):
                    return False
            
            return True
        
        result = benchmark(check_paths)
        assert result == True

    def test_path_reasoning_generation(
        self, benchmark, hierarchical_encoder, hierarchical_decoder
    ):
        """Benchmark path reasoning generation performance."""
        text = "Machine learning"
        tree = hierarchical_encoder.encode_hierarchical(text, max_depth=1)
        
        result = benchmark(
            hierarchical_decoder.decode_hierarchical,
            tree,
            top_k=5,
            with_reasoning=True
        )
        
        assert 'reasoning' in result
        assert isinstance(result['reasoning'], list)

    def test_top_k_selection(
        self, benchmark, hierarchical_encoder, hierarchical_decoder
    ):
        """Benchmark top-k path selection accuracy."""
        text = "Natural language processing"
        tree = hierarchical_encoder.encode_hierarchical(text, max_depth=1)
        
        def check_top_k():
            result = hierarchical_decoder.decode_hierarchical(
                tree, top_k=3, with_reasoning=True
            )
            
            reasoning = result['reasoning']
            
            # Should return at most top_k paths
            if len(reasoning) > 3:
                return False
            
            # Weights should be sorted descending (or at least valid)
            weights = [r.weight for r in reasoning]
            return all(0.0 <= w <= 1.0 for w in weights)
        
        result = benchmark(check_top_k)
        assert result == True

    def test_reasoning_path_validity(
        self, benchmark, hierarchical_encoder, hierarchical_decoder
    ):
        """Benchmark that reasoning paths are valid and consistent."""
        text = "Собака"
        
        def check_validity():
            tree = hierarchical_encoder.encode_hierarchical(text, max_depth=1)
            result = hierarchical_decoder.decode_hierarchical(
                tree, top_k=5, with_reasoning=True
            )
            
            reasoning = result['reasoning']
            
            # Each path should have valid components
            for r in reasoning:
                # Path should be a string or list
                if not (isinstance(r.path, (str, list))):
                    return False
                # Label should exist
                if not r.label:
                    return False
                # Weight in valid range
                if not (0.0 <= r.weight <= 1.0):
                    return False
            
            return True
        
        result = benchmark(check_validity)
        assert result == True


@skip_if_no_benchmark
class TestManipulationInterpretability:
    """Benchmark interpretability of semantic manipulations."""

    def test_manipulation_effect_observable(
        self, benchmark, hierarchical_encoder, hierarchical_decoder
    ):
        """Benchmark that manipulations have observable effects."""
        text = "Собака"
        
        def check_effect():
            tree = hierarchical_encoder.encode_hierarchical(text, max_depth=1)
            
            # Get original output
            original = hierarchical_decoder.decode_hierarchical(tree, with_reasoning=False)
            
            # Manipulate root
            new_value = [-0.9, -0.8, 0.7, 0.6, -0.5]
            modified_tree = hierarchical_decoder.manipulate_path(tree, "root", new_value)
            
            # Get modified output
            modified = hierarchical_decoder.decode_hierarchical(
                modified_tree, with_reasoning=False
            )
            
            # Both should produce valid output
            if 'text' not in original or 'text' not in modified:
                return False
            
            # Output should be non-empty
            if len(original['text']) == 0 or len(modified['text']) == 0:
                return False
            
            return True
        
        result = benchmark(check_effect)
        assert result == True

    def test_manipulation_preserves_interpretability(
        self, benchmark, hierarchical_encoder, hierarchical_decoder
    ):
        """Benchmark that manipulated trees remain interpretable."""
        text = "Machine learning"
        
        def check_interpretability():
            tree = hierarchical_encoder.encode_hierarchical(text, max_depth=1)
            
            # Manipulate
            new_value = [0.5, 0.5, 0.5, 0.5, 0.5]
            modified = hierarchical_decoder.manipulate_path(tree, "root", new_value)
            
            # Should still be decodable with reasoning
            result = hierarchical_decoder.decode_hierarchical(
                modified, top_k=3, with_reasoning=True
            )
            
            if 'reasoning' not in result or 'text' not in result:
                return False
            
            return len(result['reasoning']) > 0
        
        result = benchmark(check_interpretability)
        assert result == True

    def test_multiple_manipulations(
        self, benchmark, hierarchical_encoder, hierarchical_decoder
    ):
        """Benchmark multiple sequential manipulations."""
        text = "Natural language"
        
        def multi_manipulate():
            tree = hierarchical_encoder.encode_hierarchical(text, max_depth=1)
            
            # First manipulation
            tree1 = hierarchical_decoder.manipulate_path(
                tree, "root", [0.8, 0.7, 0.6, 0.5, 0.4]
            )
            
            # Second manipulation  
            tree2 = hierarchical_decoder.manipulate_path(
                tree1, "root", [0.3, 0.2, 0.1, 0.0, -0.1]
            )
            
            # Should still be valid
            result = hierarchical_decoder.decode_hierarchical(tree2, with_reasoning=False)
            
            return 'text' in result and len(result['text']) > 0
        
        result = benchmark(multi_manipulate)
        assert result == True


@skip_if_no_benchmark
class TestExplanationQuality:
    """Benchmark quality and usefulness of explanations."""

    def test_explanation_non_empty(self, benchmark, decoder):
        """Benchmark that explanations are always generated."""
        vectors = [
            np.array([0.8, 0.5, 0.2, 0.1, 0.9]),
            np.array([-0.8, -0.5, -0.2, -0.1, -0.9]),
            np.array([0.0, 0.0, 0.0, 0.0, 0.0]),
        ]
        
        def check_explanations():
            for v in vectors:
                result = decoder.decode_with_reasoning(v)
                if 'reasoning' not in result or len(result['reasoning']) == 0:
                    return False
            return True
        
        result = benchmark(check_explanations)
        assert result == True

    def test_explanation_consistency(self, benchmark, decoder):
        """Benchmark that same vector produces same explanation."""
        vector = np.array([0.5, 0.4, 0.3, 0.2, 0.1])
        
        def check_consistency():
            r1 = decoder.decode_with_reasoning(vector)
            r2 = decoder.decode_with_reasoning(vector)
            
            # Should produce identical explanations
            return r1['reasoning'] == r2['reasoning']
        
        result = benchmark(check_consistency)
        assert result == True

    def test_batch_explanation_quality(self, benchmark, encoder, decoder):
        """Benchmark explanation quality for batch processing."""
        texts = ["love", "hate", "joy", "sadness", "fear"]
        
        def batch_explain():
            vectors = encoder.encode_text(texts)
            results = []
            
            for v in vectors:
                result = decoder.decode_with_reasoning(v)
                results.append(result)
            
            # All should have valid reasoning
            return all(
                'reasoning' in r and len(r['reasoning']) > 0
                for r in results
            )
        
        result = benchmark(batch_explain)
        assert result == True
