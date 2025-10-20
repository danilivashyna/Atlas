# Atlas v0.2 API Reference

Complete API reference for Atlas v0.2 semantic space.

## Table of Contents

- [Core Classes](#core-classes)
  - [SemanticSpace](#semanticspace)
  - [HierarchicalEncoder](#hierarchicalencoder)
  - [HierarchicalDecoder](#hierarchicaldecoder)
- [REST API Endpoints](#rest-api-endpoints)
  - [Health Endpoints](#health-endpoints)
  - [Flat Endpoints](#flat-endpoints)
  - [Hierarchical Endpoints](#hierarchical-endpoints)
- [CLI Commands](#cli-commands)
- [Data Models](#data-models)

---

## Core Classes

### SemanticSpace

Main interface for working with the 5D semantic space.

```python
from atlas import SemanticSpace

space = SemanticSpace()
```

#### Methods

##### `encode(text: str) -> np.ndarray`

Encode text into a 5D vector.

**Parameters:**
- `text` (str): Text to encode

**Returns:**
- `np.ndarray`: 5D vector in range [-1, 1]

**Example:**
```python
vector = space.encode("Собака")
# Returns: array([0.12, 0.89, -0.45, 0.18, 0.82])
```

##### `decode(vector: np.ndarray, with_reasoning: bool = False) -> Union[str, dict]`

Decode 5D vector back to text.

**Parameters:**
- `vector` (np.ndarray): 5D vector
- `with_reasoning` (bool): Include reasoning process in output

**Returns:**
- `str`: Decoded text (if `with_reasoning=False`)
- `dict`: `{"text": str, "reasoning": str}` (if `with_reasoning=True`)

**Example:**
```python
# Without reasoning
text = space.decode(vector)
# Returns: "Собака"

# With reasoning
result = space.decode(vector, with_reasoning=True)
# Returns: {
#   "text": "Собака",
#   "reasoning": "dim₁ = 0.12 → слегка action..."
# }
```

##### `transform(text: str, show_reasoning: bool = False) -> dict`

Transform text through encode/decode cycle.

**Parameters:**
- `text` (str): Input text
- `show_reasoning` (bool): Include reasoning in output

**Returns:**
- `dict`: Contains `original_text`, `vector`, `decoded`

**Example:**
```python
result = space.transform("Любовь", show_reasoning=True)
# Returns: {
#   "original_text": "Любовь",
#   "vector": [0.15, 0.92, 0.35, -0.10, 0.68],
#   "decoded": {
#     "text": "Любовь",
#     "reasoning": "..."
#   }
# }
```

##### `manipulate_dimension(text: str, dimension: int, new_value: float) -> dict`

Change a specific dimension and see the effect.

**Parameters:**
- `text` (str): Input text
- `dimension` (int): Dimension index (0-4)
- `new_value` (float): New value for dimension (-1 to 1)

**Returns:**
- `dict`: Contains `original` and `modified` states

**Example:**
```python
result = space.manipulate_dimension("Радость", dimension=1, new_value=-0.9)
# Returns: {
#   "original": {
#     "text": "Радость",
#     "vector": [...],
#     "decoded": {"text": "Радость"}
#   },
#   "modified": {
#     "dimension_changed": "dim₁ (Позитив ↔ Негатив)",
#     "new_value": -0.9,
#     "vector": [...],
#     "decoded": {"text": "Грусть"}
#   }
# }
```

##### `interpolate(text1: str, text2: str, steps: int = 5) -> List[dict]`

Create smooth transition between two concepts.

**Parameters:**
- `text1` (str): Start text
- `text2` (str): End text
- `steps` (int): Number of interpolation steps

**Returns:**
- `List[dict]`: List of interpolation results

**Example:**
```python
results = space.interpolate("Любовь", "Страх", steps=5)
# Returns: [
#   {"step": 0, "alpha": 0.0, "vector": [...], "decoded": {"text": "Любовь"}},
#   {"step": 1, "alpha": 0.25, "vector": [...], "decoded": {"text": "Волнение"}},
#   ...
# ]
```

##### `explore_dimension(text: str, dimension: int, range_vals: List[float]) -> List[dict]`

Explore how a dimension affects meaning.

**Parameters:**
- `text` (str): Base text
- `dimension` (int): Dimension to explore (0-4)
- `range_vals` (List[float]): Values to try

**Returns:**
- `List[dict]`: List of exploration results

**Example:**
```python
import numpy as np
results = space.explore_dimension(
    "Жизнь",
    dimension=2,
    range_vals=np.linspace(-1, 1, 5)
)
# Returns: [
#   {"dimension": "dim₂", "value": -1.0, "decoded": {"text": "Философия"}},
#   {"dimension": "dim₂", "value": -0.5, "decoded": {"text": "Мысль"}},
#   ...
# ]
```

##### `get_dimension_info() -> dict`

Get information about all dimensions.

**Returns:**
- `dict`: Dimension information

**Example:**
```python
info = space.get_dimension_info()
# Returns: {
#   "dim0": {
#     "name": "Structure",
#     "poles": ["Object", "Action"],
#     "description": "Defines the grammatical structure"
#   },
#   ...
# }
```

---

### HierarchicalEncoder

Encoder for hierarchical semantic trees (v0.2).

```python
from atlas.hierarchical import HierarchicalEncoder

encoder = HierarchicalEncoder()
```

#### Methods

##### `encode_hierarchical(text: str, max_depth: int = 1, expand_threshold: float = 0.2) -> TreeNode`

Encode text into hierarchical tree structure.

**Parameters:**
- `text` (str): Text to encode
- `max_depth` (int): Maximum tree depth (0-5)
- `expand_threshold` (float): Minimum weight to expand branches (0-1)

**Returns:**
- `TreeNode`: Root of hierarchical tree

**Example:**
```python
tree = encoder.encode_hierarchical(
    "Любовь",
    max_depth=2,
    expand_threshold=0.2
)
# Returns TreeNode with recursive children
```

---

### HierarchicalDecoder

Decoder for hierarchical semantic trees (v0.2).

```python
from atlas.hierarchical import HierarchicalDecoder

decoder = HierarchicalDecoder()
```

#### Methods

##### `decode_hierarchical(tree: TreeNode, top_k: int = 3, with_reasoning: bool = False) -> dict`

Decode hierarchical tree to text.

**Parameters:**
- `tree` (TreeNode): Hierarchical tree
- `top_k` (int): Number of top paths to consider
- `with_reasoning` (bool): Include path reasoning

**Returns:**
- `dict`: Contains `text` and optionally `reasoning`

**Example:**
```python
result = decoder.decode_hierarchical(tree, top_k=3, with_reasoning=True)
# Returns: {
#   "text": "Любовь",
#   "reasoning": [
#     PathReasoning(path="root", label="love", weight=1.0, ...),
#     PathReasoning(path="dim2", label="positive-affective", weight=0.92, ...),
#     ...
#   ]
# }
```

##### `manipulate_path(tree: TreeNode, path: str, new_value: List[float]) -> TreeNode`

Modify specific path in tree.

**Parameters:**
- `tree` (TreeNode): Hierarchical tree
- `path` (str): Path to target node (e.g., "dim2/dim2.4")
- `new_value` (List[float]): New 5D vector for node

**Returns:**
- `TreeNode`: Modified tree

**Example:**
```python
modified = decoder.manipulate_path(
    tree,
    path="dim2/dim2.4",
    new_value=[0.9, 0.1, -0.2, 0.0, 0.0]
)
```

---

## REST API Endpoints

Base URL: `http://localhost:8000`

### Health Endpoints

#### `GET /`

Root endpoint with API information.

**Response:**
```json
{
  "name": "Atlas Semantic Space API",
  "version": "0.2.0a1",
  "description": "5D semantic space for interpretable text representations",
  "endpoints": {...}
}
```

#### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2025-10-20T08:30:00Z"
}
```

#### `GET /ready`

Readiness check endpoint.

**Response:**
```json
{
  "ready": true,
  "components": {
    "encoder": "ready",
    "decoder": "ready"
  }
}
```

#### `GET /metrics`

Basic metrics endpoint.

**Response:**
```json
{
  "requests_total": 42,
  "requests_success": 40,
  "requests_error": 2
}
```

---

### Flat Endpoints

#### `POST /encode`

Encode text to 5D vector.

**Request:**
```json
{
  "text": "Собака",
  "lang": "ru"
}
```

**Response:**
```json
{
  "vector": [0.12, 0.89, -0.45, 0.18, 0.82],
  "text": "Собака"
}
```

#### `POST /decode`

Decode 5D vector to text.

**Request:**
```json
{
  "vector": [0.1, 0.9, -0.5, 0.2, 0.8],
  "top_k": 3,
  "with_reasoning": false
}
```

**Response:**
```json
{
  "text": "Собака",
  "candidates": ["Собака", "Кот", "Животное"]
}
```

#### `POST /explain`

Explain text semantic dimensions.

**Request:**
```json
{
  "text": "Любовь",
  "lang": "ru"
}
```

**Response:**
```json
{
  "text": "Любовь",
  "vector": [0.15, 0.92, 0.35, -0.10, 0.68],
  "explanation": {
    "dim0": {"value": 0.15, "interpretation": "слегка action"},
    "dim1": {"value": 0.92, "interpretation": "сильно positive"},
    ...
  }
}
```

---

### Hierarchical Endpoints

#### `POST /encode_h`

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
    "key": "root",
    "value": [0.15, 0.92, 0.35, -0.10, 0.68],
    "weight": 1.0,
    "label": "love",
    "children": [...]
  }
}
```

#### `POST /decode_h`

Decode hierarchical tree to text.

**Request:**
```json
{
  "tree": {...},
  "top_k": 3,
  "with_reasoning": true
}
```

**Response:**
```json
{
  "text": "Любовь",
  "reasoning": [
    {
      "path": "root",
      "label": "love",
      "weight": 1.0,
      "evidence": ["positive", "affective", "organic"]
    },
    ...
  ]
}
```

#### `POST /manipulate_h`

Manipulate hierarchical tree by paths.

**Request:**
```json
{
  "text": "Собака",
  "edits": [
    {
      "path": "dim2/dim2.4",
      "value": [0.9, 0.1, -0.2, 0.0, 0.0]
    }
  ],
  "max_depth": 2
}
```

**Response:**
```json
{
  "original": {
    "text": "Собака",
    "tree": {...}
  },
  "modified": {
    "text": "Счастливая собака",
    "tree": {...},
    "edits_applied": 1
  }
}
```

---

## CLI Commands

### Basic Commands

```bash
# Show dimension information
atlas info

# Encode text
atlas encode "Собака" [--explain] [--output FILE]

# Decode vector
atlas decode --vector V1 V2 V3 V4 V5 [--reasoning]
atlas decode --input FILE [--reasoning]

# Transform text
atlas transform "Любовь" [--reasoning]

# Explain (alias for transform with reasoning)
atlas explain "Любовь"
```

### Manipulation Commands

```bash
# Manipulate dimension
atlas manipulate TEXT --dimension DIM --value VAL [--reasoning]

# Interpolate between texts
atlas interpolate TEXT1 TEXT2 [--steps N]

# Explore dimension
atlas explore TEXT --dimension DIM [--steps N] [--range V1 V2 ...]
```

### Hierarchical Commands

```bash
# Hierarchical encode
atlas encode-h TEXT [--max-depth N] [--expand-threshold T] [--output FILE]

# Hierarchical decode
atlas decode-h --input FILE [--top-k N] [--reasoning]

# Hierarchical manipulate
atlas manipulate-h TEXT --edit PATH=V1,V2,V3,V4,V5 [--reasoning]
```

---

## Data Models

### TreeNode

Hierarchical tree node structure.

```python
class TreeNode:
    key: str                    # Node identifier (e.g., "root", "dim2", "dim2.4")
    value: List[float]          # 5D vector
    weight: float               # Importance weight (0-1)
    label: str                  # Human-readable label
    children: List[TreeNode]    # Recursive children
```

### PathReasoning

Path reasoning for hierarchical decoding.

```python
class PathReasoning:
    path: str                   # Full path (e.g., "root/dim2/dim2.4")
    label: str                  # Node label
    weight: float               # Path weight
    evidence: List[str]         # Supporting evidence
```

---

## Dimension Reference

| Index | Name | Poles | Description |
|-------|------|-------|-------------|
| 0 | Structure | Object ↔ Action | Grammatical structure |
| 1 | Emotion | Positive ↔ Negative | Emotional tone |
| 2 | Abstraction | Abstract ↔ Concrete | Level of generalization |
| 3 | Perspective | I ↔ World | Point of observation |
| 4 | Nature | Living ↔ Mechanical | Essential nature |

---

## Error Handling

All API endpoints return errors in this format:

```json
{
  "error": "Error message",
  "detail": "Detailed description",
  "trace_id": "uuid-v4",
  "timestamp": "2025-10-20T08:30:00Z"
}
```

Common HTTP status codes:
- `200` - Success
- `400` - Bad Request (invalid input)
- `422` - Validation Error
- `500` - Internal Server Error

---

## Examples

See the [demos/](../demos/) directory for complete examples:
- [demo_01_basic.md](../demos/demo_01_basic.md) - Basic usage
- [demo_02_hierarchical.md](../demos/demo_02_hierarchical.md) - Hierarchical features
- [demo_03_cli.md](../demos/demo_03_cli.md) - CLI reference

---

**Atlas v0.2 API Reference** - Complete documentation for developers 📚
