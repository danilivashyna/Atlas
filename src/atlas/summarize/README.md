# Atlas Proportional Summarization

Length-controlled summarization that preserves 5D semantic ratios of the source text.

## Overview

This module implements a novel summarization algorithm that maintains the semantic distribution of the source text while compressing or expanding to a target length. The algorithm uses KL-divergence to measure and control how well the semantic proportions are preserved.

## Features

- **Length Control**: Precisely control output length via `target_tokens` parameter
- **Semantic Preservation**: Maintains 5D semantic distribution with KL-divergence ≤ ε
- **Dual Modes**: 
  - `compress`: Reduce text while preserving meaning
  - `expand`: Elaborate on content to reach target length
- **Graceful Degradation**: Falls back to simple methods if evidence extraction fails
- **Order Preservation**: Optional macro-order preservation of ideas
- **Anti-Repeat**: Automatic deduplication to avoid redundant content

## Algorithm

The proportional summarization algorithm works as follows:

1. **Encode**: Convert source text to 5D semantic vector
2. **Normalize**: Transform vector to probability distribution p (using softmax or abs-norm)
3. **Evidence Collection**: Extract candidate text pieces for each dimension with relevance weights
4. **Quota Calculation**: Compute token allocation per dimension: `t_i = round(L' * p_i)`
5. **Greedy Filling**: Select pieces round-robin across dimensions, respecting quotas
6. **KL Verification**: Check `D_KL(p||p') ≤ ε` and adjust if needed
7. **Merge**: Combine selected pieces into final summary

## Usage

### Python API

```python
from atlas.summarize import summarize

result = summarize(
    text="Your long text here...",
    target_tokens=120,
    mode="compress",
    epsilon=0.05,
    preserve_order=True
)

print(result["summary"])
print(f"KL divergence: {result['kl_div']}")
```

### REST API

```bash
curl -X POST http://localhost:8000/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your text here...",
    "target_tokens": 120,
    "mode": "compress",
    "epsilon": 0.05,
    "preserve_order": true
  }'
```

## Parameters

- **text** (str): Source text to summarize
- **target_tokens** (int): Target length in tokens (10-5000)
- **mode** (str): Either "compress" or "expand"
- **epsilon** (float): KL-divergence tolerance (0.0-1.0, default: 0.05)
  - Lower values = stricter semantic preservation
  - Higher values = more flexibility in output
- **preserve_order** (bool): Maintain macro order of ideas (default: true)

## Response Format

```json
{
  "summary": "Generated summary text...",
  "length": 118,
  "ratio_target": [0.28, 0.07, 0.35, 0.10, 0.20],
  "ratio_actual": [0.27, 0.08, 0.34, 0.11, 0.20],
  "kl_div": 0.012,
  "trace_id": "req_xyz123"
}
```

## Feature Flag

The summarization feature can be controlled via environment variable:

```bash
export ATLAS_SUMMARY_MODE=proportional  # Enable (default)
export ATLAS_SUMMARY_MODE=off           # Disable endpoint
```

## Implementation Details

### Modules

- **proportional.py**: Core algorithm implementation
  - Distribution normalization (softmax/abs-norm)
  - KL-divergence computation
  - Evidence collection and quota calculation
  - Greedy filling with adjustments

- **selectors.py**: Evidence extraction utilities
  - Sentence and n-gram extraction
  - Keyword identification with stopword filtering
  - Duplicate detection (Jaccard similarity)
  - Token estimation and text truncation

### Normalization Methods

1. **Softmax**: `p_i = exp(v_i) / Σ exp(v_j)`
   - Handles negative values well
   - Creates smooth distributions

2. **Absolute Norm**: `p_i = |v_i| / Σ |v_j|`
   - Simpler, more interpretable
   - Preserves relative magnitudes

### Evidence Selection

Evidence pieces are scored based on:
- Dimension weight from source vector
- Keyword overlap
- Position in text
- Uniqueness (anti-duplicate)

Pieces are selected greedily to fill token quotas while avoiding repeats.

### KL-Divergence Adjustment

If `D_KL(p||p') > ε`, the algorithm performs local adjustments:
- Identifies dimensions with largest error
- Swaps pieces to improve distribution match
- Re-evaluates up to max_iterations times

## Limitations

- **Language Support**: Primarily EN/RU (basic tokenization)
- **Token Estimation**: Approximate (words × 1.3 factor)
- **No External Knowledge**: Works only with source text content
- **Deterministic**: Same input produces same output

## Examples

See `examples/summarize_example.py` for complete usage examples.

## Testing

```bash
pytest tests/test_summarize.py -v
```

## References

- KL-divergence: Kullback-Leibler divergence for distribution comparison
- Softmax normalization: Standard probability distribution transform
- Jaccard similarity: Set-based text similarity metric
