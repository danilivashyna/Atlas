# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

# Hierarchical 5D Semantic Space (v0.2) Schema

## Core Node Structure

```json
{
  "value": [d1, d2, d3, d4, d5],
  "label": "coarse" | "fine",
  "key": "dim2.4",
  "children": [
    { "value": [...], "label": "fine", ... }
  ],
  "confidence": 0.95
}
```

### Field Descriptions

- **value** (float[]): 5-dimensional vector in [-1, 1] range
  - d1: Object ↔ Action
  - d2: Positive ↔ Negative
  - d3: Abstract ↔ Concrete
  - d4: I ↔ World
  - d5: Living ↔ Mechanical

- **label**: Granularity level ("coarse" | "fine" | "sub-fine")
- **key**: Human-readable ID (e.g., "dim2.4" = dimension 2, quadrant 4)
- **children**: Sub-trees for hierarchical expansion
- **confidence**: Router confidence [0, 1]

## API Endpoints v0.2

### 1. POST /encode_h - Hierarchical Encoding

**Request:**
```json
{
  "text": "Собака прыгает",
  "max_depth": 2,
  "expand_threshold": 0.7
}
```

**Response:**
```json
{
  "tree": {
    "value": [0.3, 0.8, -0.2, 0.5, 0.9],
    "label": "coarse",
    "key": "root",
    "children": [
      {
        "value": [0.35, 0.85, -0.15, 0.55, 0.92],
        "label": "fine",
        "key": "dim1.1"
      }
    ],
    "confidence": 0.98
  },
  "norm": 1.0,
  "schema_id": "v0.2-20250101"
}
```

### 2. POST /decode_h - Hierarchical Decoding

**Request:**
```json
{
  "tree": { /* tree object */ },
  "top_k": 3
}
```

**Response:**
```json
{
  "text": "Собака прыгает",
  "reasoning": [
    {
      "dimension": 1,
      "label": "Object → Action",
      "value": 0.3,
      "interpretation": "Action-oriented: jumping"
    },
    {
      "dimension": 2,
      "label": "Positive ↔ Negative",
      "value": 0.8,
      "interpretation": "Positive: agile, joyful"
    }
  ]
}
```

### 3. POST /manipulate_h - Surgical Manipulation

**Request:**
```json
{
  "text": "Собака",
  "edits": [
    {
      "dimension": 2,
      "target_value": -0.8,
      "reason": "Make negative: angry dog"
    }
  ]
}
```

**Response:**
```json
{
  "original": {
    "text": "Собака",
    "vector": [0.3, 0.8, -0.2, 0.5, 0.9]
  },
  "modified": {
    "text": "Злая собака",
    "vector": [0.3, -0.8, -0.2, 0.5, 0.9]
  },
  "changes": [
    {
      "dimension": 2,
      "before": 0.8,
      "after": -0.8,
      "semantic_shift": "positive→negative"
    }
  ]
}
```

## Loss Functions (v0.2)

### 1. Orthogonal Projection Loss

```
ortho_loss(W) = ||W^T W - I||_F
```

Ensures projection matrix W is orthogonal (preserves distances in 5D space).

### 2. L1 Sparsity Loss

```
l1_sparsity(z) = mean(|z|)
```

Encourages interpretability: dimensions should be "on/off" rather than mixed.

### 3. Router Entropy Loss

```
router_entropy(p) = -mean(sum(p * log(p)))
```

Prevents collapse: ensures router uses all children at lower depths.

## Metrics (v0.2)

### 1. H-Coherence (Hierarchical Coherence)

Measures: Do sibling nodes have similar meanings?

```
H-Coherence = mean(cosine_sim(child_i, child_j)) for all siblings
```

Target: **≥ 0.85** (siblings should be semantically related)

### 2. H-Stability (Hierarchical Stability)

Measures: Do perturbations in depth-1 propagate consistently?

```
H-Stability = 1 - mean(path_divergence) across random permutations
```

Target: **≥ 0.80** (small input changes → small tree changes)

## Inference Example (Python)

```python
from atlas.api.app import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Encode
r = client.post("/encode_h", json={
    "text": "Кот быстро прыгает",
    "max_depth": 2
})
tree = r.json()["tree"]

# Decode
r = client.post("/decode_h", json={"tree": tree, "top_k": 5})
print(r.json()["text"])
print(r.json()["reasoning"])
```

## cURL Examples

### Encode
```bash
curl -X POST http://localhost:8000/encode_h \
  -H "Content-Type: application/json" \
  -d '{"text":"Собака","max_depth":1}'
```

### Decode
```bash
curl -X POST http://localhost:8000/decode_h \
  -H "Content-Type: application/json" \
  -d '{
    "tree": {
      "value": [0.3, 0.8, -0.2, 0.5, 0.9],
      "label": "coarse",
      "key": "root",
      "children": [],
      "confidence": 0.98
    },
    "top_k": 3
  }'
```

## CLI Usage

```bash
# Encode with explanation
atlas encode "Собака" --max-depth 2 --explain

# Decode from vector
atlas decode 0.3 0.8 -0.2 0.5 0.9 --reasoning

# Manipulate
atlas manipulate "Собака" --dimension 2 --target -0.8
```
