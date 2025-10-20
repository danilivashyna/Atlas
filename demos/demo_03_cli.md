# Demo 3: CLI Command Reference

This demo shows how to use Atlas v0.2 from the command line.
All examples are runnable shell commands - no Python code needed!

## Installation Check

```bash
# Verify Atlas is installed
atlas --help

# Show dimension information
atlas info
```

## Basic Commands

### 1. Encode Text

```bash
# Simple encoding
atlas encode "Собака"

# Output:
# ============================================================
#   ENCODING RESULT
# ============================================================
# 
# Input text: "Собака"
# 
# 5D Vector: [0.12 0.89 -0.45 0.18 0.82]
```

### 2. Encode with Explanation

```bash
# Encode with dimensional interpretation
atlas encode "Любовь" --explain

# Output:
# ============================================================
#   ENCODING RESULT
# ============================================================
# 
# Input text: "Любовь"
# 
# 5D Vector: [0.15 0.92 0.35 -0.10 0.68]
# 
# Dimensional Interpretation:
# dim₁ = 0.15 → слегка action (Структура фразы)
# dim₂ = 0.92 → сильно positive (Эмоциональный тон)
# dim₃ = 0.35 → слегка abstract (Уровень обобщения)
# dim₄ = -0.10 → слегка self (Точка наблюдения)
# dim₅ = 0.68 → умеренно living (Сущностная природа)
```

### 3. Save Encoding to File

```bash
# Save vector to JSON file
atlas encode "Собака" --output dog_vector.json

# Check the file
cat dog_vector.json
# Output:
# {
#   "text": "Собака",
#   "vector": [0.12, 0.89, -0.45, 0.18, 0.82]
# }
```

### 4. Decode Vector

```bash
# Decode from vector values
atlas decode --vector 0.1 0.9 -0.5 0.2 0.8

# Output:
# ============================================================
#   DECODING RESULT
# ============================================================
# 
# 5D Vector: [0.1 0.9 -0.5 0.2 0.8]
# 
# Decoded Text: "Собака"
```

### 5. Decode with Reasoning

```bash
# Show reasoning process
atlas decode --vector 0.1 0.9 -0.5 0.2 0.8 --reasoning

# Output:
# ============================================================
#   DECODING RESULT
# ============================================================
# 
# 5D Vector: [0.1 0.9 -0.5 0.2 0.8]
# 
# Reasoning Process:
# Я чувствую, что:
# dim₁ = 0.10 → слегка action
# dim₂ = 0.90 → сильно positive
# dim₃ = -0.50 → умеренно concrete
# dim₄ = 0.20 → слегка world
# dim₅ = 0.80 → сильно living
# → итог: "Собака"
# 
# Decoded Text: "Собака"
```

### 6. Decode from File

```bash
# Decode vector saved in JSON file
atlas decode --input dog_vector.json --reasoning
```

## Semantic Manipulation

### 7. Change Dimension Value

```bash
# Transform "Радость" by making it negative
atlas manipulate "Радость" --dimension 1 --value -0.9

# Output:
# ============================================================
#   DIMENSION MANIPULATION
# ============================================================
# 
# === ORIGINAL ===
# Text: "Радость"
# Vector: [0.05, 0.95, -0.20, -0.15, 0.50]
# Decoded: "Радость"
# 
# === MODIFIED ===
# Changed: dim₁ (Позитив ↔ Негатив)
# New value: -0.9
# Vector: [0.05, -0.90, -0.20, -0.15, 0.50]
# Decoded: "Грусть"
```

### 8. Manipulate with Reasoning

```bash
# Show detailed reasoning for manipulation
atlas manipulate "Любовь" --dimension 2 --value 1.0 --reasoning
```

## Semantic Exploration

### 9. Interpolate Between Concepts

```bash
# Create semantic transition
atlas interpolate "Любовь" "Страх" --steps 5

# Output:
# ============================================================
#   SEMANTIC INTERPOLATION
# ============================================================
# 
# From: "Любовь"
# To: "Страх"
# Steps: 5
# 
# Step 0 (α=0.00):
#   Vector: ['0.15', '0.92', '0.35', '-0.10', '0.68']
#   Text: "Любовь"
# 
# Step 1 (α=0.25):
#   Vector: ['0.12', '0.65', '0.15', '0.05', '0.50']
#   Text: "Волнение"
# 
# Step 2 (α=0.50):
#   Vector: ['0.08', '0.38', '-0.05', '0.20', '0.32']
#   Text: "Тревога"
# ...
```

### 10. Explore Single Dimension

```bash
# See how abstractness affects "Жизнь"
atlas explore "Жизнь" --dimension 2 --steps 5

# Output:
# ============================================================
#   DIMENSION EXPLORATION
# ============================================================
# 
# Base text: "Жизнь"
# Exploring: dim₂ (Абстрактное ↔ Конкретное)
# 
# Value: -1.00
#   Text: "Философия"
# 
# Value: -0.50
#   Text: "Мысль"
# 
# Value: 0.00
#   Text: "Существование"
# 
# Value: 0.50
#   Text: "Быт"
# 
# Value: 1.00
#   Text: "Тело"
```

### 11. Custom Range Exploration

```bash
# Explore with custom values
atlas explore "Радость" --dimension 1 --range -1.0 -0.5 0.0 0.5 1.0
```

## Hierarchical Commands (v0.2)

### 12. Hierarchical Encoding

```bash
# Encode with tree structure
atlas encode-h "Любовь" --max-depth 2 --expand-threshold 0.2

# Output:
# ============================================================
#   HIERARCHICAL ENCODING
# ============================================================
# 
# Input text: "Любовь"
# Max depth: 2
# Expand threshold: 0.2
# 
# Hierarchical Tree:
# [root] love (w=1.00)
#   value: ['0.15', '0.92', '0.35', '-0.10', '0.68']
#   [dim2] positive-affective (w=0.92)
#     value: ['0.18', '0.95', '0.28', '-0.05', '0.72']
#     [dim2.4] warmth (w=0.78)
#       value: ['0.22', '0.98', '0.20', '0.00', '0.80']
```

### 13. Save Hierarchical Tree

```bash
# Save tree to file
atlas encode-h "Собака" --max-depth 2 --output dog_tree.json

# View the tree structure
cat dog_tree.json | jq .
```

### 14. Decode Hierarchical Tree

```bash
# Decode from tree file
atlas decode-h --input dog_tree.json --top-k 3

# Output:
# ============================================================
#   HIERARCHICAL DECODING
# ============================================================
# 
# Decoded Text: "Собака"
```

### 15. Decode with Path Reasoning

```bash
# Show which paths contributed to decoding
atlas decode-h --input dog_tree.json --top-k 3 --reasoning

# Output:
# ============================================================
#   HIERARCHICAL DECODING
# ============================================================
# 
# Path Reasoning:
#   root: dog (weight=1.00)
#     Evidence: concrete, positive, living
#   dim2: positive-entity (weight=0.85)
#     Evidence: high emotional tone
#   dim5: organic (weight=0.82)
#     Evidence: living creature
# 
# Decoded Text: "Собака"
```

### 16. Surgical Path Manipulation

```bash
# Edit specific semantic branch
atlas manipulate-h "Собака" \
  --edit dim2/dim2.4=0.9,0.1,-0.2,0.0,0.0 \
  --reasoning

# Output:
# ============================================================
#   HIERARCHICAL MANIPULATION
# ============================================================
# 
# === ORIGINAL ===
# Text: "Собака"
# Decoded: "Собака"
# 
# === MODIFIED ===
# Edits applied: 1
#   dim2/dim2.4 = ['0.90', '0.10', '-0.20', '0.00', '0.00']
# 
# Decoded: "Счастливая собака"
```

### 17. Multiple Path Edits

```bash
# Apply multiple edits at once
atlas manipulate-h "Дом" \
  --edit dim2/dim2.4=0.9,0.1,-0.2,0.0,0.0 \
  --edit dim3=-0.8,0.0,0.0,0.0,0.0 \
  --reasoning
```

## Workflows

### Workflow 1: Analyze → Modify → Compare

```bash
# 1. Analyze original
atlas encode "Собака" --explain > original.txt

# 2. Modify dimension
atlas manipulate "Собака" --dimension 1 --value -0.9 > modified.txt

# 3. Compare results
diff original.txt modified.txt
```

### Workflow 2: Encode → Save → Load → Decode

```bash
# 1. Encode and save
atlas encode "Любовь" --output love.json

# 2. Later, load and decode
atlas decode --input love.json --reasoning
```

### Workflow 3: Hierarchical Pipeline

```bash
# 1. Encode hierarchically
atlas encode-h "Радость" --max-depth 2 --output joy_tree.json

# 2. Decode with reasoning
atlas decode-h --input joy_tree.json --reasoning

# 3. Manipulate specific path
atlas manipulate-h "Радость" \
  --edit dim2/dim2.4=0.9,0.1,-0.2,0.0,0.0 \
  --reasoning
```

## Tips and Tricks

### Dimension Reference

```
--dimension 0  →  Object ↔ Action (phrase structure)
--dimension 1  →  Positive ↔ Negative (emotional tone)
--dimension 2  →  Abstract ↔ Concrete (abstraction level)
--dimension 3  →  Self ↔ World (perspective)
--dimension 4  →  Living ↔ Mechanical (entity nature)
```

### Value Ranges

- Dimension values are in range [-1.0, 1.0]
- -1.0 = extreme negative pole
- 0.0 = neutral
- 1.0 = extreme positive pole

### Hierarchical Depth

```
--max-depth 0  →  Just root (flat mode)
--max-depth 1  →  Root + 5 children (standard)
--max-depth 2  →  Root + children + grandchildren (detailed)
--max-depth 3+ →  Very fine-grained (slower)
```

### Expand Threshold

```
--expand-threshold 0.0  →  Expand all branches
--expand-threshold 0.2  →  Only important branches (default)
--expand-threshold 0.5  →  Only very important branches
```

## Shell Aliases (Optional)

Add to your `.bashrc` or `.zshrc`:

```bash
# Quick aliases
alias ae='atlas encode'
alias ad='atlas decode'
alias am='atlas manipulate'
alias ai='atlas interpolate'
alias aeh='atlas encode-h'
alias adh='atlas decode-h'
```

Then use:

```bash
ae "Собака" --explain
ad --vector 0.1 0.9 -0.5 0.2 0.8 --reasoning
```

## Debugging

```bash
# Show all available commands
atlas --help

# Show help for specific command
atlas encode --help
atlas manipulate-h --help

# Check version
atlas info
```

## Next Steps

- Try different dimension manipulations
- Experiment with hierarchical depth
- Create your own workflows
- Combine with other CLI tools (jq, grep, etc.)

The CLI makes Atlas accessible without writing any Python code! 🚀
