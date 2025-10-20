# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Interpretability benchmarks for Atlas Semantic Space.

Tests the quality and completeness of semantic explanations,
path reasoning, and dimension interpretations.
"""

import pytest
from tests.benchmarks import benchmark_required
from atlas.hierarchical import HierarchicalEncoder, HierarchicalDecoder
from atlas.dimensions import DimensionMapper, SemanticDimension


@pytest.fixture
def encoder():
    """Fixture providing a hierarchical encoder instance."""
    return HierarchicalEncoder()


@pytest.fixture
def decoder():
    """Fixture providing a hierarchical decoder instance."""
    return HierarchicalDecoder()


@pytest.fixture
def dimension_mapper():
    """Fixture providing a dimension mapper for interpretations."""
    return DimensionMapper()


@pytest.fixture
def test_texts():
    """Fixture providing test texts with clear semantic meaning."""
    return [
        "Собака",
        "Любовь",
        "Машина",
        "Радость",
        "Страх",
        "Дом",
        "Дерево",
        "Жизнь",
        "Свобода",
        "Мир"
    ]


@pytest.mark.benchmark
@benchmark_required
def test_reasoning_path_generation(benchmark, encoder, decoder, test_texts):
    """
    Benchmark path reasoning generation performance.
    
    Measures the time to generate detailed reasoning paths
    that explain how the decoder reached its output.
    """
    def generate_reasoning():
        text = test_texts[0]
        tree = encoder.encode_hierarchical(text, max_depth=1, expand_threshold=0.2)
        result = decoder.decode_hierarchical(tree, top_k=3, with_reasoning=True)
        
        # Verify reasoning is present
        assert "reasoning" in result
        assert result["reasoning"] is not None
        
        return {
            "text": text,
            "num_paths": len(result["reasoning"]) if result["reasoning"] else 0,
            "reasoning": result["reasoning"]
        }
    
    result = benchmark(generate_reasoning)
    assert result is not None
    assert result["num_paths"] > 0, "Should generate at least one reasoning path"


@pytest.mark.benchmark
@benchmark_required
def test_reasoning_path_completeness(benchmark, encoder, decoder, test_texts):
    """
    Benchmark reasoning path completeness.
    
    Measures how complete and informative the generated
    reasoning paths are for explaining the output.
    """
    def measure_path_completeness():
        text = test_texts[1]
        tree = encoder.encode_hierarchical(text, max_depth=2, expand_threshold=0.2)
        result = decoder.decode_hierarchical(tree, top_k=5, with_reasoning=True)
        
        paths = result.get("reasoning", [])
        
        # Measure completeness: do paths have necessary fields?
        complete_paths = []
        for path in paths:
            has_path = hasattr(path, "path") or isinstance(path, dict) and "path" in path
            has_contribution = hasattr(path, "contribution") or isinstance(path, dict) and "contribution" in path
            has_explanation = hasattr(path, "explanation") or isinstance(path, dict) and "explanation" in path
            
            is_complete = has_path and has_contribution
            complete_paths.append(is_complete)
        
        completeness_rate = sum(complete_paths) / len(complete_paths) if complete_paths else 0.0
        
        return {
            "text": text,
            "num_paths": len(paths),
            "complete_paths": sum(complete_paths),
            "completeness_rate": completeness_rate
        }
    
    result = benchmark(measure_path_completeness)
    assert result is not None
    # Note: Completeness depends on the decoder implementation


@pytest.mark.benchmark
@benchmark_required
def test_dimension_interpretation_quality(benchmark, encoder, dimension_mapper, test_texts):
    """
    Benchmark dimension interpretation quality.
    
    Measures how well individual dimensions are interpreted
    with meaningful semantic descriptions.
    """
    def interpret_dimensions():
        text = test_texts[2]
        tree = encoder.encode_hierarchical(text, max_depth=1, expand_threshold=0.2)
        
        # Map dimension indices to SemanticDimension enum
        dim_enums = [SemanticDimension.DIM1, SemanticDimension.DIM2, SemanticDimension.DIM3, 
                     SemanticDimension.DIM4, SemanticDimension.DIM5]
        
        interpretations = []
        for i, value in enumerate(tree.value):
            dim_enum = dim_enums[i]
            dim_info = dimension_mapper.get_dimension_info(dim_enum)
            interpretation = dimension_mapper.interpret_value(dim_enum, value)
            
            # Check interpretation quality
            has_name = dim_info is not None and hasattr(dim_info, "name")
            has_interpretation = interpretation is not None and len(interpretation) > 0
            is_descriptive = has_interpretation and len(interpretation) > 10
            
            interpretations.append({
                "dimension": i,
                "value": value,
                "has_name": has_name,
                "has_interpretation": has_interpretation,
                "is_descriptive": is_descriptive,
                "interpretation": interpretation
            })
        
        quality_rate = sum(1 for i in interpretations if i["is_descriptive"]) / len(interpretations)
        
        return {
            "text": text,
            "num_dimensions": len(interpretations),
            "quality_rate": quality_rate,
            "interpretations": interpretations
        }
    
    result = benchmark(interpret_dimensions)
    assert result is not None
    # Note: Quality depends on the dimension mapper implementation


@pytest.mark.benchmark
@benchmark_required
def test_vector_explanation_generation(benchmark, encoder, dimension_mapper, test_texts):
    """
    Benchmark full vector explanation generation.
    
    Measures performance of generating a complete textual
    explanation for an entire semantic vector.
    """
    def generate_explanation():
        text = test_texts[3]
        tree = encoder.encode_hierarchical(text, max_depth=1, expand_threshold=0.2)
        
        # Generate explanation using dimension mapper
        explanation = dimension_mapper.explain_vector(tree.value)
        
        # Verify explanation quality
        has_explanations = explanation and len(explanation) > 0
        total_length = sum(len(str(e)) for e in explanation.values()) if isinstance(explanation, dict) else len(str(explanation))
        
        return {
            "text": text,
            "has_explanations": has_explanations,
            "explanation_length": total_length,
            "explanation": explanation
        }
    
    result = benchmark(generate_explanation)
    assert result is not None
    assert result["has_explanations"], "Should generate explanations"


@pytest.mark.benchmark
@benchmark_required
def test_hierarchical_explanation_depth(benchmark, encoder, decoder, dimension_mapper, test_texts):
    """
    Benchmark hierarchical explanation at different depths.
    
    Measures how explanation quality scales with tree depth,
    testing multi-level semantic interpretation.
    """
    def explain_at_depths():
        text = test_texts[4]
        results = []
        
        for depth in [0, 1, 2]:
            tree = encoder.encode_hierarchical(text, max_depth=depth, expand_threshold=0.2)
            result = decoder.decode_hierarchical(tree, top_k=3, with_reasoning=True)
            
            reasoning_paths = len(result.get("reasoning", [])) if result.get("reasoning") else 0
            
            results.append({
                "depth": depth,
                "num_reasoning_paths": reasoning_paths,
                "reconstructed": result["text"]
            })
        
        return {
            "text": text,
            "depth_results": results
        }
    
    result = benchmark(explain_at_depths)
    assert result is not None
    assert len(result["depth_results"]) == 3


@pytest.mark.benchmark
@benchmark_required
def test_explanation_consistency(benchmark, encoder, decoder, test_texts):
    """
    Benchmark explanation consistency across runs.
    
    Measures whether multiple explanation generations for
    the same input produce consistent reasoning.
    """
    def generate_multiple_explanations():
        text = test_texts[5]
        explanations = []
        
        for _ in range(3):
            tree = encoder.encode_hierarchical(text, max_depth=1, expand_threshold=0.2)
            result = decoder.decode_hierarchical(tree, top_k=3, with_reasoning=True)
            
            # Serialize reasoning for comparison
            reasoning_summary = []
            if result.get("reasoning"):
                for path in result["reasoning"]:
                    if hasattr(path, "path"):
                        reasoning_summary.append(tuple(path.path))
                    elif isinstance(path, dict) and "path" in path:
                        reasoning_summary.append(tuple(path["path"]))
            
            explanations.append(tuple(reasoning_summary))
        
        # Check consistency
        consistent = len(set(explanations)) == 1
        
        return {
            "text": text,
            "consistent": consistent,
            "num_runs": 3
        }
    
    result = benchmark(generate_multiple_explanations)
    assert result is not None
    # Explanations should be deterministic
    assert result["consistent"], "Explanations should be consistent across runs"


@pytest.mark.benchmark
@benchmark_required
def test_top_k_reasoning_coverage(benchmark, encoder, decoder, test_texts):
    """
    Benchmark top-k reasoning path coverage.
    
    Measures how well top-k paths cover the semantic space
    and contribute to the final output explanation.
    """
    def measure_coverage():
        text = test_texts[6]
        tree = encoder.encode_hierarchical(text, max_depth=1, expand_threshold=0.2)
        
        results = []
        for k in [1, 3, 5]:
            result = decoder.decode_hierarchical(tree, top_k=k, with_reasoning=True)
            num_paths = len(result.get("reasoning", [])) if result.get("reasoning") else 0
            
            results.append({
                "top_k": k,
                "num_paths": num_paths,
                "text": result["text"]
            })
        
        return {
            "original_text": text,
            "coverage_results": results
        }
    
    result = benchmark(measure_coverage)
    assert result is not None
    assert len(result["coverage_results"]) == 3


@pytest.mark.benchmark
@benchmark_required
def test_explanation_informativeness(benchmark, encoder, decoder, test_texts):
    """
    Benchmark explanation informativeness.
    
    Measures the richness and detail of generated explanations,
    testing how much information they convey.
    """
    def measure_informativeness():
        results = []
        
        for text in test_texts[:5]:
            tree = encoder.encode_hierarchical(text, max_depth=1, expand_threshold=0.2)
            result = decoder.decode_hierarchical(tree, top_k=3, with_reasoning=True)
            
            # Measure informativeness
            reasoning = result.get("reasoning", [])
            total_explanation_length = 0
            
            if reasoning:
                for path in reasoning:
                    if hasattr(path, "explanation"):
                        total_explanation_length += len(str(path.explanation))
                    elif isinstance(path, dict) and "explanation" in path:
                        total_explanation_length += len(str(path["explanation"]))
            
            results.append({
                "text": text,
                "num_paths": len(reasoning),
                "explanation_length": total_explanation_length
            })
        
        avg_length = sum(r["explanation_length"] for r in results) / len(results) if results else 0
        
        return {
            "avg_explanation_length": avg_length,
            "num_texts": len(results),
            "results": results
        }
    
    result = benchmark(measure_informativeness)
    assert result is not None


@pytest.mark.benchmark
@benchmark_required
def test_dimension_manipulation_interpretability(benchmark, encoder, decoder, dimension_mapper, test_texts):
    """
    Benchmark interpretability of dimension manipulations.
    
    Tests whether manipulating specific dimensions produces
    interpretable and predictable changes in output.
    """
    def test_manipulation_interpretability():
        text = test_texts[7]
        tree = encoder.encode_hierarchical(text, max_depth=1, expand_threshold=0.2)
        
        # Original decoding
        original_result = decoder.decode_hierarchical(tree, top_k=3, with_reasoning=True)
        original_text = original_result["text"]
        
        # Manipulate first dimension
        manipulated_tree = encoder.encode_hierarchical(text, max_depth=1, expand_threshold=0.2)
        original_value = manipulated_tree.value[0]
        manipulated_tree.value[0] = min(1.0, original_value * 1.5)
        
        manipulated_result = decoder.decode_hierarchical(manipulated_tree, top_k=3, with_reasoning=True)
        manipulated_text = manipulated_result["text"]
        
        # Get dimension interpretation
        dim_info = dimension_mapper.get_dimension_info(SemanticDimension.DIM1)
        
        return {
            "original_text": original_text,
            "manipulated_text": manipulated_text,
            "dimension_manipulated": 0,
            "dimension_name": dim_info.name if dim_info else "unknown",
            "output_changed": original_text != manipulated_text
        }
    
    result = benchmark(test_manipulation_interpretability)
    assert result is not None
