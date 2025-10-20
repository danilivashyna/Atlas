#!/usr/bin/env python
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Example usage of Atlas proportional summarization.

Demonstrates length-controlled summarization with semantic preservation.
"""

from atlas.summarize import summarize


def main():
    """Run summarization examples"""
    
    # Example 1: Compress mode
    print("=" * 70)
    print("Example 1: Compress Mode")
    print("=" * 70)
    
    long_text = """
    Artificial intelligence is rapidly transforming industries worldwide. 
    Machine learning algorithms can now process vast amounts of data to 
    identify patterns and make accurate predictions. Deep learning neural 
    networks have revolutionized computer vision and natural language processing. 
    AI systems are being deployed in healthcare to assist with diagnosis and 
    treatment planning. Autonomous vehicles use sophisticated AI to navigate 
    safely through complex environments. The technology continues to advance 
    at an unprecedented pace, raising both opportunities and ethical considerations 
    for society.
    """
    
    result = summarize(
        text=long_text.strip(),
        target_tokens=60,
        mode="compress",
        epsilon=0.05,
        preserve_order=True
    )
    
    print(f"\nOriginal length: ~{len(long_text.split())} words")
    print(f"Target tokens: 60")
    print(f"Actual length: {result['length']} tokens")
    print(f"\nSummary:\n{result['summary']}")
    print(f"\nTarget ratio: {[round(r, 3) for r in result['ratio_target']]}")
    print(f"Actual ratio:  {[round(r, 3) for r in result['ratio_actual']]}")
    print(f"KL divergence: {result['kl_div']:.4f}")
    
    # Example 2: Expand mode
    print("\n" + "=" * 70)
    print("Example 2: Expand Mode")
    print("=" * 70)
    
    short_text = "Machine learning enables computers to learn from data."
    
    result = summarize(
        text=short_text,
        target_tokens=50,
        mode="expand",
        epsilon=0.1,
        preserve_order=True
    )
    
    print(f"\nOriginal: {short_text}")
    print(f"Target tokens: 50")
    print(f"Actual length: {result['length']} tokens")
    print(f"\nExpanded:\n{result['summary'][:200]}...")
    print(f"\nKL divergence: {result['kl_div']:.4f}")
    
    # Example 3: Different epsilon values
    print("\n" + "=" * 70)
    print("Example 3: Different Epsilon Values")
    print("=" * 70)
    
    test_text = """
    The quick brown fox jumps over the lazy dog. This sentence contains 
    every letter of the alphabet and is often used for font testing and 
    typing practice.
    """
    
    for eps in [0.01, 0.05, 0.1, 0.5]:
        result = summarize(
            text=test_text.strip(),
            target_tokens=25,
            mode="compress",
            epsilon=eps,
            preserve_order=True
        )
        print(f"\nEpsilon={eps:.2f}: KL={result['kl_div']:.4f}, Length={result['length']}")
    
    print("\n" + "=" * 70)
    print("Examples completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
