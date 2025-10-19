"""
Comprehensive Atlas Demo

This script demonstrates all the key capabilities of Atlas in one place.
"""

from atlas import SemanticSpace
import numpy as np


def section_header(title):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def main():
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  ATLAS - COMPREHENSIVE DEMONSTRATION".center(78) + "█")
    print("█" + "  Semantic Space Control Panel".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)
    
    space = SemanticSpace()
    
    # 1. Show dimensions
    section_header("1. THE 5 DIMENSIONS OF MEANING")
    print("Atlas operates in a 5-dimensional semantic space:")
    print()
    info = space.get_dimension_info()
    for i, (dim_key, dim_info) in enumerate(info.items(), 1):
        print(f"  {dim_key}: {dim_info['name']}")
        print(f"       {dim_info['poles'][0]} ↔ {dim_info['poles'][1]}")
        print(f"       {dim_info['description']}")
        print()
    
    # 2. Encoding
    section_header("2. ENCODING: Text → 5D Vector")
    examples = ["Собака", "Машина", "Любовь", "Страх"]
    print("Encoding sample texts into 5D semantic space:\n")
    for text in examples:
        vector = space.encode(text)
        print(f"  \"{text:10}\" → {vector}")
    
    # 3. Decoding with reasoning
    section_header("3. DECODING: Vector → Text (with Reasoning)")
    test_vector = np.array([0.1, 0.9, -0.5, 0.2, 0.8])
    print(f"Input vector: {test_vector}\n")
    result = space.decode(test_vector, with_reasoning=True)
    print("Reasoning process:")
    print("-" * 80)
    print(result['reasoning'])
    print("-" * 80)
    print(f"\nDecoded text: \"{result['text']}\"")
    
    # 4. Dimension manipulation
    section_header("4. DIMENSION MANIPULATION: Rotating Meaning")
    print("Start with: \"Радость\" (Joy)")
    print("Manipulate: Emotion dimension (dim₂) from positive to negative\n")
    
    result = space.manipulate_dimension("Радость", dimension=1, new_value=-0.9)
    
    print(f"Original text:  \"{result['original']['decoded']['text']}\"")
    print(f"Original dim₂:  {result['original']['vector'][1]:.2f}")
    print()
    print(f"Modified dim₂:  {result['modified']['vector'][1]:.2f}")
    print(f"Modified text:  \"{result['modified']['decoded']['text']}\"")
    print()
    print("→ By rotating one dimension, meaning transforms!")
    
    # 5. Interpolation
    section_header("5. INTERPOLATION: Semantic Journey")
    print("Watch meaning gradually transform from \"Любовь\" to \"Страх\":\n")
    
    results = space.interpolate("Любовь", "Страх", steps=5)
    for r in results:
        bar = "█" * int((1 - r['alpha']) * 30) + "░" * int(r['alpha'] * 30)
        print(f"  α={r['alpha']:.2f} [{bar}] \"{r['decoded']['text']}\"")
    
    # 6. Exploration
    section_header("6. DIMENSION EXPLORATION: Axis Scanning")
    print("Exploring how Living↔Mechanical dimension (dim₅) affects \"Жизнь\":\n")
    
    results = space.explore_dimension("Жизнь", dimension=4, range_vals=[-1, -0.5, 0, 0.5, 1])
    
    for r in results:
        val = r['value']
        text = r['decoded']['text']
        bar_pos = int((val + 1) * 20)
        bar = " " * bar_pos + "▼" + " " * (40 - bar_pos)
        print(f"  {val:+.1f} │{bar}│ → \"{text}\"")
    
    print("\n  " + "─" * 43)
    print("       Mechanical        ←→        Living")
    
    # 7. Complete transformation
    section_header("7. COMPLETE TRANSFORMATION CYCLE")
    print("Full cycle: Text → Vector → Text (with interpretation)\n")
    
    original = "Собака"
    result = space.transform(original, show_reasoning=True)
    
    print(f"Original text: \"{result['original_text']}\"")
    print(f"Encoded to:    {result['vector']}")
    print()
    print("Decoding reasoning:")
    for line in result['decoded']['reasoning'].split('\n')[:3]:
        print(f"  {line}")
    print(f"  ...")
    print()
    print(f"Reconstructed: \"{result['decoded']['text']}\"")
    
    # 8. Practical applications
    section_header("8. PRACTICAL APPLICATIONS")
    print("Atlas enables:")
    print()
    print("  ✓ Interpretable AI")
    print("    → See exactly which dimension contributes to which meaning")
    print()
    print("  ✓ Semantic exploration")
    print("    → Navigate the space of possible meanings")
    print()
    print("  ✓ Controlled generation")
    print("    → Adjust dimensions to guide meaning in specific directions")
    print()
    print("  ✓ Concept analysis")
    print("    → Compare how different concepts are positioned in space")
    print()
    print("  ✓ Educational tool")
    print("    → Understand how language models represent meaning")
    
    # Final message
    section_header("CONCLUSION")
    print("Atlas is not just a model - it's a mirror where meaning sees")
    print("how it moves through space.")
    print()
    print("Through Atlas, you can:")
    print("  • Explore embeddings in reduced spaces")
    print("  • Observe how axes correlate with concepts")
    print("  • 'Control' thought like parameters in an audio editor")
    print()
    print("This is the cognitive interface where abstract meaning meets")
    print("concrete form - where AI becomes interpretable and transparent.")
    
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  Thank you for exploring Atlas!".center(78) + "█")
    print("█" + "  GitHub: github.com/danilivashyna/Atlas".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80 + "\n")


if __name__ == "__main__":
    main()
