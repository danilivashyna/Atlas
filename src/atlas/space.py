# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Semantic Space - The 5D space where meaning moves

This is the core interface for working with the semantic space.
It combines encoder, decoder, and visualization capabilities.
"""

import numpy as np
from typing import Union, List, Dict
import matplotlib.pyplot as plt

from .encoder import SimpleSemanticEncoder
from .decoder import SimpleInterpretableDecoder
from .dimensions import DimensionMapper, SemanticDimension


class SemanticSpace:
    """
    The complete Atlas interface - where meaning meets form.

    This is not just a model, but a mirror where meaning sees how it moves.
    It's a visual brain reflecting the structure of thought.
    """

    def __init__(self):
        """Initialize the semantic space with encoder and decoder"""
        self.encoder = SimpleSemanticEncoder()
        self.decoder = SimpleInterpretableDecoder()
        self.mapper = DimensionMapper()
        self.dimension = 5

    def encode(self, text: Union[str, List[str]]) -> np.ndarray:
        """
        Encode text into 5D semantic space.

        Args:
            text: Input text or list of texts

        Returns:
            5D semantic vector(s)
        """
        return self.encoder.encode_text(text)

    def decode(self, vector: np.ndarray, with_reasoning: bool = False) -> Union[str, Dict]:
        """
        Decode semantic vector back to text.

        Args:
            vector: 5D semantic vector
            with_reasoning: Whether to include interpretable reasoning

        Returns:
            Text or dictionary with reasoning
        """
        if with_reasoning:
            return self.decoder.decode_with_reasoning(vector)
        else:
            return self.decoder.decode(vector)

    def transform(self, text: str, show_reasoning: bool = True) -> Dict:
        """
        Complete transformation: text → vector → text with interpretation.

        This demonstrates the full cycle of semantic encoding and decoding.

        Args:
            text: Input text
            show_reasoning: Whether to show reasoning

        Returns:
            Dictionary with original text, vector, and decoded result
        """
        vector = self.encode(text)
        decoded = self.decode(vector, with_reasoning=show_reasoning)

        return {"original_text": text, "vector": vector.tolist(), "decoded": decoded}

    def manipulate_dimension(self, text: str, dimension: int, new_value: float) -> Dict:
        """
        Manipulate a specific dimension and see how meaning changes.

        This allows "rotating" meaning like a spectrum of light.

        Args:
            text: Input text
            dimension: Dimension to manipulate (0-4)
            new_value: New value for that dimension (-1 to 1)

        Returns:
            Original and manipulated results
        """
        # Encode original
        original_vector = self.encode(text)
        original_decoded = self.decode(original_vector, with_reasoning=True)

        # Manipulate
        modified_vector = original_vector.copy()
        modified_vector[dimension] = np.clip(new_value, -1, 1)
        modified_decoded = self.decode(modified_vector, with_reasoning=True)

        dim_info = self.mapper.get_dimension_info(SemanticDimension(dimension))

        return {
            "original": {
                "text": text,
                "vector": original_vector.tolist(),
                "decoded": original_decoded,
            },
            "modified": {
                "dimension_changed": f"{dim_info.name} ({dim_info.poles[0]} ↔ {dim_info.poles[1]})",
                "new_value": new_value,
                "vector": modified_vector.tolist(),
                "decoded": modified_decoded,
            },
        }

    def interpolate(self, text1: str, text2: str, steps: int = 5) -> List[Dict]:
        """
        Interpolate between two texts in semantic space.

        Shows how meaning gradually transforms from one concept to another.

        Args:
            text1: First text
            text2: Second text
            steps: Number of interpolation steps

        Returns:
            List of interpolated results
        """
        vec1 = self.encode(text1)
        vec2 = self.encode(text2)

        results = []
        for i in range(steps):
            alpha = i / (steps - 1)
            interpolated = vec1 * (1 - alpha) + vec2 * alpha
            decoded = self.decode(interpolated, with_reasoning=True)

            results.append(
                {"step": i, "alpha": alpha, "vector": interpolated.tolist(), "decoded": decoded}
            )

        return results

    def explore_dimension(
        self, base_text: str, dimension: int, range_vals: List[float]
    ) -> List[Dict]:
        """
        Explore how varying one dimension affects meaning.

        Args:
            base_text: Starting text
            dimension: Dimension to vary (0-4)
            range_vals: List of values to try for that dimension

        Returns:
            List of results for each value
        """
        base_vector = self.encode(base_text)
        dim_info = self.mapper.get_dimension_info(SemanticDimension(dimension))

        results = []
        for val in range_vals:
            modified = base_vector.copy()
            modified[dimension] = np.clip(val, -1, 1)
            decoded = self.decode(modified, with_reasoning=True)

            results.append(
                {
                    "dimension": f"{dim_info.name} ({dim_info.poles[0]} ↔ {dim_info.poles[1]})",
                    "value": val,
                    "vector": modified.tolist(),
                    "decoded": decoded,
                }
            )

        return results

    def visualize_vector(self, vector: np.ndarray, title: str = "Semantic Vector") -> plt.Figure:
        """
        Visualize a 5D vector as a radar/spider chart.

        Args:
            vector: 5D semantic vector
            title: Chart title

        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection="polar"))

        # Prepare data
        labels = []
        for i, dim in enumerate(SemanticDimension):
            info = self.mapper.get_dimension_info(dim)
            labels.append(f"{info.name}\n({info.poles[0]}↔{info.poles[1]})")

        # Close the plot
        angles = np.linspace(0, 2 * np.pi, len(vector), endpoint=False).tolist()
        values = vector.tolist()

        angles += angles[:1]
        values += values[:1]

        # Plot
        ax.plot(angles, values, "o-", linewidth=2, label=title)
        ax.fill(angles, values, alpha=0.25)
        ax.set_ylim(-1, 1)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels)
        ax.set_title(title, size=14, pad=20)
        ax.grid(True)

        return fig

    def visualize_space_2d(self, texts: List[str], dimensions: tuple = (0, 1)) -> plt.Figure:
        """
        Visualize multiple texts in 2D projection of semantic space.

        Args:
            texts: List of texts to visualize
            dimensions: Which two dimensions to plot (default: 0, 1)

        Returns:
            Matplotlib figure
        """
        vectors = np.array([self.encode(text) for text in texts])

        fig, ax = plt.subplots(figsize=(10, 8))

        dim1, dim2 = dimensions
        x = vectors[:, dim1]
        y = vectors[:, dim2]

        ax.scatter(x, y, s=100, alpha=0.6)

        # Label points
        for i, text in enumerate(texts):
            ax.annotate(text, (x[i], y[i]), xytext=(5, 5), textcoords="offset points", fontsize=9)

        # Get dimension info
        info1 = self.mapper.get_dimension_info(SemanticDimension(dim1))
        info2 = self.mapper.get_dimension_info(SemanticDimension(dim2))

        ax.set_xlabel(
            f"Dimension {dim1+1}: {info1.name} ({info1.poles[0]} ↔ {info1.poles[1]})", fontsize=11
        )
        ax.set_ylabel(
            f"Dimension {dim2+1}: {info2.name} ({info2.poles[0]} ↔ {info2.poles[1]})", fontsize=11
        )
        ax.set_title("Semantic Space Projection", fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color="k", linewidth=0.5)
        ax.axvline(x=0, color="k", linewidth=0.5)

        return fig

    def get_dimension_info(self) -> Dict:
        """
        Get information about all dimensions.

        Returns:
            Dictionary describing each dimension
        """
        info = {}
        for i, dim in enumerate(SemanticDimension):
            dim_info = self.mapper.get_dimension_info(dim)
            info[f"dim{i+1}"] = {
                "name": dim_info.name,
                "poles": dim_info.poles,
                "description": dim_info.description,
            }
        return info
