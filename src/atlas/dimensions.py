"""
Semantic Dimensions - The 5 axes of meaning

Each dimension is a regulator of semantic state, like knobs on a thinking mixer.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Tuple


class SemanticDimension(Enum):
    """The five dimensions of semantic space"""
    DIM1 = 0  # Object ↔ Action (Structure of phrase)
    DIM2 = 1  # Positive ↔ Negative (Emotional tone)
    DIM3 = 2  # Abstract ↔ Concrete (Level of generalization)
    DIM4 = 3  # I ↔ World (Point of observation)
    DIM5 = 4  # Living ↔ Mechanical (Essential nature)


@dataclass
class DimensionInfo:
    """Information about a semantic dimension"""
    name: str
    poles: Tuple[str, str]
    description: str
    
    
class DimensionMapper:
    """
    Maps and interprets the 5-dimensional semantic space.
    
    These dimensions are not fixed but emerge from training.
    The model itself distributes meaning across the axes.
    """
    
    DIMENSIONS = {
        SemanticDimension.DIM1: DimensionInfo(
            name="Structure",
            poles=("Object", "Action"),
            description="Defines the grammatical structure of the phrase"
        ),
        SemanticDimension.DIM2: DimensionInfo(
            name="Emotion",
            poles=("Positive", "Negative"),
            description="Emotional tone and sentiment"
        ),
        SemanticDimension.DIM3: DimensionInfo(
            name="Abstraction",
            poles=("Abstract", "Concrete"),
            description="Level of generalization vs. specificity"
        ),
        SemanticDimension.DIM4: DimensionInfo(
            name="Perspective",
            poles=("I", "World"),
            description="Point of observation: self vs. external"
        ),
        SemanticDimension.DIM5: DimensionInfo(
            name="Nature",
            poles=("Living", "Mechanical"),
            description="Essential nature: organic vs. artificial"
        ),
    }
    
    @classmethod
    def get_dimension_info(cls, dim: SemanticDimension) -> DimensionInfo:
        """Get information about a specific dimension"""
        return cls.DIMENSIONS[dim]
    
    @classmethod
    def interpret_value(cls, dim: SemanticDimension, value: float) -> str:
        """
        Interpret a dimension value (-1 to 1) as a semantic description.
        
        Args:
            dim: The semantic dimension
            value: The value along that dimension (-1 to 1)
            
        Returns:
            Human-readable interpretation
        """
        info = cls.get_dimension_info(dim)
        
        if abs(value) < 0.2:
            return f"neutral {info.name.lower()}"
        
        pole = info.poles[0] if value < 0 else info.poles[1]
        intensity = abs(value)
        
        if intensity > 0.7:
            strength = "strongly"
        elif intensity > 0.4:
            strength = "moderately"
        else:
            strength = "slightly"
            
        return f"{strength} {pole.lower()}"
    
    @classmethod
    def explain_vector(cls, vector: list) -> str:
        """
        Provide a complete interpretation of a 5D vector.
        
        Args:
            vector: 5-dimensional vector
            
        Returns:
            Human-readable explanation
        """
        explanations = []
        
        for i, (dim, value) in enumerate(zip(SemanticDimension, vector)):
            info = cls.get_dimension_info(dim)
            interpretation = cls.interpret_value(dim, value)
            explanations.append(
                f"dim₍{i+1}₎ = {value:.2f} → {interpretation} ({info.description})"
            )
        
        return "\n".join(explanations)
