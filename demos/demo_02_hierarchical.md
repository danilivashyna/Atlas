# Demo 2: Hierarchical Semantic Space (v0.2)

This demo showcases the new hierarchical features in Atlas v0.2.
Run this as a Python script: `python demos/demo_02_hierarchical.py`

## What is Hierarchical Encoding?

In v0.2, Atlas introduces a "matryoshka" structure where each dimension can recursively
expand into sub-dimensions. Think of it as a tree where:

- **Root**: Overall 5D semantic representation
- **Branches**: Sub-dimensions that capture finer semantic nuances
- **Leaves**: Specific semantic features at the deepest level

## Setup

```python
from atlas.hierarchical import HierarchicalEncoder, HierarchicalDecoder
import json

# Initialize hierarchical components
encoder = HierarchicalEncoder()
decoder = HierarchicalDecoder()
```

## Example 1: Basic Hierarchical Encoding

```python
# Encode text into hierarchical tree
text = "Любовь"
tree = encoder.encode_hierarchical(
    text,
    max_depth=2,           # How deep to expand
    expand_threshold=0.2   # Minimum weight to expand
)

# Print tree structure
def print_tree(node, indent=0):
    prefix = "  " * indent
    print(f"{prefix}[{node.key}] {node.label} (w={node.weight:.2f})")
    print(f"{prefix}  value: {node.value}")
    for child in node.children or []:
        print_tree(child, indent + 1)

print_tree(tree)
```

Expected output:
```
[root] love (w=1.00)
  value: [0.15, 0.92, 0.35, -0.10, 0.68]
  [dim2] positive-affective (w=0.92)
    value: [0.18, 0.95, 0.28, -0.05, 0.72]
    [dim2.4] warmth (w=0.78)
      value: [0.22, 0.98, 0.20, 0.00, 0.80]
  [dim5] organic (w=0.68)
    value: [0.12, 0.85, 0.40, -0.15, 0.95]
```

## Example 2: Hierarchical Decoding with Reasoning

```python
# Decode with path-based reasoning
result = decoder.decode_hierarchical(tree, top_k=3, with_reasoning=True)

print(f"Decoded text: {result['text']}")
print("\nPath reasoning:")
for r in result['reasoning']:
    print(f"  {r.path}: {r.label} (weight={r.weight:.2f})")
    if r.evidence:
        print(f"    Evidence: {', '.join(r.evidence)}")
```

Expected output:
```
Decoded text: Любовь

Path reasoning:
  root: love (weight=1.00)
    Evidence: positive, affective, organic
  dim2: positive-affective (weight=0.92)
    Evidence: high dim2 value, emotional context
  dim2.4: warmth (weight=0.78)
    Evidence: specific emotional nuance
```

## Example 3: Surgical Path Manipulation

```python
# Modify a specific semantic branch
text = "Собака"
tree = encoder.encode_hierarchical(text, max_depth=2)

# Original decoding
original = decoder.decode_hierarchical(tree, top_k=3)
print(f"Original: {original['text']}")

# Modify specific path to add emotional nuance
modified_tree = decoder.manipulate_path(
    tree,
    path="dim2/dim2.4",  # Target specific emotional branch
    new_value=[0.9, 0.1, -0.2, 0.0, 0.0]  # Inject positive emotion
)

# Decode modified tree
modified = decoder.decode_hierarchical(modified_tree, top_k=3)
print(f"Modified: {modified['text']}")
```

Expected output:
```
Original: Собака
Modified: Счастливая собака
```

## Example 4: Multi-Path Manipulation

```python
# Apply multiple edits at different paths
text = "Дом"
tree = encoder.encode_hierarchical(text, max_depth=2)

# Edit multiple branches
edits = [
    ("dim2/dim2.4", [0.9, 0.1, -0.2, 0.0, 0.0]),  # Add warmth
    ("dim3", [-0.8, 0.0, 0.0, 0.0, 0.0]),         # Make more abstract
]

modified_tree = tree
for path, value in edits:
    modified_tree = decoder.manipulate_path(modified_tree, path, value)

result = decoder.decode_hierarchical(modified_tree)
print(f"Original: Дом")
print(f"Multi-edited: {result['text']}")
```

Expected output:
```
Original: Дом
Multi-edited: Родной очаг
```

## Example 5: Comparing Flat vs Hierarchical

```python
from atlas import SemanticSpace

space = SemanticSpace()
text = "Любовь"

# Flat encoding (v0.1 style)
flat_vector = space.encode(text)
flat_decoded = space.decode(flat_vector)

# Hierarchical encoding (v0.2 style)
hier_tree = encoder.encode_hierarchical(text, max_depth=2)
hier_decoded = decoder.decode_hierarchical(hier_tree)

print("=== FLAT (v0.1) ===")
print(f"Vector: {flat_vector}")
print(f"Decoded: {flat_decoded}")

print("\n=== HIERARCHICAL (v0.2) ===")
print(f"Tree nodes: {len(list(_traverse_tree(hier_tree)))}")
print(f"Decoded: {hier_decoded['text']}")
print(f"Reasoning paths: {len(hier_decoded.get('reasoning', []))}")

def _traverse_tree(node):
    yield node
    for child in node.children or []:
        yield from _traverse_tree(child)
```

Expected output:
```
=== FLAT (v0.1) ===
Vector: [0.15, 0.92, 0.35, -0.10, 0.68]
Decoded: Любовь

=== HIERARCHICAL (v0.2) ===
Tree nodes: 5
Decoded: Любовь
Reasoning paths: 3
```

## Example 6: Save and Load Trees

```python
# Save hierarchical tree to JSON
tree = encoder.encode_hierarchical("Радость", max_depth=2)

with open("tree_radost.json", "w", encoding="utf-8") as f:
    json.dump(tree.model_dump(), f, indent=2, ensure_ascii=False)

# Load and decode later
with open("tree_radost.json", "r", encoding="utf-8") as f:
    from atlas.hierarchical import TreeNode
    loaded_tree = TreeNode(**json.load(f))

result = decoder.decode_hierarchical(loaded_tree)
print(f"Loaded and decoded: {result['text']}")
```

Expected output:
```
Loaded and decoded: Радость
```

## Use Cases for Hierarchical Space

### 1. Fine-grained Emotional Control

```python
# Target specific emotional nuances
tree = encoder.encode_hierarchical("Любовь", max_depth=3)
# Modify dim2/dim2.4/dim2.4.3 for very specific emotion
```

### 2. Compositional Semantics

```python
# Build meaning hierarchically
tree = encoder.encode_hierarchical("Красивый дом", max_depth=2)
# Each word contributes to different branches
```

### 3. Semantic Debugging

```python
# Understand why decoder chose specific meaning
result = decoder.decode_hierarchical(tree, with_reasoning=True)
for r in result['reasoning']:
    print(f"Path {r.path}: contributed {r.weight:.2%}")
```

### 4. Controlled Generation

```python
# Surgical edits at specific semantic levels
# Layer 0: Overall meaning
# Layer 1: Broad semantic features
# Layer 2: Fine-grained nuances
```

## Running the Demo

Save the complete code as `demos/demo_02_hierarchical.py` and run:

```bash
python demos/demo_02_hierarchical.py
```

Or run via CLI:

```bash
# Encode hierarchically
atlas encode-h "Любовь" --max-depth 2 --expand-threshold 0.2

# Manipulate by path
atlas manipulate-h "Собака" --edit dim2/dim2.4=0.9,0.1,-0.2,0.0,0.0 --reasoning
```

## Key Advantages of Hierarchical Space

1. **Finer Control**: Edit specific semantic branches without affecting others
2. **Interpretability**: See which paths contribute to final meaning
3. **Compositionality**: Build complex meanings from simpler components
4. **Efficiency**: Lazy expansion - only compute branches that matter
5. **Debugging**: Trace exactly why decoder chose specific interpretation

## Tree Structure Visualization

```
Root (overall meaning)
├── dim0 (phrase structure)
│   ├── dim0.0 (noun-like)
│   ├── dim0.1 (verb-like)
│   └── ...
├── dim1 (emotional tone)
│   ├── dim1.0 (very negative)
│   ├── dim1.4 (very positive)
│   └── ...
├── dim2 (abstractness)
├── dim3 (perspective)
└── dim4 (entity nature)
```

Each path from root to leaf represents a specific semantic hypothesis.
The decoder combines multiple paths weighted by importance.

## Next Steps

- Experiment with different `max_depth` values (0-5)
- Try varying `expand_threshold` (0.0-1.0)
- Explore path manipulation for creative text generation
- Compare flat vs hierarchical for your use case

**Hierarchical space** unlocks surgical control over meaning! 🗺️🌳✨
