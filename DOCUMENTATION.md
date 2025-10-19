# Atlas Documentation

## Table of Contents

1. [Introduction](#introduction)
2. [Key Concepts](#key-concepts)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Python API](#python-api)
6. [Command Line Interface](#command-line-interface)
7. [Examples](#examples)
8. [Architecture](#architecture)
9. [Advanced Usage](#advanced-usage)
10. [Contributing](#contributing)

## Introduction

Atlas is a 5-dimensional semantic space control panel that serves as an interface between abstract meaning and concrete form. Unlike traditional AI systems that operate as "black boxes", Atlas provides interpretability by showing how meaning moves through a structured semantic space.

### Philosophy

> **Atlas is not a model, but a mirror where meaning sees how it moves.**

It's a visual brain that reflects the structure of thought, allowing you to:
- See which axis represents which meaning
- Understand not just "what" the model understood, but "why"
- Consciously adjust thinking by "rotating" meaning like a spectrum of light

## Key Concepts

### The 5 Dimensions

Each dimension is a regulator of semantic state, like knobs on a thinking mixer:

| Dimension | Poles | Description |
|-----------|-------|-------------|
| dim₁ | Object ↔ Action | Grammatical structure of the phrase |
| dim₂ | Positive ↔ Negative | Emotional tone and sentiment |
| dim₃ | Abstract ↔ Concrete | Level of generalization |
| dim₄ | I ↔ World | Point of observation |
| dim₅ | Living ↔ Mechanical | Essential nature |

These values are not hardcoded but emerge from data. The model distributes meaning across axes.

### Components

1. **Encoder** - Compresses text into 5D semantic space
2. **Decoder** - Reconstructs text with reasoning about dimension values
3. **Space** - Interface for exploration and manipulation
4. **Visualizer** - Creates visual representations of semantic vectors

## Installation

### Basic Installation

```bash
git clone https://github.com/danilivashyna/Atlas.git
cd Atlas
pip install -r requirements.txt
pip install -e .
```

### Dependencies

- Python 3.8+
- numpy
- matplotlib
- Optional: torch, transformers (for advanced features)

## Quick Start

### Python

```python
from atlas import SemanticSpace

# Initialize
space = SemanticSpace()

# Encode text to 5D vector
vector = space.encode("Собака")
print(vector)  # [-0.46, 0.0, 0.46, 0.0, 0.46]

# Decode with reasoning
result = space.decode(vector, with_reasoning=True)
print(result['reasoning'])
print(result['text'])
```

### Command Line

```bash
# Show dimension information
atlas info

# Encode text
atlas encode "Собака бежит" --explain

# Decode vector
atlas decode --vector 0.1 0.9 -0.5 0.2 0.8 --reasoning

# Manipulate meaning
atlas manipulate "Радость" --dimension 1 --value -0.9
```

## Python API

### SemanticSpace

Main interface for working with semantic space.

#### Methods

##### `encode(text: str | List[str]) -> np.ndarray`

Encode text into 5D semantic vector.

```python
vector = space.encode("Любовь")
# Returns: array([0.0, 0.46, 0.0, 0.0, 0.0])
```

##### `decode(vector: np.ndarray, with_reasoning: bool = False) -> str | Dict`

Decode vector back to text, optionally with reasoning.

```python
# Simple decode
text = space.decode(vector)

# With reasoning
result = space.decode(vector, with_reasoning=True)
print(result['reasoning'])
print(result['text'])
```

##### `transform(text: str, show_reasoning: bool = True) -> Dict`

Complete transformation: text → vector → text with interpretation.

```python
result = space.transform("Жизнь", show_reasoning=True)
```

##### `manipulate_dimension(text: str, dimension: int, new_value: float) -> Dict`

Manipulate a specific dimension to see how meaning changes.

```python
result = space.manipulate_dimension(
    "Радость",
    dimension=1,  # Emotion
    new_value=-0.9  # Make negative
)
```

##### `interpolate(text1: str, text2: str, steps: int = 5) -> List[Dict]`

Interpolate between two concepts in semantic space.

```python
results = space.interpolate("Любовь", "Страх", steps=5)
for r in results:
    print(f"α={r['alpha']:.2f}: {r['decoded']['text']}")
```

##### `explore_dimension(text: str, dimension: int, range_vals: List[float]) -> List[Dict]`

Explore how varying one dimension affects meaning.

```python
results = space.explore_dimension(
    "Жизнь",
    dimension=4,  # Living ↔ Mechanical
    range_vals=[-1, -0.5, 0, 0.5, 1]
)
```

##### `visualize_vector(vector: np.ndarray, title: str) -> plt.Figure`

Create a radar chart visualization of a semantic vector.

```python
fig = space.visualize_vector(vector, title="Concept: Dog")
fig.savefig("vector.png")
```

##### `visualize_space_2d(texts: List[str], dimensions: tuple) -> plt.Figure`

Visualize multiple texts in 2D projection.

```python
texts = ["Собака", "Машина", "Любовь", "Страх"]
fig = space.visualize_space_2d(texts, dimensions=(1, 2))
fig.savefig("space_2d.png")
```

### DimensionMapper

Utility for interpreting dimensional values.

```python
from atlas import DimensionMapper, SemanticDimension

# Get dimension info
info = DimensionMapper.get_dimension_info(SemanticDimension.DIM1)
print(info.name, info.poles, info.description)

# Interpret value
interpretation = DimensionMapper.interpret_value(
    SemanticDimension.DIM2, 
    0.8
)
print(interpretation)  # "strongly negative"

# Explain complete vector
explanation = DimensionMapper.explain_vector([0.1, 0.9, -0.5, 0.2, 0.8])
print(explanation)
```

## Command Line Interface

### atlas info

Display information about all dimensions.

```bash
atlas info
```

### atlas encode

Encode text to 5D vector.

```bash
atlas encode "Собака бежит" --explain
atlas encode "Love" --output result.json
```

### atlas decode

Decode 5D vector to text.

```bash
atlas decode --vector 0.1 0.9 -0.5 0.2 0.8 --reasoning
atlas decode --input vector.json --reasoning
```

### atlas transform

Transform text through semantic space.

```bash
atlas transform "Любовь" --reasoning
```

### atlas manipulate

Manipulate a specific dimension.

```bash
atlas manipulate "Радость" --dimension 1 --value -0.9 --reasoning
```

Options:
- `-d, --dimension`: Dimension to change (0-4)
- `-v, --value`: New value (-1 to 1)
- `--reasoning`: Show reasoning process

### atlas interpolate

Interpolate between two concepts.

```bash
atlas interpolate "Любовь" "Ненависть" --steps 7
```

### atlas explore

Explore how a dimension affects meaning.

```bash
atlas explore "Жизнь" --dimension 4 --steps 5
atlas explore "Life" --dimension 2 --range -1 -0.5 0 0.5 1
```

## Examples

### Example 1: Basic Encoding and Decoding

```python
from atlas import SemanticSpace

space = SemanticSpace()

# Encode
text = "Собака"
vector = space.encode(text)
print(f"Vector: {vector}")

# Decode with reasoning
result = space.decode(vector, with_reasoning=True)
print("Reasoning:")
print(result['reasoning'])
print(f"\nDecoded: {result['text']}")
```

### Example 2: Dimension Manipulation

```python
# Start with a positive emotion
result = space.manipulate_dimension(
    "Радость",
    dimension=1,  # Emotion axis
    new_value=-0.9  # Make very negative
)

print(f"Original: {result['original']['decoded']['text']}")
print(f"Modified: {result['modified']['decoded']['text']}")
```

### Example 3: Semantic Interpolation

```python
# Watch meaning transform gradually
results = space.interpolate("Любовь", "Ненависть", steps=7)

for r in results:
    print(f"Step {r['step']} (α={r['alpha']:.2f}): {r['decoded']['text']}")
```

### Example 4: Visualization

```python
import matplotlib.pyplot as plt

# Visualize a concept
vector = space.encode("Собака")
fig = space.visualize_vector(vector, "Concept: Dog")
plt.savefig("dog_vector.png")

# Compare multiple concepts
texts = ["Собака", "Машина", "Любовь", "Страх"]
fig = space.visualize_space_2d(texts, dimensions=(1, 2))
plt.savefig("semantic_space.png")
```

## Architecture

### File Structure

```
atlas/
├── __init__.py         # Package initialization
├── dimensions.py       # Dimension definitions and interpretation
├── encoder.py          # Text → 5D vector encoding
├── decoder.py          # 5D vector → text decoding with reasoning
├── space.py            # Main interface combining all components
└── cli.py              # Command-line interface

examples/
├── basic_usage.py      # Basic API examples
└── visualization.py    # Visualization examples

tests/
├── test_dimensions.py  # Tests for dimension mapping
├── test_encoder.py     # Tests for encoder
├── test_decoder.py     # Tests for decoder
└── test_space.py       # Tests for semantic space
```

### Design Principles

1. **Interpretability First** - Every operation includes reasoning
2. **Minimal Dependencies** - Core functionality works with just numpy
3. **Extensibility** - Easy to add new encoders/decoders
4. **User-Friendly** - Both Python API and CLI available

## Advanced Usage

### Custom Encoders

You can create custom encoders for specific domains:

```python
from atlas.encoder import SimpleSemanticEncoder

class DomainSpecificEncoder(SimpleSemanticEncoder):
    def encode_text(self, text):
        # Custom encoding logic
        pass
```

### Batch Processing

Process multiple texts efficiently:

```python
texts = ["Text 1", "Text 2", "Text 3"]
vectors = space.encode(texts)  # Returns (N, 5) array

# Batch decode
for vector in vectors:
    result = space.decode(vector, with_reasoning=True)
    print(result['text'])
```

### Integration with Machine Learning

Use Atlas vectors as features:

```python
from sklearn.cluster import KMeans

# Encode texts
texts = ["dog", "cat", "car", "bike", "love", "hate"]
vectors = space.encode(texts)

# Cluster in semantic space
kmeans = KMeans(n_clusters=3)
clusters = kmeans.fit_predict(vectors)
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

### Development Setup

```bash
git clone https://github.com/danilivashyna/Atlas.git
cd Atlas
pip install -e .[dev]
pytest tests/
```

## License

MIT License - see LICENSE file for details.

## Citation

If you use Atlas in your research, please cite:

```bibtex
@software{atlas2025,
  title={Atlas: Semantic Space Control Panel},
  author={danilivashyna},
  year={2025},
  url={https://github.com/danilivashyna/Atlas}
}
```
