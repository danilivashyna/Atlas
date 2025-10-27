# Atlas β — PR Scope Validation Checklist

**Purpose:** Ensure every PR stays within memory-engine scope. Use this checklist before submitting any PR.

---

## Pre-Submission Checklist

### Scope Verification
- [ ] **No consciousness/HSI concepts** in code or comments
  - ❌ Words to avoid: "aware", "conscious", "self-improving", "observing", "intention", "goal", "agent"
  - ❌ Patterns to avoid: feedback loops, learning from outcomes, hidden state, attention weighting
- [ ] **No attention policies** for request routing
  - ✅ OK: Deterministic routing by config (routes.yaml)
  - ❌ NOT OK: "Important requests get routed to X", "Popular queries cached"
- [ ] **No online learning** in the codebase
  - ✅ OK: Offline model training, then new MANIFEST
  - ❌ NOT OK: Updating weights during /encode calls, learning from user feedback
- [ ] **No hidden state in FAB**
  - ✅ OK: Stateless router → returns results
  - ❌ NOT OK: Position bias, query budget, session tracking
- [ ] **No auto-reconfig** without external review
  - ✅ OK: Change config file → git commit → review → deploy + restart
  - ❌ NOT OK: Detecting performance drop → auto-adjust parameters

### Code Quality
- [ ] `make validate --strict` passes ✅
- [ ] `make smoke` passes ✅
- [ ] All new code is deterministic (same input → same output)
- [ ] Reproducibility tests included (if applicable)
- [ ] No `random`, `datetime.now()`, or other non-deterministic calls without seed

### Documentation
- [ ] Commit message is clear and factual (no marketing language)
- [ ] Code comments explain *what* and *why*, not "*how good* this is"
- [ ] References to config files (routes.yaml, h_metrics.yaml, etc.)
- [ ] Acceptance criteria match E1_E3_ROADMAP.md expectations

### Testing
- [ ] Unit tests cover happy path and edge cases
- [ ] Integration tests verify determinism
- [ ] No tests that check for "learning" or "improvement"
- [ ] All tests have clear, verifiable assertions

---

## PR Description Template

```markdown
## Description
[Brief factual description of what this PR does]

## Type
- [ ] E1 (API)
- [ ] E2 (Indices)
- [ ] E3 (Metrics)
- [ ] E4-E7 (Other)

## Scope Validated
- [ ] No consciousness/HSI concepts
- [ ] No attention policies
- [ ] No online learning
- [ ] No hidden state in FAB
- [ ] No auto-reconfig

## Acceptance Criteria (from E1_E3_ROADMAP.md)
- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] [Criterion 3]

## CI Status
- [ ] `make validate` ✅
- [ ] `make smoke` ✅
- [ ] All tests pass ✅

## Files Changed
- `src/atlas/...`: [description]
- `tests/...`: [test descriptions]
- `docs/...`: [doc updates, if any]
```

---

## Common Mistakes (Avoid!)

### ❌ Memory Engine Violations

**Attention Policies:**
```python
# BAD: Weighting requests by importance
if request_type == "important":
    use_faster_index()
else:
    use_slower_index()
```
**GOOD:**
```python
# Use deterministic routing from config
ef_search = ConfigLoader.get_index_config("sentence")["ef_search"]
```

**Online Learning:**
```python
# BAD: Updating model based on feedback
if user_satisfaction > 0.8:
    model.weights *= 1.01  # Improve if users like it
```
**GOOD:**
```python
# Export metrics for offline analysis only
prometheus_h_coherence.set(computed_value)
# Humans decide: retrain offline, create new MANIFEST, deploy
```

**Hidden State:**
```python
# BAD: FAB maintaining query history
class FABRouter:
    def __init__(self):
        self.query_history = []  # Hidden state!
    
    def route(self, q):
        self.query_history.append(q)  # Learning from history
        return smart_route(q, self.query_history)
```
**GOOD:**
```python
# Stateless routing
def route_search(query, levels, k):
    """Pure function: query → results. No history, no side effects."""
    return {"sent": [], "para": [], "doc": []}
```

**Auto-Reconfig:**
```python
# BAD: Automatically adjusting parameters
if p50_latency > target_latency:
    current_ef_search += 10  # Self-tune
```
**GOOD:**
```python
# Record metrics, humans update config
assert p50_latency <= ConfigLoader.get_metrics_config()["latency"]["p50_ms"], \
    f"Latency {p50_latency} exceeds target. Update h_metrics.yaml and redeploy."
```

---

## Determinism Checklist

Every PR must guarantee **reproducibility**:

- [ ] All algorithms use fixed seeds (if random is needed)
- [ ] No `import time`, `datetime`, `random` without seeding
- [ ] No file I/O side effects during computation
- [ ] RRF always produces identical ranking for same inputs
- [ ] Embeddings always produce identical vectors for same text

**Test reproducibility:**
```bash
# Run the same operation twice, should get identical output
python -c "from my_module import func; print(func('test'))" > /tmp/out1.txt
python -c "from my_module import func; print(func('test'))" > /tmp/out2.txt
diff /tmp/out1.txt /tmp/out2.txt  # Should be empty (identical)
```

---

## Validation Commands

### Before submitting PR:
```bash
# 1. Validate configs
make validate --strict

# 2. Run smoke tests
make smoke

# 3. Run all tests
pytest tests/ -v

# 4. Check for forbidden patterns
grep -r "attention\|conscious\|self.improve\|observe\|online_learn" src/ --include="*.py" || echo "✅ No forbidden patterns"

# 5. Verify determinism
python scripts/smoke_test_wiring.py  # Should be identical on re-run
```

### CI will automatically check:
- `make validate --strict` (all configs)
- `make smoke` (wiring tests)
- `pytest tests/` (unit tests)
- `flake8` / `black` (code style)

---

## Examples of ✅ Good PRs

### E1.1: Pydantic Schemas
- Adds `src/atlas/api/schemas.py`
- Defines 8 request/response classes
- No logic, just type definitions
- All tests deterministic
- ✅ Passes `make validate`, `make smoke`

### E2.2: MANIFEST Generator
- Adds `tools/make_manifest.py`
- Computes SHA256 of artifacts
- Records git commit/branch
- Pure function: artifacts → manifest JSON
- ✅ Output is reproducible for same artifacts

### E3.1: H-Coherence Metric
- Adds `src/atlas/metrics/h_memory.py`
- Computes cosine similarity between embeddings
- Compares against threshold from config
- No feedback, no learning
- ✅ Same embeddings → same metric value

---

## Red Flags 🚩

If you see ANY of these in a PR, **request changes**:

- [ ] `os.environ` for runtime config (should use MANIFEST)
- [ ] `session["state"]` or similar hidden storage
- [ ] `if user_feedback > threshold: improve()`
- [ ] "smart" routing that doesn't match routes.yaml
- [ ] Caching decisions based on query patterns
- [ ] Learning loops or feedback signals
- [ ] Comments about "consciousness", "awareness", "goals"

---

## Questions to Ask Before Merging

1. **Can I trace all parameters through config files?**
   - Every parameter should come from routes.yaml, *.yaml, or MANIFEST
   - If it's hardcoded or derived from data, that's a violation

2. **Is this deterministic?**
   - Run it 10 times with same input → same output?

3. **Is there any feedback loop or learning?**
   - Does the system improve/adapt based on feedback? That's HSI.

4. **Does FAB stay stateless?**
   - FAB should not maintain history, learn patterns, or track sessions.

5. **Could a human reviewer verify this is correct?**
   - Code should be simple enough to understand in 5 minutes.
   - Complex logic should be in tests, not in production code.

---

## Scope Locked In ✨

**All PRs to Atlas β must:**
- ✅ Be memory engines (hierarchical encoding + search)
- ✅ Stay deterministic and reproducible
- ✅ Keep FAB stateless (routing + RRF fusion)
- ✅ Validate against configs (single source of truth)
- ✅ Require explicit review for any config change

**No PR should:**
- ❌ Implement consciousness, HSI, or attention policies
- ❌ Add online learning or self-modification
- ❌ Introduce hidden state or learning loops
- ❌ Auto-adjust parameters without external review
- ❌ Use terms like "aware", "conscious", "agent", "goal"

---

**Questions?** Refer to:
- `docs/TZ_ATLAS_BETA.md` — Scope definition
- `docs/SAFETY_BOUNDARIES.md` — Safety guards
- `docs/E1_E3_ROADMAP.md` — Implementation guide

