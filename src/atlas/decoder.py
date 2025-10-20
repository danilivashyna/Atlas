# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Interpretable Decoder - Reconstructs text from 5D semantic vectors with reasoning

The decoder doesn't just map vector → word, it explains the story of how meaning
was chosen. It transforms dry numbers into an explainable story of meaning formation.
"""

from typing import Dict, List

import numpy as np

from .dimensions import DimensionMapper, SemanticDimension

try:
    import torch
    import torch.nn as nn
    from transformers import AutoModelForCausalLM, AutoTokenizer, GPT2LMHeadModel, GPT2Tokenizer

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class InterpretableDecoder:
    """
    Decoder that reconstructs text from 5D semantic space with explanations.

    This is not just "vector → text", but "vector → story of choice".
    It explains why it chose this particular meaning based on the dimensional values.

    Note: Requires PyTorch and Transformers for advanced features.
    """

    def __init__(self, model_name: str = "gpt2", dimension: int = 5):
        """
        Initialize the interpretable decoder.

        Args:
            model_name: Pre-trained language model for generation
            dimension: Number of semantic dimensions (default: 5)
        """
        if not TORCH_AVAILABLE:
            raise ImportError(
                "PyTorch and Transformers are required for InterpretableDecoder. "
                "Install with: pip install torch transformers. "
                "Use SimpleInterpretableDecoder for basic functionality."
            )

        self.dimension = dimension
        self.mapper = DimensionMapper()

        # For now, we use a rule-based approach for interpretation
        # In a full implementation, this would be a trained model
        self.tokenizer = None
        self.model = None

    def decode_with_reasoning(self, vector: np.ndarray, verbose: bool = True) -> Dict[str, str]:
        """
        Decode a 5D semantic vector into text with full reasoning.

        Args:
            vector: 5D semantic vector
            verbose: Whether to include detailed reasoning

        Returns:
            Dictionary with 'reasoning' and 'text' keys
        """
        if len(vector) != self.dimension:
            raise ValueError(f"Expected {self.dimension}D vector, got {len(vector)}D")

        # Generate reasoning about each dimension
        reasoning_steps = []

        for i, (dim, value) in enumerate(zip(SemanticDimension, vector)):
            info = self.mapper.get_dimension_info(dim)
            interpretation = self.mapper.interpret_value(dim, value)

            reasoning_steps.append(f"I sense that dim₍{i+1}₎ = {value:.2f} → {interpretation}.")

        # Infer likely text based on dimensional analysis
        text = self._infer_text_from_dimensions(vector)

        reasoning_steps.append(f'→ итог: "{text}"')

        return {"reasoning": "\n".join(reasoning_steps), "text": text, "vector": vector.tolist()}

    def _infer_text_from_dimensions(self, vector: np.ndarray) -> str:
        """
        Infer appropriate text based on dimensional values.

        This is a rule-based implementation for demonstration.
        A full implementation would use a trained decoder model.
        """
        dim1, dim2, dim3, dim4, dim5 = vector

        # Analyze key dimensions
        is_object = dim1 < 0
        is_action = dim1 > 0
        is_positive = dim2 > 0
        is_concrete = dim3 > 0
        is_living = dim5 > 0.3

        # Decision tree based on dimensions
        if is_living and is_concrete:
            if is_positive:
                if abs(dim4) < 0.3:  # neutral perspective
                    return "Собака"  # Dog (as in the example)
                elif dim4 < 0:  # "I" perspective
                    return "Мой друг"  # My friend
                else:  # "World" perspective
                    return "Природа"  # Nature
            else:
                return "Волк"  # Wolf

        elif is_action:
            if is_positive:
                return "Бежать"  # To run
            else:
                return "Падать"  # To fall

        elif not is_concrete:  # Abstract
            if is_positive:
                return "Любовь"  # Love
            else:
                return "Страх"  # Fear

        elif dim5 < -0.3:  # Mechanical
            if is_concrete:
                return "Машина"  # Machine
            else:
                return "Система"  # System

        else:
            # Default based on primary dimension
            if abs(dim1) > 0.5:
                return "Движение" if is_action else "Объект"
            elif abs(dim2) > 0.5:
                return "Радость" if is_positive else "Грусть"
            elif abs(dim3) > 0.5:
                return "Камень" if is_concrete else "Идея"
            elif abs(dim4) > 0.5:
                return "Мир" if dim4 > 0 else "Я"
            else:
                return "Существо" if is_living else "Вещь"

    def decode(self, vector: np.ndarray) -> str:
        """
        Simple decode without reasoning (just return the text).

        Args:
            vector: 5D semantic vector

        Returns:
            Decoded text
        """
        return self._infer_text_from_dimensions(vector)

    def batch_decode(self, vectors: np.ndarray, verbose: bool = False) -> List[Dict[str, str]]:
        """
        Decode multiple vectors.

        Args:
            vectors: Array of 5D semantic vectors
            verbose: Whether to include reasoning

        Returns:
            List of decoded results
        """
        results = []
        for vector in vectors:
            if verbose:
                results.append(self.decode_with_reasoning(vector))
            else:
                results.append({"text": self.decode(vector)})
        return results


class SimpleInterpretableDecoder:
    """
    Simplified decoder for demonstration with extended vocabulary.
    """

    def __init__(self):
        self.dimension = 5
        self.mapper = DimensionMapper()

        # Extended concept map for different dimensional combinations
        self.concept_map = {
            # Living beings
            "living_concrete_positive": ["Собака", "Кот", "Птица", "Ребёнок"],
            "living_concrete_negative": ["Волк", "Змея", "Вирус"],
            "living_abstract": ["Жизнь", "Душа", "Сознание"],
            # Actions
            "action_positive": ["Бежать", "Танцевать", "Смеяться", "Создавать"],
            "action_negative": ["Падать", "Ломать", "Плакать"],
            # Abstract concepts
            "abstract_positive": ["Любовь", "Радость", "Свобода", "Мечта"],
            "abstract_negative": ["Страх", "Боль", "Тоска"],
            # Mechanical/artificial
            "mechanical_concrete": ["Машина", "Робот", "Компьютер"],
            "mechanical_abstract": ["Система", "Алгоритм", "Механизм"],
            # Neutral objects
            "object_concrete": ["Дом", "Дерево", "Камень", "Стол"],
            "object_abstract": ["Идея", "Мысль", "Понятие"],
        }

    def decode_with_reasoning(self, vector: np.ndarray) -> Dict[str, str]:
        """Decode with full interpretable reasoning"""
        reasoning = self.mapper.explain_vector(vector)
        text = self._select_word(vector)

        return {"reasoning": reasoning, "text": text, "vector": vector.tolist()}

    def _select_word(self, vector: np.ndarray) -> str:
        """Select appropriate word based on vector dimensions"""
        dim1, dim2, dim3, dim4, dim5 = vector

        # Classify along each dimension
        is_action = dim1 > 0.3
        is_positive = dim2 > 0.2
        is_concrete = dim3 > 0.2
        is_living = dim5 > 0.3
        is_mechanical = dim5 < -0.3

        # Select concept category
        if is_living:
            if is_concrete:
                category = "living_concrete_positive" if is_positive else "living_concrete_negative"
            else:
                category = "living_abstract"
        elif is_action:
            category = "action_positive" if is_positive else "action_negative"
        elif is_mechanical:
            category = "mechanical_concrete" if is_concrete else "mechanical_abstract"
        elif is_concrete:
            category = "object_concrete"
        else:
            category = "abstract_positive" if is_positive else "abstract_negative"

        # Select word from category
        words = self.concept_map.get(category, ["Нечто"])
        # Use dim4 to select from list
        index = int((dim4 + 1) / 2 * len(words)) % len(words)
        return words[index]

    def decode(self, vector: np.ndarray) -> str:
        """Simple decode without reasoning"""
        return self._select_word(vector)
