"""
Atlas Example: Recreating the problem statement example

This demonstrates the exact example from the problem statement:
Input: [0.1, 0.9, -0.5, 0.2, 0.8]
Expected output with interpretable reasoning.
"""

from atlas import SemanticSpace
import numpy as np


def main():
    print("=" * 80)
    print("  ATLAS EXAMPLE - From Problem Statement")
    print("=" * 80)
    print()
    
    # Initialize semantic space
    space = SemanticSpace()
    
    # The vector from the problem statement
    vector = np.array([0.1, 0.9, -0.5, 0.2, 0.8])
    
    print("Input Vector: [0.1, 0.9, -0.5, 0.2, 0.8]")
    print()
    print("-" * 80)
    print("ОБЫЧНЫЙ AI:")
    print("-" * 80)
    print("\"Собака.\"")
    print()
    
    print("-" * 80)
    print("АТЛАС:")
    print("-" * 80)
    print()
    
    # Decode with reasoning
    result = space.decode(vector, with_reasoning=True)
    
    # Display reasoning in the style from problem statement
    print("Я чувствую, что:")
    
    lines = result['reasoning'].split('\n')
    for line in lines:
        if 'dim₍' in line:
            # Format to match problem statement style
            parts = line.split(' → ')
            if len(parts) == 2:
                dim_part = parts[0]
                interpretation = parts[1]
                print(f"{dim_part} → {interpretation}")
    
    print(f"\n→ итог: \"{result['text']}\"")
    print()
    
    print("=" * 80)
    print("  KEY INSIGHT")
    print("=" * 80)
    print()
    print("Atlas doesn't just output a word - it explains the STORY of how")
    print("meaning was chosen based on each dimensional value.")
    print()
    print("This transforms dry numbers into an explainable reasoning process,")
    print("making AI interpretable and transparent.")
    print()
    
    # Additional demonstration
    print("=" * 80)
    print("  DIMENSIONAL ANALYSIS")
    print("=" * 80)
    print()
    
    dimensions = [
        ("dim₁ = 0.1", "Slightly towards action/movement"),
        ("dim₂ = 0.9", "Strongly positive emotional tone"),
        ("dim₃ = -0.5", "Moderately concrete (not abstract)"),
        ("dim₄ = 0.2", "Slightly world-oriented"),
        ("dim₅ = 0.8", "Strongly living/organic")
    ]
    
    print("What each dimension tells us:")
    for dim, meaning in dimensions:
        print(f"  {dim:12} → {meaning}")
    
    print()
    print("Combined interpretation: A living, concrete being with positive")
    print("associations → likely an animal, specifically \"Собака\" (Dog)")
    print()
    
    # Show how changing dimensions changes meaning
    print("=" * 80)
    print("  DIMENSION MANIPULATION DEMO")
    print("=" * 80)
    print()
    
    print("Original vector: [0.1, 0.9, -0.5, 0.2, 0.8]")
    print(f"Result: \"{result['text']}\"")
    print()
    
    # Make it mechanical instead of living
    modified_vector = vector.copy()
    modified_vector[4] = -0.8  # Living → Mechanical
    modified_result = space.decode(modified_vector, with_reasoning=False)
    
    print("Modified: dim₅ changed from 0.8 (living) to -0.8 (mechanical)")
    print(f"New vector: {modified_vector}")
    print(f"New result: \"{modified_result}\"")
    print()
    
    print("By changing just one dimension, we \"rotate\" the meaning in")
    print("semantic space, like adjusting a control on a mixing board.")
    print()


if __name__ == "__main__":
    main()
