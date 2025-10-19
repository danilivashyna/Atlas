"""
Semantic Encoder - Compresses text into 5-dimensional semantic space

The encoder transforms millions of texts into a 5D space where each dimension
becomes a separate "axis of meaning".
"""

from typing import List, Union
import numpy as np

try:
    import torch
    import torch.nn as nn
    from transformers import AutoTokenizer, AutoModel
    TORCH_AVAILABLE = True
    TorchTensor = torch.Tensor
except ImportError:
    TORCH_AVAILABLE = False
    TorchTensor = None  # type: ignore


class SemanticEncoder(nn.Module if TORCH_AVAILABLE else object):
    """
    Encoder that compresses text into 5-dimensional semantic space.
    
    This is not just dimensionality reduction - each axis learns to capture
    a distinct semantic property that emerges from the data itself.
    
    Note: Requires PyTorch and Transformers to be installed.
    """
    
    def __init__(self, model_name: str = "bert-base-multilingual-cased", dimension: int = 5):
        """
        Initialize the semantic encoder.
        
        Args:
            model_name: Pre-trained transformer model to use as base
            dimension: Number of semantic dimensions (default: 5)
        """
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch and Transformers are required for SemanticEncoder. "
                            "Install with: pip install torch transformers")
        
        super().__init__()
        
        self.dimension = dimension
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.base_model = AutoModel.from_pretrained(model_name)
        
        # Freeze base model to preserve semantic knowledge
        for param in self.base_model.parameters():
            param.requires_grad = False
        
        # Projection layer to compress to 5D semantic space
        hidden_size = self.base_model.config.hidden_size
        self.projection = nn.Sequential(
            nn.Linear(hidden_size, 256),
            nn.LayerNorm(256),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(256, 64),
            nn.LayerNorm(64),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(64, dimension),
            nn.Tanh()  # Normalize to [-1, 1] range
        )
    
    def encode_text(self, text: Union[str, List[str]], normalize: bool = True):
        """
        Encode text into 5D semantic space.
        
        Args:
            text: Input text or list of texts
            normalize: Whether to normalize vectors to [-1, 1]
            
        Returns:
            5D semantic vector(s)
        """
        if isinstance(text, str):
            text = [text]
        
        # Tokenize
        inputs = self.tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )
        
        # Get contextual embeddings
        with torch.no_grad():
            outputs = self.base_model(**inputs)
            # Use [CLS] token as sentence representation
            embeddings = outputs.last_hidden_state[:, 0, :]
        
        # Project to 5D space
        semantic_vectors = self.projection(embeddings)
        
        if normalize:
            # Additional normalization to ensure values are in [-1, 1]
            semantic_vectors = torch.tanh(semantic_vectors)
        
        return semantic_vectors
    
    def forward(self, text: Union[str, List[str]]):
        """Forward pass through the encoder"""
        return self.encode_text(text)
    
    def encode_to_numpy(self, text: Union[str, List[str]]) -> np.ndarray:
        """
        Encode text and return as numpy array.
        
        Args:
            text: Input text or list of texts
            
        Returns:
            5D semantic vector(s) as numpy array
        """
        vectors = self.encode_text(text)
        return vectors.detach().cpu().numpy()
    
    def save_model(self, path: str):
        """Save the projection layer weights"""
        torch.save({
            'projection_state_dict': self.projection.state_dict(),
            'dimension': self.dimension,
            'model_name': self.tokenizer.name_or_path,
        }, path)
    
    def load_model(self, path: str):
        """Load the projection layer weights"""
        checkpoint = torch.load(path)
        self.projection.load_state_dict(checkpoint['projection_state_dict'])
        return self


class SimpleSemanticEncoder:
    """
    A simplified encoder for demonstration purposes.
    
    Uses heuristics to map text to 5D semantic space without requiring
    a trained model. Useful for quick experimentation.
    """
    
    def __init__(self):
        self.dimension = 5
    
    def encode_text(self, text: Union[str, List[str]]) -> np.ndarray:
        """
        Encode text using simple heuristics.
        
        This is a demonstration implementation that uses basic NLP heuristics
        to map text to semantic dimensions.
        
        Args:
            text: Input text or list of texts
            
        Returns:
            5D semantic vector(s)
            
        Raises:
            ValueError: If text is empty or None
        """
        if isinstance(text, str):
            if not text or not text.strip():
                raise ValueError("Input text cannot be empty")
            texts = [text]
            single_input = True
        else:
            if not text:
                raise ValueError("Input text list cannot be empty")
            if any(not t or not t.strip() for t in text):
                raise ValueError("Input text list contains empty strings")
            texts = text
            single_input = False
        
        vectors = []
        for txt in texts:
            txt_lower = txt.lower()
            words = txt_lower.split()
            
            # Dim 1: Object ↔ Action (based on verbs)
            action_words = ['run', 'jump', 'move', 'go', 'do', 'make', 'create', 'walk', 'drive',
                          'бежать', 'бег', 'прыгать', 'идти', 'делать', 'создавать', 'двигаться']
            object_words = ['dog', 'cat', 'house', 'tree', 'car', 'book', 'table', 'person',
                          'собака', 'кот', 'кошка', 'дом', 'дерево', 'машина', 'книга', 'стол', 'человек']
            dim1 = sum(1 for w in words if any(a in w for a in action_words))
            dim1 -= sum(1 for w in words if any(o in w for o in object_words))
            dim1 = np.tanh(dim1 * 0.5)
            
            # Dim 2: Positive ↔ Negative (sentiment)
            positive_words = ['good', 'happy', 'love', 'great', 'wonderful', 'beautiful', 'nice',
                            'хорошо', 'счастье', 'радость', 'любовь', 'прекрасный', 'замечательный']
            negative_words = ['bad', 'sad', 'hate', 'terrible', 'awful', 'ugly', 'wrong',
                            'плохо', 'грустный', 'грусть', 'ненависть', 'ужасный', 'страх', 'боль']
            dim2 = sum(1 for w in words if any(p in w for p in positive_words))
            dim2 -= sum(1 for w in words if any(n in w for n in negative_words))
            dim2 = np.tanh(dim2 * 0.5)
            
            # Dim 3: Abstract ↔ Concrete
            abstract_words = ['idea', 'concept', 'theory', 'thought', 'meaning', 'freedom', 'justice',
                            'идея', 'концепция', 'теория', 'мысль', 'смысл', 'свобода', 'справедливость']
            concrete_words = ['dog', 'tree', 'house', 'rock', 'water', 'hand', 'door',
                            'собака', 'дерево', 'дом', 'камень', 'вода', 'рука', 'дверь']
            dim3 = sum(1 for w in words if any(c in w for c in concrete_words))
            dim3 -= sum(1 for w in words if any(a in w for a in abstract_words))
            dim3 = np.tanh(dim3 * 0.5)
            
            # Dim 4: I ↔ World
            self_words = ['i', 'me', 'my', 'mine', 'myself', 'я', 'мне', 'мой', 'моя', 'мои']
            world_words = ['world', 'everyone', 'people', 'society', 'they', 'them',
                          'мир', 'все', 'люди', 'общество', 'они', 'их']
            dim4 = sum(1 for w in words if w in world_words)
            dim4 -= sum(1 for w in words if w in self_words)
            dim4 = np.tanh(dim4 * 0.5)
            
            # Dim 5: Living ↔ Mechanical
            living_words = ['dog', 'cat', 'person', 'tree', 'animal', 'life', 'alive', 'bird',
                          'собака', 'кот', 'кошка', 'человек', 'дерево', 'животное', 'жизнь', 'живой', 'птица']
            mechanical_words = ['machine', 'robot', 'computer', 'car', 'device', 'tool', 'engine',
                              'машина', 'робот', 'компьютер', 'автомобиль', 'устройство', 'инструмент', 'двигатель']
            dim5 = sum(1 for w in words if any(l in w for l in living_words))
            dim5 -= sum(1 for w in words if any(m in w for m in mechanical_words))
            dim5 = np.tanh(dim5 * 0.5)
            
            vectors.append([dim1, dim2, dim3, dim4, dim5])
        
        result = np.array(vectors)
        return result[0] if single_input else result
