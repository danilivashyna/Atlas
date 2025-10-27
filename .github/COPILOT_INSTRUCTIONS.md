# 🚨 COPILOT: Scope Boundaries for Atlas β

**READ THIS BEFORE GENERATING ANY CODE OR SUGGESTIONS**

---

## Atlas β = Memory Engine ONLY

This codebase implements a **hierarchical semantic memory system**, NOT an AGI or consciousness prototype.

---

## ✅ What You CAN Suggest

### Memory Operations
- Encoding/decoding text to semantic vectors (5D rule-based, hierarchical multi-level)
- Storing and retrieving embeddings from indices (HNSW, FAISS)
- Multi-level search (sentence/paragraph/document) with deterministic fusion
- Memory quality metrics (H-Coherence, H-Stability)

### Infrastructure
- Pydantic schemas for API validation
- FastAPI routes for REST endpoints (`/encode`, `/search`, `/health`, etc.)
- ConfigLoader for reading YAML/JSON configs (read-only)
- Index builders that construct HNSW/FAISS indices from configs
- MANIFEST generation with SHA256 checksums
- Validation scripts (`validate_baseline.py`, `smoke_test_wiring.py`)

### FAB (Filter-and-Blend) Layer
- **Stateless** routing of queries to multiple index levels
- **Deterministic** fusion using RRF (Reciprocal Rank Fusion) or max_sim
- NO state, NO learning, NO feedback loops
- Pure functions only: same input → same output

---

## ❌ What You MUST NOT Suggest

### Consciousness / AGI Concepts
- ❌ Observer patterns, self-reflection, introspection
- ❌ Meta-cognition, theory of mind, self-awareness
- ❌ Attention mechanisms that prioritize based on "importance" or "salience"
- ❌ HSI (Human-level Self-Improvement) boundary crossing

### Learning / Adaptation
- ❌ Online learning (updating model weights at runtime)
- ❌ Self-modification without external review
- ❌ Auto-tuning of hyperparameters based on feedback
- ❌ Dynamic config changes in production

### Autonomous Behavior
- ❌ Planning systems, goal-setting, task decomposition
- ❌ Autonomous agents that make decisions
- ❌ Multi-agent coordination, swarms
- ❌ Reinforcement learning loops

### Unsafe Patterns
- ❌ Runtime config mutation (ConfigLoader is read-only)
- ❌ Non-deterministic algorithms (must be reproducible via tests)
- ❌ Hidden state in FAB (must be stateless)
- ❌ Side effects in pure functions
- ❌ Bypassing MANIFEST validation

---

## 🔐 Safety Constraints (Always Enforce)

1. **Config-Driven**: All parameters in YAML/JSON (git-tracked, reviewed)
2. **Read-Only**: ConfigLoader never mutates configs at runtime
3. **Deterministic**: RRF/max_sim are pure functions (same input → same output)
4. **Validated**: MANIFEST checks SHA256 of all models/indices
5. **Stateless FAB**: No memory, no caching, no learning inside FAB
6. **Reproducible**: `make validate` and `make smoke` must pass

---

## 📋 Current Work (E1-E3 Focus)

### E1: API & Contracts
- Pydantic schemas from `configs/api/schemas.json`
- FastAPI routes from `configs/api/routes.yaml`
- FAB router (stateless, deterministic RRF fusion)
- ConfigLoader integration

### E2: Indices & MANIFEST
- Index builders (HNSW/FAISS from configs)
- MANIFEST generator with SHA256 checksums
- Validation against `manifest_schema.json`

### E3: Memory Metrics
- H-Coherence computation (cosine similarity between levels)
- H-Stability tracking (drift detection)
- Thresholds from `h_metrics.yaml`

---

## 🎯 When Suggesting Code

**Always ask yourself:**
1. Is this a memory operation (encode/search/store)?
2. Is it deterministic and reproducible?
3. Does it stay within the memory subsystem?
4. Does it avoid consciousness/learning/agent patterns?
5. Does it respect read-only configs and stateless FAB?

**If any answer is NO → don't suggest it.**

---

## 📚 Reference Documents

- `docs/TZ_ATLAS_BETA.md` — Full scope clarification (⚠️ section)
- `docs/SAFETY_BOUNDARIES.md` — HSI boundaries + safeguards
- `docs/E1_E3_ROADMAP.md` — Implementation guide
- `E1_START.md` — Quick reference

---

## ✅ Example: Good Suggestions

```python
# ✅ Good: Deterministic RRF fusion
def fuse_rrf(buckets, k=60):
    agg = defaultdict(float)
    for hits in buckets:
        for rank, hit in enumerate(hits):
            agg[hit["id"]] += 1.0 / (rank + k)
    return sorted(agg.items(), key=lambda x: x[1], reverse=True)

# ✅ Good: Read-only config access
routes = ConfigLoader.get_api_routes()

# ✅ Good: Pydantic validation
class EncodeRequest(BaseModel):
    text: str
    metadata: Optional[dict] = None
```

---

## ❌ Example: Bad Suggestions

```python
# ❌ Bad: Online learning
def update_encoder_weights(feedback):
    model.weights += learning_rate * gradient  # NO!

# ❌ Bad: Attention policy
def prioritize_query(query, context):
    if is_important(query):  # NO!
        return high_priority_route()

# ❌ Bad: Config mutation
def tune_hyperparameters():
    ConfigLoader._cached_configs["M"] = 128  # NO!

# ❌ Bad: Non-deterministic
def fuse_random(buckets):
    return random.sample(buckets, k)  # NO!
```

---

**Remember: Atlas β is a tool (memory engine), not a mind (AGI).**

**Keep all suggestions within memory subsystem boundaries. 🧠 ➜ 💾**

