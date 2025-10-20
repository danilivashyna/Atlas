# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

# Hierarchical Semantic Space — "Matryoshka 5D"

## Overview

The Hierarchical Semantic Space extends Atlas's 5D semantic model with a multi-level tree structure where each dimension can recursively have child dimensions, enabling fine-grained semantic decomposition.

**Key Concept**: Instead of a flat 1536-dimensional or 5-dimensional vector, we organize semantics hierarchically:
- **Level 0**: 5 "main handles" (coarse semantics)
- **Level 1+**: Each handle has 5 sub-dimensions (fine semantics)
- **Dynamic depth**: Expands lazily based on router confidence

## Architecture

### Hierarchical Tree Structure (tree@v2)

```json
{
  "value": [0.12, 0.88, -0.41, 0.05, 0.67],
  "label": "coarse",
  "key": "root",
  "weight": 1.0,
  "children": [
    {
      "key": "dim1",
      "value": [0.2, -0.1, 0.6, -0.4, 0.3],
      "label": "agent/action",
      "weight": 0.8,
      "children": [...]
    },
    {
      "key": "dim2",
      "value": [0.9, 0.1, -0.2, 0.0, 0.0],
      "label": "valence",
      "weight": 0.7,
      "children": [...]
    }
    // ... 3 more dimensions
  ]
}
```

### Components

#### 1. HierarchicalEncoder

Encodes text into a tree structure with:
- **Router Network**: Computes confidence weights for each dimension
- **Child Generation**: Creates 5D vectors for each child dimension
- **Lazy Expansion**: Only expands branches above `expand_threshold`

```python
from atlas.hierarchical import HierarchicalEncoder

encoder = HierarchicalEncoder()
tree = encoder.encode_hierarchical(
    text="Собака",
    max_depth=2,              # Maximum tree depth
    expand_threshold=0.2      # Router confidence threshold
)
```

#### 2. HierarchicalDecoder

Decodes tree to text with path-wise reasoning:
- **Path Extraction**: Identifies all semantic paths in tree
- **Weighted Combination**: Combines paths by their router weights
- **Path Reasoning**: Explains which branches contributed most

```python
from atlas.hierarchical import HierarchicalDecoder

decoder = HierarchicalDecoder()
result = decoder.decode_hierarchical(
    tree=tree,
    top_k=3,                  # Top contributing paths
    with_reasoning=True
)

print(result['text'])
for r in result['reasoning']:
    print(f"{r.path}: {r.label} (weight={r.weight})")
```

## API Endpoints

### POST /encode_h

Encode text to hierarchical tree.

**Request:**
```json
{
  "text": "Любовь",
  "max_depth": 2,
  "expand_threshold": 0.2,
  "lang": "ru"
}
```

**Response:**
```json
{
  "tree": {
    "value": [0.12, 0.88, -0.41, 0.05, 0.67],
    "label": "coarse",
    "key": "root",
    "children": [...]
  },
  "norm": true,
  "max_depth": 2,
  "trace_id": "req_abc123",
  "timestamp": "2025-01-19T12:34:56.789Z"
}
```

### POST /decode_h

Decode hierarchical tree to text with path reasoning.

**Request:**
```json
{
  "tree": {
    "value": [0.12, 0.88, -0.41, 0.05, 0.67],
    "label": "coarse",
    "key": "root"
  },
  "top_k": 3
}
```

**Response:**
```json
{
  "text": "Собака",
  "reasoning": [
    {
      "path": "dim2/dim2.4",
      "weight": 0.73,
      "label": "домашнее-живое-позитив",
      "evidence": ["Emotion: positive", "Nature: living"]
    }
  ],
  "explainable": true,
  "trace_id": "req_xyz789",
  "timestamp": "2025-01-19T12:34:56.789Z"
}
```

### POST /manipulate_h

Manipulate specific paths in the tree.

**Request:**
```json
{
  "text": "Собака",
  "edits": [
    {
      "path": "dim2/dim2.4",
      "value": [0.9, 0.1, -0.2, 0.0, 0.0]
    },
    {
      "path": "dim3",
      "value": [-0.5, 0.3, 0.8, 0.1, -0.2]
    }
  ]
}
```

**Response:**
```json
{
  "original": {
    "text": "Собака",
    "tree": {...},
    "decoded": {...}
  },
  "modified": {
    "tree": {...},
    "decoded": {...},
    "edits_applied": [...]
  },
  "trace_id": "req_manipulate",
  "timestamp": "2025-01-19T12:34:56.789Z"
}
```

## CLI Commands

### encode-h

Encode text to hierarchical tree:

```bash
atlas encode-h "Любовь" --max-depth 2 --expand-threshold 0.2 -o tree.json
```

Output:
```
======================================================================
  HIERARCHICAL ENCODING
======================================================================

Input text: "Любовь"
Max depth: 2
Expand threshold: 0.2

Hierarchical Tree:
[root] coarse (w=1.00)
  value: [0.00, 0.46, 0.00, 0.00, 0.00]
  [dim1] Structure (neutral) (w=1.00)
    value: [0.00, 0.46, 0.00, 0.00, 0.00]
  [dim2] Emotion (slightly negative) (w=1.00)
    value: [-0.01, 0.21, -0.04, 0.08, -0.01]
    [dim2/dim1] ... (w=0.45)
    [dim2/dim2] ... (w=0.32)
  ...
```

### decode-h

Decode hierarchical tree to text:

```bash
atlas decode-h --input tree.json --top-k 3 --reasoning
```

Output:
```
======================================================================
  HIERARCHICAL DECODING
======================================================================

Path Reasoning:
  root: coarse (weight=1.00)
    Evidence: Emotion: positive, Nature: living
  dim2/dim2.4: домашнее-живое-позитив (weight=0.73)
    Evidence: Emotion: positive, Abstraction: concrete
  dim5: Nature (strongly living) (weight=0.68)
    Evidence: Nature: living, Structure: object

Decoded Text: "Собака"
```

### manipulate-h

Manipulate tree by path:

```bash
atlas manipulate-h "Собака" \
  --edit "dim2/dim2.4=0.9,0.1,-0.2,0.0,0.0" \
  --edit "dim3=-0.5,0.3,0.8,0.1,-0.2" \
  --reasoning
```

Output:
```
======================================================================
  HIERARCHICAL MANIPULATION
======================================================================

=== ORIGINAL ===
Text: "Собака"
Decoded: "Собака"
Path reasoning:
  root: coarse (w=1.00)
  dim2/dim2.4: домашнее-живое-позитив (w=0.73)

=== MODIFIED ===
Edits applied: 2
  dim2/dim2.4 = [0.90, 0.10, -0.20, 0.00, 0.00]
  dim3 = [-0.50, 0.30, 0.80, 0.10, -0.20]

Decoded: "Кот"
Path reasoning:
  root: coarse (w=1.00)
  dim2/dim2.4: modified-valence (w=0.90)
```

## Python API

### Basic Usage

```python
from atlas.hierarchical import HierarchicalEncoder, HierarchicalDecoder

# Initialize
encoder = HierarchicalEncoder()
decoder = HierarchicalDecoder()

# Encode text
tree = encoder.encode_hierarchical(
    "Собака",
    max_depth=2,
    expand_threshold=0.2
)

# Decode with reasoning
result = decoder.decode_hierarchical(tree, top_k=3, with_reasoning=True)

print(f"Text: {result['text']}")
for r in result['reasoning']:
    print(f"  {r.path}: {r.label} (weight={r.weight:.2f})")
    for evidence in r.evidence:
        print(f"    - {evidence}")
```

### Path Manipulation

```python
# Manipulate specific path
new_value = [0.9, 0.1, -0.2, 0.0, 0.0]
modified_tree = decoder.manipulate_path(tree, "dim2/dim2.4", new_value)

# Decode modified tree
modified_result = decoder.decode_hierarchical(modified_tree)
print(f"Modified text: {modified_result['text']}")
```

### Flatten to Vector

```python
# Convert hierarchical tree to flat vector (for compatibility)
flat_vector = encoder.flatten_tree(tree)
print(f"Flat 5D vector: {flat_vector}")
```

## Schema Validation

### TreeNode Validation

All tree nodes are validated:

1. **Value Range**: All values must be in `[-1, 1]`
2. **No NaN/Inf**: Values cannot be NaN or Infinity
3. **5 Dimensions**: Values must have exactly 5 components
4. **5 Children**: If children exist, must have exactly 5 (one per dimension)

```python
from atlas.hierarchical import TreeNode

# Valid node
node = TreeNode(
    value=[0.1, 0.2, 0.3, 0.4, 0.5],
    label="test",
    key="dim1"
)

# Invalid: NaN value
try:
    TreeNode(value=[0.1, float('nan'), 0.3, 0.4, 0.5])
except ValueError as e:
    print(f"Error: {e}")  # "Vector values cannot contain NaN or Inf"

# Invalid: out of range
try:
    TreeNode(value=[0.1, 1.5, 0.3, 0.4, 0.5])
except ValueError as e:
    print(f"Error: {e}")  # "Vector values must be in range [-1, 1]"
```

## Benefits

### 1. Explainability Through Paths

Instead of opaque 1536D vectors, understand meaning through interpretable paths:
- `root`: Overall semantics
- `dim2`: Emotional tone
- `dim2/dim2.4`: Fine-grained positive emotion for domestic contexts

### 2. Computational Efficiency

**Lazy Expansion**: Only compute branches above confidence threshold
- Depth 0 (root only): 5 values
- Depth 1 (selective): ~10-15 values (only high-confidence branches)
- Depth 2 (full): ~155 values (still much less than 1536)

### 3. Surgical Control

Manipulate specific semantic aspects without affecting others:
```python
# Change only emotional valence of domestic contexts
decoder.manipulate_path(tree, "dim2/dim2.4", [0.9, 0.1, 0.0, 0.0, 0.0])
```

### 4. Hierarchical Reasoning

See how global and local semantics combine:
```
root (coarse): "living thing"
  └─ dim5 (nature): "domestic"
      └─ dim5.2 (fine): "canine family"
```

## Roadmap

### v0.1.1 (Current)
- ✅ Basic hierarchical encoding/decoding
- ✅ Path-wise reasoning
- ✅ Path manipulation
- ✅ REST API endpoints
- ✅ CLI commands

### v0.1.2 (Planned)
- [ ] Loss functions: orthogonality, sparsity, router entropy
- [ ] Advanced router networks (learned gating)
- [ ] Hierarchical metrics (H-Coherence, H-Stability)

### v0.1.3 (Future)
- [ ] Distillation from 1536D teacher models
- [ ] Visualization (lazy expand, breadcrumbs, path sliders)
- [ ] Benchmark utilities (p50/p95 latency)
- [ ] Depth 2-3 optimization

### v0.2 (Future)
- [ ] Neural encoder/decoder heads
- [ ] Multi-language support
- [ ] Batch processing
- [ ] Custom dimension semantics

## Examples

### Example 1: Semantic Analysis

```python
from atlas.hierarchical import HierarchicalEncoder, HierarchicalDecoder

encoder = HierarchicalEncoder()
decoder = HierarchicalDecoder()

# Analyze text
text = "Радостный щенок играет в парке"
tree = encoder.encode_hierarchical(text, max_depth=2, expand_threshold=0.15)

result = decoder.decode_hierarchical(tree, top_k=5, with_reasoning=True)

print(f"Original: {text}")
print(f"Reconstructed: {result['text']}")
print("\nSemantic Path Analysis:")
for r in result['reasoning']:
    print(f"  {r.path}: {r.label}")
    print(f"    Weight: {r.weight:.2f}")
    print(f"    Evidence: {', '.join(r.evidence)}")
```

### Example 2: Semantic Transformation

```python
# Transform sentiment while preserving other aspects
original = "Грустный волк воет в лесу"
tree = encoder.encode_hierarchical(original, max_depth=2)

# Make it positive
modified_tree = decoder.manipulate_path(
    tree,
    path="dim2",  # Emotion dimension
    new_value=[0.0, 0.9, 0.1, 0.0, 0.0]  # Strongly positive
)

result = decoder.decode_hierarchical(modified_tree)
print(f"Original: {original}")
print(f"Modified: {result['text']}")
# Expected: "Радостный волк воет в лесу" or similar
```

### Example 3: Semantic Interpolation

```python
# Interpolate through hierarchical space
text1 = "Любовь"
text2 = "Ненависть"

tree1 = encoder.encode_hierarchical(text1, max_depth=1)
tree2 = encoder.encode_hierarchical(text2, max_depth=1)

# Interpolate at root level
for alpha in [0.0, 0.25, 0.5, 0.75, 1.0]:
    interpolated_tree = tree1  # Copy
    # Mix values: v = (1-α)*v1 + α*v2
    mixed_value = [
        (1-alpha)*v1 + alpha*v2
        for v1, v2 in zip(tree1.value, tree2.value)
    ]
    interpolated_tree.value = mixed_value

    result = decoder.decode_hierarchical(interpolated_tree)
    print(f"α={alpha:.2f}: {result['text']}")
```

## Comparison: Flat vs Hierarchical

| Aspect | Flat 5D | Hierarchical (Matryoshka) |
|--------|---------|---------------------------|
| **Dimensions** | 5 fixed | 5 × 5 × ... (dynamic) |
| **Explainability** | Global only | Path-wise (coarse→fine) |
| **Control** | Dimension-level | Path-level (surgical) |
| **Computation** | Fixed (5 values) | Adaptive (5-155 values) |
| **Reasoning** | Single-level | Multi-level hierarchy |
| **Memory** | 5 × float32 = 20B | ~50-600B (depth-dependent) |

## See Also

- [DOCUMENTATION.md](../DOCUMENTATION.md) - Main Atlas documentation
- [API Documentation](http://localhost:8000/docs) - Interactive API docs
- [Examples](../examples/) - Code examples
- [Tests](../tests/test_hierarchical.py) - Comprehensive test suite

## License

SPDX-License-Identifier: AGPL-3.0-or-later

This feature is part of Atlas, dual-licensed under AGPLv3 and Commercial licenses.
See [LICENSE](../LICENSE) for details.
