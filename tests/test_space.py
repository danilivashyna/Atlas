"""
Tests for semantic space
"""

import pytest
import numpy as np

from atlas.space import SemanticSpace


class TestSemanticSpace:
    """Test the complete semantic space"""
    
    @pytest.fixture
    def space(self):
        """Create semantic space instance"""
        return SemanticSpace()
    
    def test_space_initialization(self, space):
        """Test space initializes correctly"""
        assert space.dimension == 5
        assert space.encoder is not None
        assert space.decoder is not None
        assert space.mapper is not None
    
    def test_encode(self, space):
        """Test encoding through space"""
        vector = space.encode("Собака")
        assert isinstance(vector, np.ndarray)
        assert vector.shape == (5,)
    
    def test_decode(self, space):
        """Test decoding through space"""
        vector = np.array([0.1, 0.9, -0.5, 0.2, 0.8])
        text = space.decode(vector)
        assert isinstance(text, str)
    
    def test_decode_with_reasoning(self, space):
        """Test decoding with reasoning through space"""
        vector = np.array([0.1, 0.9, -0.5, 0.2, 0.8])
        result = space.decode(vector, with_reasoning=True)
        assert isinstance(result, dict)
        assert 'text' in result
        assert 'reasoning' in result
    
    def test_transform(self, space):
        """Test complete transformation"""
        result = space.transform("Собака", show_reasoning=True)
        
        assert isinstance(result, dict)
        assert 'original_text' in result
        assert 'vector' in result
        assert 'decoded' in result
        assert result['original_text'] == "Собака"
    
    def test_manipulate_dimension(self, space):
        """Test dimension manipulation"""
        result = space.manipulate_dimension("Собака", dimension=1, new_value=-0.8)
        
        assert isinstance(result, dict)
        assert 'original' in result
        assert 'modified' in result
        
        # Check that dimension was actually changed
        original_vec = result['original']['vector']
        modified_vec = result['modified']['vector']
        assert original_vec[1] != modified_vec[1]
        assert modified_vec[1] == -0.8
    
    def test_interpolate(self, space):
        """Test interpolation between texts"""
        results = space.interpolate("Любовь", "Страх", steps=5)
        
        assert len(results) == 5
        assert results[0]['alpha'] == 0.0
        assert results[-1]['alpha'] == 1.0
        
        # Each result should have required fields
        for result in results:
            assert 'step' in result
            assert 'alpha' in result
            assert 'vector' in result
            assert 'decoded' in result
    
    def test_explore_dimension(self, space):
        """Test dimension exploration"""
        results = space.explore_dimension("Жизнь", dimension=2, range_vals=[-1, 0, 1])
        
        assert len(results) == 3
        
        for result in results:
            assert 'dimension' in result
            assert 'value' in result
            assert 'vector' in result
            assert 'decoded' in result
    
    def test_get_dimension_info(self, space):
        """Test getting dimension information"""
        info = space.get_dimension_info()
        
        assert isinstance(info, dict)
        assert len(info) == 5
        
        for dim_key in ['dim1', 'dim2', 'dim3', 'dim4', 'dim5']:
            assert dim_key in info
            assert 'name' in info[dim_key]
            assert 'poles' in info[dim_key]
            assert 'description' in info[dim_key]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
