#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Benchmark script for hierarchical semantic space.

Measures performance across different configurations.
"""

import argparse
import sys
from atlas.hierarchical import HierarchicalBenchmark, print_benchmark_results


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark hierarchical semantic space performance"
    )
    parser.add_argument(
        '--operation',
        choices=['encode', 'decode', 'roundtrip'],
        default='roundtrip',
        help='Operation to benchmark (default: roundtrip)'
    )
    parser.add_argument(
        '--depth',
        type=int,
        default=1,
        choices=[0, 1, 2, 3],
        help='Maximum tree depth (default: 1)'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.2,
        help='Expansion threshold (default: 0.2)'
    )
    parser.add_argument(
        '--samples',
        type=int,
        default=100,
        help='Number of samples to benchmark (default: 100)'
    )
    parser.add_argument(
        '--top-k',
        type=int,
        default=3,
        help='Top-K paths for decode (default: 3)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed statistics'
    )
    
    args = parser.parse_args()
    
    # Sample texts
    base_texts = [
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
    
    # Replicate to reach desired sample count
    texts = (base_texts * ((args.samples // len(base_texts)) + 1))[:args.samples]
    
    print(f"\n🔬 Benchmarking Atlas Hierarchical Space")
    print(f"   Operation: {args.operation}")
    print(f"   Samples: {args.samples}")
    print(f"   Configuration: depth={args.depth}, threshold={args.threshold}")
    
    # Initialize benchmark
    benchmark = HierarchicalBenchmark()
    
    # Run benchmark
    if args.operation == 'encode':
        results = benchmark.benchmark_encode(
            texts,
            max_depth=args.depth,
            expand_threshold=args.threshold
        )
    elif args.operation == 'decode':
        # First encode to get trees
        print("\n   (Pre-encoding samples for decode benchmark...)")
        trees = [
            benchmark.encoder.encode_hierarchical(text, args.depth, args.threshold)
            for text in texts
        ]
        results = benchmark.benchmark_decode(
            trees,
            top_k=args.top_k,
            with_reasoning=True
        )
    else:  # roundtrip
        results = benchmark.benchmark_roundtrip(
            texts,
            max_depth=args.depth,
            expand_threshold=args.threshold,
            top_k=args.top_k
        )
    
    # Print results
    print_benchmark_results(results, verbose=args.verbose)
    
    # Summary
    print(f"\n{'=' * 70}")
    print(f"  Summary")
    print(f"{'=' * 70}")
    print(f"  ✓ Throughput: {1000.0 / results['latency']['mean_ms']:.1f} ops/sec")
    print(f"  ✓ P95 Latency: {results['latency']['p95_ms']:.2f} ms")
    if 'tree_stats' in results:
        print(f"  ✓ Avg Tree Size: {results['tree_stats']['num_nodes']['mean']:.1f} nodes")
    print()


if __name__ == '__main__':
    main()
