"""
Example: Visualization of semantic space

This demonstrates how to visualize vectors and text in the 5D semantic space.
"""

import matplotlib.pyplot as plt
import numpy as np

from atlas.space import SemanticSpace


def main():
    print("=" * 70)
    print("  ATLAS - Semantic Space Visualization")
    print("=" * 70)
    print()

    space = SemanticSpace()

    # Example 1: Visualize a single vector
    print("1. Visualizing a semantic vector...")
    vector = np.array([0.1, 0.9, -0.5, 0.2, 0.8])
    fig = space.visualize_vector(vector, title="Example: 'Собака'")
    plt.savefig("/tmp/vector_visualization.png", dpi=150, bbox_inches="tight")
    print("   Saved to: /tmp/vector_visualization.png")
    plt.close()

    # Example 2: Compare multiple concepts
    print("2. Comparing multiple concepts...")
    concepts = ["Собака", "Машина", "Любовь", "Страх", "Радость"]

    for i, concept in enumerate(concepts):
        vector = space.encode(concept)
        fig = space.visualize_vector(vector, title=f"Concept: {concept}")
        plt.savefig(f"/tmp/concept_{i}_{concept}.png", dpi=150, bbox_inches="tight")
        print(f"   Saved: /tmp/concept_{i}_{concept}.png")
        plt.close()

    # Example 3: Visualize texts in 2D projection
    print("3. Visualizing semantic space (2D projection)...")
    texts = [
        "Собака",
        "Кот",
        "Птица",  # Living beings
        "Машина",
        "Робот",
        "Компьютер",  # Mechanical
        "Любовь",
        "Радость",
        "Счастье",  # Positive abstract
        "Страх",
        "Боль",
        "Тоска",  # Negative abstract
    ]

    fig = space.visualize_space_2d(texts, dimensions=(1, 2))  # Emotion vs Abstraction
    plt.savefig("/tmp/space_2d_projection.png", dpi=150, bbox_inches="tight")
    print("   Saved to: /tmp/space_2d_projection.png")
    plt.close()

    # Example 4: Visualize interpolation
    print("4. Visualizing semantic interpolation...")
    results = space.interpolate("Любовь", "Ненависть", steps=7)

    fig, axes = plt.subplots(1, len(results), figsize=(20, 3), subplot_kw=dict(projection="polar"))

    for i, (ax, result) in enumerate(zip(axes, results)):
        vector = np.array(result["vector"])
        angles = np.linspace(0, 2 * np.pi, 5, endpoint=False).tolist()
        values = vector.tolist()
        angles += angles[:1]
        values += values[:1]

        ax.plot(angles, values, "o-", linewidth=2)
        ax.fill(angles, values, alpha=0.25)
        ax.set_ylim(-1, 1)
        ax.set_title(f"α={result['alpha']:.2f}\n{result['decoded']['text']}", size=10, pad=10)
        ax.grid(True)

    plt.tight_layout()
    plt.savefig("/tmp/interpolation_visualization.png", dpi=150, bbox_inches="tight")
    print("   Saved to: /tmp/interpolation_visualization.png")
    plt.close()

    print()
    print("=" * 70)
    print("  Visualization complete!")
    print("  Check /tmp/ directory for generated images")
    print("=" * 70)


if __name__ == "__main__":
    main()
