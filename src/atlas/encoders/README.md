# TextEncoder5D

TextEncoder5D is a neural text encoder that compresses text into 5-dimensional semantic space using sentence-transformers and PCA projection.

## Features

- **Neural Encoding**: Uses `sentence-transformers/all-MiniLM-L6-v2` model (384D embeddings)
- **PCA Projection**: Projects 384D embeddings to 5D space
- **Normalization**: Supports tanh ([-1, 1]) and unit norm normalization
- **Fallback Support**: Gracefully falls back to SimpleSemanticEncoder when model unavailable
- **Multilingual**: Works with Russian, English, and other languages

## Usage

### Basic Usage

```python
from atlas.encoders import TextEncoder5D

# Initialize encoder
encoder = TextEncoder5D()

# Encode single text
vector = encoder.encode("Собака бежит по полю")
print(vector)  # 5D numpy array in [-1, 1] range

# Encode multiple texts
vectors = encoder.encode(["Hello", "World", "AI"])
print(vectors.shape)  # (3, 5)
```

### Custom Configuration

```python
# Use different normalization method
encoder = TextEncoder5D(
    dimension=5,
    normalize_method="unit_norm",  # or "tanh" (default)
    device="cpu"  # or "cuda"
)

# Disable fallback (will raise error if model unavailable)
encoder = TextEncoder5D(use_fallback=False)
```

### API Integration

The encoder is integrated into the FastAPI `/encode` endpoint. You can select which encoder to use via environment variable:

```bash
# Use default SimpleSemanticEncoder
python -m atlas.api.app

# Use TextEncoder5D
export ATLAS_ENCODER_TYPE=text_encoder_5d
python -m atlas.api.app
```

Or programmatically:

```python
from atlas import SemanticSpace

# Use TextEncoder5D
space = SemanticSpace(encoder_type="text_encoder_5d")
vector = space.encode("Hello world")

# Use default simple encoder
space = SemanticSpace(encoder_type="simple")
vector = space.encode("Hello world")
```

## Implementation Details

### Architecture

1. **Input**: Text string(s)
2. **Embedding**: sentence-transformers/all-MiniLM-L6-v2 (384D)
3. **Projection**: PCA dimensionality reduction (384D → 5D)
4. **Normalization**: tanh or L2 normalization
5. **Output**: 5D numpy array

### PCA Fitting

- PCA is fitted lazily after collecting enough samples (default: 100 samples)
- Before fitting, uses random projection as fallback
- After fitting, projection matrix is cached and reused

### Fallback Mechanism

When sentence-transformers model is unavailable (e.g., no internet, missing dependencies):
- Automatically falls back to SimpleSemanticEncoder
- Logs a warning but continues to work
- All tests pass with fallback enabled

## Testing

Run tests with:

```bash
# Run TextEncoder5D tests
pytest tests/test_text_encoder_5d.py -v

# Run with offline mode (uses fallback)
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 pytest tests/test_text_encoder_5d.py -v
```

Test coverage:
- ✅ Initialization
- ✅ Single/multiple text encoding
- ✅ Empty input validation
- ✅ Consistency and determinism
- ✅ Normalization ranges
- ✅ Multilingual support
- ✅ PCA fitting (when model available)
- ✅ Fallback behavior

## Dependencies

Required:
- `sentence-transformers>=2.2.0`
- `scikit-learn>=0.24.0`
- `numpy>=1.20.0`

Optional (for fallback):
- `atlas.encoder.SimpleSemanticEncoder`

## Performance

- **Latency**: <100ms per text on CPU (with cached model)
- **Memory**: ~90MB model size
- **Batch encoding**: Supports efficient batch processing

## Limitations

- Requires internet connection for first-time model download
- Model stored in `~/.cache/huggingface/`
- PCA needs ~100 samples to fit properly
- Fallback encoder has lower accuracy than neural encoder
