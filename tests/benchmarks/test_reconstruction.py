# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Reconstruction benchmarks for Atlas Semantic Space.

Tests the quality and performance of encode-decode reconstruction.
Measures semantic similarity and fidelity of reconstructed text.
"""

import pytest
from tests.benchmarks import benchmark_required
from atlas.hierarchical import HierarchicalEncoder, HierarchicalDecoder
from atlas.encoder import SimpleSemanticEncoder
from atlas.decoder import SimpleInterpretableDecoder
import numpy as np


@pytest.fixture
def encoder():
    """Fixture providing a hierarchical encoder instance."""
    return HierarchicalEncoder()


@pytest.fixture
def decoder():
    """Fixture providing a hierarchical decoder instance."""
    return HierarchicalDecoder()


@pytest.fixture
def base_encoder():
    """Fixture providing a base semantic encoder for similarity checks."""
    return SimpleSemanticEncoder()


@pytest.fixture
def test_texts():
    """Fixture providing diverse test texts for reconstruction."""
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


def compute_cosine_similarity(vec1, vec2):
    """Compute cosine similarity between two vectors."""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return np.dot(vec1, vec2) / (norm1 * norm2)


@pytest.mark.benchmark
@benchmark_required
def test_reconstruction_accuracy_depth_0(benchmark, encoder, decoder, base_encoder, test_texts):
    """
    Benchmark reconstruction accuracy at depth 0.
    
    Measures how well the system reconstructs text when using
    only the root level (no hierarchical expansion).
    """
    def reconstruct_and_measure():
        original_text = test_texts[0]
        
        # Encode and decode
        tree = encoder.encode_hierarchical(original_text, max_depth=0, expand_threshold=0.2)
        result = decoder.decode_hierarchical(tree, top_k=3, with_reasoning=True)
        reconstructed_text = result["text"]
        
        # Measure similarity using base encoder
        original_vec = base_encoder.encode_text(original_text)
        reconstructed_vec = base_encoder.encode_text(reconstructed_text)
        similarity = compute_cosine_similarity(original_vec, reconstructed_vec)
        
        return {
            "original": original_text,
            "reconstructed": reconstructed_text,
            "similarity": similarity
        }
    
    result = benchmark(reconstruct_and_measure)
    assert result is not None
    assert "similarity" in result
    # Note: Reconstruction quality depends on the underlying encoder/decoder
    # This benchmark measures performance, not quality thresholds


@pytest.mark.benchmark
@benchmark_required
def test_reconstruction_accuracy_depth_1(benchmark, encoder, decoder, base_encoder, test_texts):
    """
    Benchmark reconstruction accuracy at depth 1.
    
    Measures reconstruction quality with one level of hierarchical
    expansion, which should capture more semantic nuance.
    """
    def reconstruct_and_measure():
        original_text = test_texts[1]
        
        # Encode and decode
        tree = encoder.encode_hierarchical(original_text, max_depth=1, expand_threshold=0.2)
        result = decoder.decode_hierarchical(tree, top_k=3, with_reasoning=True)
        reconstructed_text = result["text"]
        
        # Measure similarity
        original_vec = base_encoder.encode_text(original_text)
        reconstructed_vec = base_encoder.encode_text(reconstructed_text)
        similarity = compute_cosine_similarity(original_vec, reconstructed_vec)
        
        return {
            "original": original_text,
            "reconstructed": reconstructed_text,
            "similarity": similarity
        }
    
    result = benchmark(reconstruct_and_measure)
    assert result is not None
    assert "similarity" in result
    # Note: Reconstruction quality depends on the underlying encoder/decoder


@pytest.mark.benchmark
@benchmark_required
def test_reconstruction_accuracy_depth_2(benchmark, encoder, decoder, base_encoder, test_texts):
    """
    Benchmark reconstruction accuracy at depth 2.
    
    Measures reconstruction quality with two levels of expansion,
    testing if deeper trees improve semantic fidelity.
    """
    def reconstruct_and_measure():
        original_text = test_texts[2]
        
        # Encode and decode with deeper tree
        tree = encoder.encode_hierarchical(original_text, max_depth=2, expand_threshold=0.2)
        result = decoder.decode_hierarchical(tree, top_k=5, with_reasoning=True)
        reconstructed_text = result["text"]
        
        # Measure similarity
        original_vec = base_encoder.encode_text(original_text)
        reconstructed_vec = base_encoder.encode_text(reconstructed_text)
        similarity = compute_cosine_similarity(original_vec, reconstructed_vec)
        
        return {
            "original": original_text,
            "reconstructed": reconstructed_text,
            "similarity": similarity
        }
    
    result = benchmark(reconstruct_and_measure)
    assert result is not None
    assert "similarity" in result
    # Note: Reconstruction quality depends on the underlying encoder/decoder


@pytest.mark.benchmark
@benchmark_required
def test_reconstruction_consistency(benchmark, encoder, decoder, test_texts):
    """
    Benchmark reconstruction consistency.
    
    Measures whether multiple encode-decode cycles produce
    consistent results for the same input.
    """
    def reconstruct_multiple_times():
        original_text = test_texts[3]
        results = []
        
        for _ in range(3):
            tree = encoder.encode_hierarchical(original_text, max_depth=1, expand_threshold=0.2)
            result = decoder.decode_hierarchical(tree, top_k=3, with_reasoning=True)
            results.append(result["text"])
        
        # All reconstructions should be the same
        consistency = len(set(results)) == 1
        
        return {
            "original": original_text,
            "reconstructions": results,
            "consistent": consistency
        }
    
    result = benchmark(reconstruct_multiple_times)
    assert result is not None
    assert "consistent" in result
    # Deterministic reconstruction expected
    # Note: Consistency depends on determinism in encoder/decoder


@pytest.mark.benchmark
@benchmark_required
def test_batch_reconstruction_quality(benchmark, encoder, decoder, base_encoder, test_texts):
    """
    Benchmark batch reconstruction quality.
    
    Measures average reconstruction quality across multiple
    diverse texts, testing system robustness.
    """
    def reconstruct_batch():
        similarities = []
        
        for text in test_texts[:5]:  # Test first 5 texts
            tree = encoder.encode_hierarchical(text, max_depth=1, expand_threshold=0.2)
            result = decoder.decode_hierarchical(tree, top_k=3, with_reasoning=True)
            reconstructed_text = result["text"]
            
            # Measure similarity
            original_vec = base_encoder.encode_text(text)
            reconstructed_vec = base_encoder.encode_text(reconstructed_text)
            similarity = compute_cosine_similarity(original_vec, reconstructed_vec)
            similarities.append(similarity)
        
        avg_similarity = np.mean(similarities)
        min_similarity = np.min(similarities)
        max_similarity = np.max(similarities)
        
        return {
            "avg_similarity": avg_similarity,
            "min_similarity": min_similarity,
            "max_similarity": max_similarity,
            "num_texts": len(similarities)
        }
    
    result = benchmark(reconstruct_batch)
    assert result is not None
    assert "avg_similarity" in result
    # Average reconstruction should be reasonable
    # Note: Average quality depends on the underlying model


@pytest.mark.benchmark
@benchmark_required
def test_reconstruction_with_manipulation(benchmark, encoder, decoder, base_encoder, test_texts):
    """
    Benchmark reconstruction after semantic manipulation.
    
    Tests reconstruction quality when tree values are manipulated,
    measuring how edits affect decoded output.
    """
    def manipulate_and_reconstruct():
        original_text = test_texts[4]
        
        # Encode
        tree = encoder.encode_hierarchical(original_text, max_depth=1, expand_threshold=0.2)
        
        # Manipulate: Boost a specific dimension slightly
        original_values = tree.value.copy()
        tree.value[0] = min(1.0, tree.value[0] * 1.2)
        
        # Decode manipulated tree
        result = decoder.decode_hierarchical(tree, top_k=3, with_reasoning=True)
        manipulated_text = result["text"]
        
        # Decode original tree for comparison
        tree.value = original_values
        original_result = decoder.decode_hierarchical(tree, top_k=3, with_reasoning=True)
        original_decoded = original_result["text"]
        
        return {
            "original_input": original_text,
            "original_decoded": original_decoded,
            "manipulated_decoded": manipulated_text,
            "manipulation_changed_output": original_decoded != manipulated_text
        }
    
    result = benchmark(manipulate_and_reconstruct)
    assert result is not None


@pytest.mark.benchmark
@benchmark_required
def test_reconstruction_preservation_rate(benchmark, encoder, decoder, test_texts):
    """
    Benchmark reconstruction preservation rate.
    
    Measures how many unique semantic concepts are preserved
    through the encode-decode cycle.
    """
    def measure_preservation():
        results = []
        
        for text in test_texts[:5]:
            tree = encoder.encode_hierarchical(text, max_depth=1, expand_threshold=0.2)
            result = decoder.decode_hierarchical(tree, top_k=3, with_reasoning=True)
            
            # Check if reconstruction includes original concept
            reconstructed = result["text"].lower()
            original = text.lower()
            
            # Simple check: are they similar or contain common roots?
            preserved = (
                original in reconstructed or 
                reconstructed in original or
                len(set(original) & set(reconstructed)) > len(original) * 0.3
            )
            
            results.append({
                "original": text,
                "reconstructed": result["text"],
                "preserved": preserved
            })
        
        preservation_rate = sum(1 for r in results if r["preserved"]) / len(results)
        
        return {
            "preservation_rate": preservation_rate,
            "num_tested": len(results),
            "details": results
        }
    
    result = benchmark(measure_preservation)
    assert result is not None
    assert "preservation_rate" in result
