"""
Example: Basic usage of Atlas semantic space

This demonstrates the core functionality of encoding, decoding,
and manipulating meaning in 5D space.
"""

from atlas.space import SemanticSpace
import numpy as np


def main():
    print("=" * 70)
    print("  ATLAS - Semantic Space Control Panel")
    print("  Basic Usage Example")
    print("=" * 70)
    print()
    
    # Initialize the semantic space
    space = SemanticSpace()
    
    # Example 1: Encode text to vector
    print("1. ENCODING TEXT TO 5D VECTOR")
    print("-" * 70)
    text = "Собака"
    vector = space.encode(text)
    print(f"Text: \"{text}\"")
    print(f"5D Vector: {vector}")
    print()
    
    # Example 2: Decode vector to text with reasoning
    print("2. DECODING VECTOR WITH INTERPRETABLE REASONING")
    print("-" * 70)
    test_vector = np.array([0.1, 0.9, -0.5, 0.2, 0.8])
    result = space.decode(test_vector, with_reasoning=True)
    print(f"Input Vector: {test_vector}")
    print("\nReasoning Process:")
    print(result['reasoning'])
    print()
    
    # Example 3: Transform text through the space
    print("3. COMPLETE TRANSFORMATION (Text → Vector → Text)")
    print("-" * 70)
    text = "Любовь"
    result = space.transform(text, show_reasoning=True)
    print(f"Original: \"{result['original_text']}\"")
    print(f"Vector: {result['vector']}")
    print("\nDecoded reasoning:")
    print(result['decoded']['reasoning'])
    print()
    
    # Example 4: Manipulate a dimension
    print("4. DIMENSION MANIPULATION")
    print("-" * 70)
    print("Changing emotional tone (dimension 1) from positive to negative...")
    result = space.manipulate_dimension("Радость", dimension=1, new_value=-0.9)
    print(f"\nOriginal: \"{result['original']['decoded']['text']}\"")
    print(f"Modified: \"{result['modified']['decoded']['text']}\"")
    print(f"Changed: {result['modified']['dimension_changed']}")
    print()
    
    # Example 5: Interpolate between concepts
    print("5. SEMANTIC INTERPOLATION")
    print("-" * 70)
    print("Interpolating from 'Любовь' to 'Страх'...")
    results = space.interpolate("Любовь", "Страх", steps=5)
    for r in results:
        print(f"Step {r['step']} (α={r['alpha']:.2f}): \"{r['decoded']['text']}\"")
    print()
    
    # Example 6: Explore a dimension
    print("6. DIMENSION EXPLORATION")
    print("-" * 70)
    print("Exploring how 'Living ↔ Mechanical' dimension affects 'Жизнь'...")
    results = space.explore_dimension("Жизнь", dimension=4, range_vals=[-1, -0.5, 0, 0.5, 1])
    for r in results:
        print(f"Value {r['value']:+.1f}: \"{r['decoded']['text']}\"")
    print()
    
    # Example 7: Get dimension information
    print("7. DIMENSION INFORMATION")
    print("-" * 70)
    info = space.get_dimension_info()
    for dim, details in info.items():
        print(f"{dim}: {details['name']} ({details['poles'][0]} ↔ {details['poles'][1]})")
        print(f"     {details['description']}")
    print()
    
    print("=" * 70)
    print("  End of Basic Example")
    print("=" * 70)


if __name__ == "__main__":
    main()
