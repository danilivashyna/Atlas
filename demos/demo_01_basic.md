# Demo 1: Basic Atlas Usage

This demo shows basic usage of Atlas v0.2 semantic space without heavy dependencies.
Run this as a Python script: `python demos/demo_01_basic.py`

## Setup

```python
from atlas import SemanticSpace
from atlas.dimensions import DimensionMapper

# Initialize the semantic space
space = SemanticSpace()
mapper = DimensionMapper()
```

## Example 1: Encode and Decode

```python
# Encode a text to 5D vector
text = "Собака"
vector = space.encode(text)

print(f"Original text: {text}")
print(f"5D Vector: {vector}")
print()

# Decode back to text
decoded = space.decode(vector, with_reasoning=True)
print("Reasoning:")
print(decoded['reasoning'])
print(f"\nDecoded text: {decoded['text']}")
```

Expected output:
```
Original text: Собака
5D Vector: [0.12 0.89 -0.45 0.18 0.82]

Reasoning:
Я чувствую, что:
dim₁ = 0.12 → слегка action (Структура фразы)
dim₂ = 0.89 → сильно positive (Эмоциональный тон)
dim₃ = -0.45 → умеренно concrete (Уровень обобщения)
dim₄ = 0.18 → слегка world (Точка наблюдения)
dim₅ = 0.82 → сильно living (Сущностная природа)
→ итог: "Собака"

Decoded text: Собака
```

## Example 2: Dimension Manipulation

```python
# Change emotional tone from positive to negative
result = space.manipulate_dimension(
    "Радость",
    dimension=1,  # Emotional tone: Positive ↔ Negative
    new_value=-0.9
)

print("=== ORIGINAL ===")
print(f"Text: {result['original']['text']}")
print(f"Decoded: {result['original']['decoded']['text']}")
print()

print("=== MODIFIED ===")
print(f"Changed dimension: {result['modified']['dimension_changed']}")
print(f"New value: {result['modified']['new_value']}")
print(f"Decoded: {result['modified']['decoded']['text']}")
```

Expected output:
```
=== ORIGINAL ===
Text: Радость
Decoded: Радость

=== MODIFIED ===
Changed dimension: dim₁ (Позитив ↔ Негатив)
New value: -0.9
Decoded: Грусть
```

## Example 3: Semantic Interpolation

```python
# Interpolate between two concepts
results = space.interpolate("Любовь", "Страх", steps=5)

print("Semantic transition from 'Любовь' to 'Страх':")
for r in results:
    print(f"Step {r['step']} (α={r['alpha']:.2f}): {r['decoded']['text']}")
```

Expected output:
```
Semantic transition from 'Любовь' to 'Страх':
Step 0 (α=0.00): Любовь
Step 1 (α=0.25): Волнение
Step 2 (α=0.50): Тревога
Step 3 (α=0.75): Беспокойство
Step 4 (α=1.00): Страх
```

## Example 4: Dimension Exploration

```python
# Explore how abstractness affects meaning
import numpy as np

results = space.explore_dimension(
    "Жизнь",
    dimension=2,  # Abstract ↔ Concrete
    range_vals=np.linspace(-1, 1, 5)
)

print("Exploring 'Жизнь' along Abstract ↔ Concrete axis:")
for r in results:
    print(f"Value {r['value']:+.2f}: {r['decoded']['text']}")
```

Expected output:
```
Exploring 'Жизнь' along Abstract ↔ Concrete axis:
Value -1.00: Философия
Value -0.50: Мысль
Value +0.00: Существование
Value +0.50: Быт
Value +1.00: Тело
```

## Example 5: Dimension Information

```python
# Get information about all dimensions
info = space.get_dimension_info()

print("Atlas 5D Semantic Space:")
print()
for dim_key, dim_info in info.items():
    print(f"{dim_key.upper()}: {dim_info['name']}")
    print(f"  {dim_info['poles'][0]} ↔ {dim_info['poles'][1]}")
    print(f"  {dim_info['description']}")
    print()
```

Expected output:
```
Atlas 5D Semantic Space:

DIM0: Phrase Structure
  Object ↔ Action
  Subject vs Verb orientation

DIM1: Emotional Tone
  Positive ↔ Negative
  Affective valence

DIM2: Abstraction Level
  Abstract ↔ Concrete
  Conceptual vs Physical

DIM3: Perspective
  Self ↔ World
  Observer position

DIM4: Entity Nature
  Living ↔ Mechanical
  Organic vs Artificial
```

## Running the Demo

Save this as `demos/demo_01_basic.py` and run:

```bash
python demos/demo_01_basic.py
```

Or run interactively in Python REPL:

```bash
python
>>> from atlas import SemanticSpace
>>> space = SemanticSpace()
>>> vector = space.encode("Собака")
>>> print(vector)
```

## Key Takeaways

1. **Encode**: Text → 5D vector representation
2. **Decode**: Vector → Text with interpretable reasoning
3. **Manipulate**: Change specific dimensions to transform meaning
4. **Interpolate**: Smooth transitions between concepts
5. **Explore**: Understand how dimensions affect semantics

No heavy dependencies needed - just numpy and the Atlas core!
