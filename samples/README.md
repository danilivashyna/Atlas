# Sample Files

This directory contains reference samples for testing and demonstration.

## Files

### golden_samples.json

Golden samples for regression testing. These samples define expected behavior that should remain stable across versions.

**Structure**:
- `samples`: Expected encode/decode pairs with tolerance
- `edge_cases`: Boundary conditions and error cases
- `invariants`: Properties that must always hold

**Usage**:
```python
import json
from atlas import SemanticSpace

# Load golden samples
with open('samples/golden_samples.json') as f:
    data = json.load(f)

space = SemanticSpace()

# Test a sample
sample = data['samples'][0]
vector = space.encode(sample['text'])
assert len(vector) == 5
assert all(abs(v - e) < sample['tolerance']
           for v, e in zip(vector, sample['expected_vector']))
```

### demo_texts.json (Future)

Collection of demonstration texts showing various semantic properties.

### interpretability_examples.json (Future)

Examples specifically designed to test interpretability features.

## Adding New Samples

When adding samples:

1. **Test Stability**: Verify the sample encodes/decodes consistently
2. **Document Purpose**: Add clear notes explaining why the sample is included
3. **Set Tolerance**: Choose appropriate tolerance based on expected variance
4. **Version**: Update version field when changing samples

## Validation

Run sample validation with:

```bash
pytest tests/test_golden_samples.py
```

Or directly:

```bash
python -c "
import json
from atlas import SemanticSpace

with open('samples/golden_samples.json') as f:
    data = json.load(f)

space = SemanticSpace()
for sample in data['samples']:
    vector = space.encode(sample['text'])
    print(f'✓ {sample[\"text\"]}: {vector}')
"
```
