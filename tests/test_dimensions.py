"""
Tests for semantic dimensions and interpretation
"""

import numpy as np
import pytest

from atlas.dimensions import DimensionInfo, DimensionMapper, SemanticDimension


class TestSemanticDimension:
    """Test semantic dimension enum"""

    def test_dimension_count(self):
        """Test that we have exactly 5 dimensions"""
        assert len(SemanticDimension) == 5

    def test_dimension_indices(self):
        """Test dimension indices are 0-4"""
        indices = [dim.value for dim in SemanticDimension]
        assert indices == [0, 1, 2, 3, 4]


class TestDimensionMapper:
    """Test dimension mapper functionality"""

    def test_get_dimension_info(self):
        """Test getting dimension information"""
        info = DimensionMapper.get_dimension_info(SemanticDimension.DIM1)
        assert isinstance(info, DimensionInfo)
        assert info.name == "Structure"
        assert info.poles == ("Object", "Action")

    def test_all_dimensions_have_info(self):
        """Test that all dimensions have information"""
        for dim in SemanticDimension:
            info = DimensionMapper.get_dimension_info(dim)
            assert info is not None
            assert info.name
            assert len(info.poles) == 2
            assert info.description

    def test_interpret_value_neutral(self):
        """Test interpretation of neutral values"""
        interpretation = DimensionMapper.interpret_value(SemanticDimension.DIM1, 0.0)
        assert "neutral" in interpretation.lower()

    def test_interpret_value_positive(self):
        """Test interpretation of positive values"""
        interpretation = DimensionMapper.interpret_value(SemanticDimension.DIM1, 0.8)
        assert "action" in interpretation.lower()
        assert "strong" in interpretation.lower()

    def test_interpret_value_negative(self):
        """Test interpretation of negative values"""
        interpretation = DimensionMapper.interpret_value(SemanticDimension.DIM1, -0.8)
        assert "object" in interpretation.lower()
        assert "strong" in interpretation.lower()

    def test_explain_vector(self):
        """Test explaining a complete vector"""
        vector = [0.1, 0.9, -0.5, 0.2, 0.8]
        explanation = DimensionMapper.explain_vector(vector)

        # Check that explanation mentions all dimensions
        for i in range(1, 6):
            assert f"dim₍{i}₎" in explanation

        # Check that values are mentioned
        for val in vector:
            assert f"{val:.2f}" in explanation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
