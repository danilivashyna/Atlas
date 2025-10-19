# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Benchmarking utilities for hierarchical semantic space

Measures p50/p95 latency and cost statistics for different tree depths
and expansion configurations.
"""

import time
import statistics
from typing import List, Dict, Any, Callable
import numpy as np

from atlas.hierarchical import HierarchicalEncoder, HierarchicalDecoder, TreeNode


class HierarchicalBenchmark:
    """
    Benchmark utility for hierarchical operations.
    
    Measures:
    - p50/p95 latency
    - Average tree depth
    - Number of expanded branches
    - Memory usage (tree size)
    """
    
    def __init__(self, encoder: HierarchicalEncoder = None, decoder: HierarchicalDecoder = None):
        """
        Initialize benchmark.
        
        Args:
            encoder: HierarchicalEncoder instance (creates new if None)
            decoder: HierarchicalDecoder instance (creates new if None)
        """
        self.encoder = encoder or HierarchicalEncoder()
        self.decoder = decoder or HierarchicalDecoder()
    
    def benchmark_encode(
        self,
        texts: List[str],
        max_depth: int = 1,
        expand_threshold: float = 0.2,
        warmup_runs: int = 5
    ) -> Dict[str, Any]:
        """
        Benchmark encoding performance.
        
        Args:
            texts: List of texts to encode
            max_depth: Maximum tree depth
            expand_threshold: Expansion threshold
            warmup_runs: Number of warmup iterations
            
        Returns:
            Dictionary with benchmark results
        """
        # Warmup
        for _ in range(warmup_runs):
            _ = self.encoder.encode_hierarchical(texts[0], max_depth, expand_threshold)
        
        # Benchmark
        latencies = []
        trees = []
        
        for text in texts:
            start = time.perf_counter()
            tree = self.encoder.encode_hierarchical(text, max_depth, expand_threshold)
            end = time.perf_counter()
            
            latencies.append((end - start) * 1000)  # Convert to ms
            trees.append(tree)
        
        # Compute statistics
        latencies_sorted = sorted(latencies)
        n = len(latencies_sorted)
        
        return {
            'operation': 'encode',
            'num_samples': n,
            'max_depth': max_depth,
            'expand_threshold': expand_threshold,
            'latency': {
                'mean_ms': statistics.mean(latencies),
                'median_ms': statistics.median(latencies),
                'p50_ms': latencies_sorted[int(n * 0.50)],
                'p95_ms': latencies_sorted[int(n * 0.95)],
                'p99_ms': latencies_sorted[int(n * 0.99)] if n >= 100 else None,
                'min_ms': min(latencies),
                'max_ms': max(latencies),
                'std_ms': statistics.stdev(latencies) if n > 1 else 0.0
            },
            'tree_stats': self._analyze_trees(trees)
        }
    
    def benchmark_decode(
        self,
        trees: List[TreeNode],
        top_k: int = 3,
        with_reasoning: bool = True,
        warmup_runs: int = 5
    ) -> Dict[str, Any]:
        """
        Benchmark decoding performance.
        
        Args:
            trees: List of trees to decode
            top_k: Number of top paths
            with_reasoning: Include reasoning
            warmup_runs: Number of warmup iterations
            
        Returns:
            Dictionary with benchmark results
        """
        # Warmup
        for _ in range(warmup_runs):
            _ = self.decoder.decode_hierarchical(trees[0], top_k, with_reasoning)
        
        # Benchmark
        latencies = []
        
        for tree in trees:
            start = time.perf_counter()
            _ = self.decoder.decode_hierarchical(tree, top_k, with_reasoning)
            end = time.perf_counter()
            
            latencies.append((end - start) * 1000)  # Convert to ms
        
        # Compute statistics
        latencies_sorted = sorted(latencies)
        n = len(latencies_sorted)
        
        return {
            'operation': 'decode',
            'num_samples': n,
            'top_k': top_k,
            'with_reasoning': with_reasoning,
            'latency': {
                'mean_ms': statistics.mean(latencies),
                'median_ms': statistics.median(latencies),
                'p50_ms': latencies_sorted[int(n * 0.50)],
                'p95_ms': latencies_sorted[int(n * 0.95)],
                'p99_ms': latencies_sorted[int(n * 0.99)] if n >= 100 else None,
                'min_ms': min(latencies),
                'max_ms': max(latencies),
                'std_ms': statistics.stdev(latencies) if n > 1 else 0.0
            }
        }
    
    def benchmark_roundtrip(
        self,
        texts: List[str],
        max_depth: int = 1,
        expand_threshold: float = 0.2,
        top_k: int = 3,
        warmup_runs: int = 5
    ) -> Dict[str, Any]:
        """
        Benchmark full encode-decode roundtrip.
        
        Args:
            texts: List of texts
            max_depth: Maximum tree depth
            expand_threshold: Expansion threshold
            top_k: Number of top paths for decoding
            warmup_runs: Number of warmup iterations
            
        Returns:
            Dictionary with benchmark results
        """
        # Warmup
        for _ in range(warmup_runs):
            tree = self.encoder.encode_hierarchical(texts[0], max_depth, expand_threshold)
            _ = self.decoder.decode_hierarchical(tree, top_k, True)
        
        # Benchmark
        latencies = []
        encode_times = []
        decode_times = []
        trees = []
        
        for text in texts:
            # Encode
            start = time.perf_counter()
            tree = self.encoder.encode_hierarchical(text, max_depth, expand_threshold)
            encode_end = time.perf_counter()
            
            # Decode
            _ = self.decoder.decode_hierarchical(tree, top_k, True)
            end = time.perf_counter()
            
            encode_time = (encode_end - start) * 1000
            decode_time = (end - encode_end) * 1000
            total_time = (end - start) * 1000
            
            encode_times.append(encode_time)
            decode_times.append(decode_time)
            latencies.append(total_time)
            trees.append(tree)
        
        # Compute statistics
        latencies_sorted = sorted(latencies)
        n = len(latencies_sorted)
        
        return {
            'operation': 'roundtrip',
            'num_samples': n,
            'max_depth': max_depth,
            'expand_threshold': expand_threshold,
            'top_k': top_k,
            'latency': {
                'total_mean_ms': statistics.mean(latencies),
                'total_median_ms': statistics.median(latencies),
                'total_p50_ms': latencies_sorted[int(n * 0.50)],
                'total_p95_ms': latencies_sorted[int(n * 0.95)],
                'total_p99_ms': latencies_sorted[int(n * 0.99)] if n >= 100 else None,
                'encode_mean_ms': statistics.mean(encode_times),
                'decode_mean_ms': statistics.mean(decode_times),
                'min_ms': min(latencies),
                'max_ms': max(latencies),
                'std_ms': statistics.stdev(latencies) if n > 1 else 0.0
            },
            'tree_stats': self._analyze_trees(trees)
        }
    
    def _analyze_trees(self, trees: List[TreeNode]) -> Dict[str, Any]:
        """
        Analyze tree statistics.
        
        Args:
            trees: List of trees
            
        Returns:
            Dictionary with tree statistics
        """
        depths = []
        num_nodes = []
        num_branches = []
        
        for tree in trees:
            depths.append(self._get_tree_depth(tree))
            nodes, branches = self._count_nodes_and_branches(tree)
            num_nodes.append(nodes)
            num_branches.append(branches)
        
        return {
            'depth': {
                'mean': statistics.mean(depths),
                'median': statistics.median(depths),
                'min': min(depths),
                'max': max(depths)
            },
            'num_nodes': {
                'mean': statistics.mean(num_nodes),
                'median': statistics.median(num_nodes),
                'min': min(num_nodes),
                'max': max(num_nodes)
            },
            'num_branches': {
                'mean': statistics.mean(num_branches),
                'median': statistics.median(num_branches),
                'min': min(num_branches),
                'max': max(num_branches)
            }
        }
    
    def _get_tree_depth(self, node: TreeNode, current_depth: int = 0) -> int:
        """Get maximum depth of tree"""
        if not node.children:
            return current_depth
        
        max_child_depth = current_depth
        for child in node.children:
            child_depth = self._get_tree_depth(child, current_depth + 1)
            max_child_depth = max(max_child_depth, child_depth)
        
        return max_child_depth
    
    def _count_nodes_and_branches(self, node: TreeNode) -> tuple:
        """Count total nodes and branches in tree"""
        nodes = 1
        branches = 1 if node.children else 0
        
        if node.children:
            for child in node.children:
                child_nodes, child_branches = self._count_nodes_and_branches(child)
                nodes += child_nodes
                branches += child_branches
        
        return nodes, branches


def print_benchmark_results(results: Dict[str, Any], verbose: bool = True):
    """
    Pretty-print benchmark results.
    
    Args:
        results: Benchmark results dictionary
        verbose: Include detailed statistics
    """
    print(f"\n{'=' * 70}")
    print(f"  Benchmark: {results['operation'].upper()}")
    print(f"{'=' * 70}")
    
    print(f"\nConfiguration:")
    print(f"  Samples: {results['num_samples']}")
    if 'max_depth' in results:
        print(f"  Max Depth: {results['max_depth']}")
    if 'expand_threshold' in results:
        print(f"  Expand Threshold: {results['expand_threshold']}")
    if 'top_k' in results:
        print(f"  Top-K Paths: {results['top_k']}")
    
    latency = results['latency']
    print(f"\nLatency Statistics:")
    print(f"  Mean:   {latency['mean_ms']:.2f} ms")
    print(f"  Median: {latency['median_ms']:.2f} ms")
    print(f"  P50:    {latency['p50_ms']:.2f} ms")
    print(f"  P95:    {latency['p95_ms']:.2f} ms")
    if latency.get('p99_ms'):
        print(f"  P99:    {latency['p99_ms']:.2f} ms")
    
    if verbose:
        print(f"  Min:    {latency['min_ms']:.2f} ms")
        print(f"  Max:    {latency['max_ms']:.2f} ms")
        print(f"  StdDev: {latency['std_ms']:.2f} ms")
    
    if 'encode_mean_ms' in latency:
        print(f"\nRountrip Breakdown:")
        print(f"  Encode: {latency['encode_mean_ms']:.2f} ms")
        print(f"  Decode: {latency['decode_mean_ms']:.2f} ms")
    
    if 'tree_stats' in results:
        tree_stats = results['tree_stats']
        print(f"\nTree Statistics:")
        print(f"  Depth:      {tree_stats['depth']['mean']:.1f} (avg)")
        print(f"  Nodes:      {tree_stats['num_nodes']['mean']:.1f} (avg)")
        print(f"  Branches:   {tree_stats['num_branches']['mean']:.1f} (avg)")
        
        if verbose:
            print(f"  Depth Range:    [{tree_stats['depth']['min']}, {tree_stats['depth']['max']}]")
            print(f"  Nodes Range:    [{tree_stats['num_nodes']['min']}, {tree_stats['num_nodes']['max']}]")
            print(f"  Branches Range: [{tree_stats['num_branches']['min']}, {tree_stats['num_branches']['max']}]")


if __name__ == '__main__':
    # Example usage
    benchmark = HierarchicalBenchmark()
    
    # Sample texts
    texts = [
        "Собака",
        "Любовь",
        "Машина",
        "Радость",
        "Страх"
    ] * 20  # 100 samples
    
    # Benchmark encode at different depths
    for depth in [0, 1, 2]:
        results = benchmark.benchmark_encode(texts, max_depth=depth, expand_threshold=0.2)
        print_benchmark_results(results, verbose=False)
    
    # Benchmark roundtrip
    results = benchmark.benchmark_roundtrip(texts, max_depth=1, expand_threshold=0.2)
    print_benchmark_results(results, verbose=True)
