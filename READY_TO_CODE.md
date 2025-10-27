# Atlas β — Ready to Code

**Status:** ✅ All preparation complete. E1 implementation can begin immediately.

**Date:** 27.10.2025  
**Branch:** `feature/E1-1-pydantic-schemas`  
**Target:** `main` (via 0.2.0-release)

---

## 🚀 Quick Start (5 minutes)

### 1. Validate environment
```bash
make validate --strict  # All configs 🟢
make smoke              # All wiring tests 🟢
pytest tests/           # All unit tests 🟢
```

### 2. Read the four critical docs (in order)
```bash
1. docs/TZ_ATLAS_BETA.md               # ⚠️ SCOPE CLARIFICATION at top
2. docs/SAFETY_BOUNDARIES.md           # ⚠️ SYSTEM CLASSIFICATION at top
3. docs/E1_E3_ROADMAP.md               # Detailed implementation plan
4. docs/PR_SCOPE_CHECKLIST.md          # PRE-PR validation checklist
```

### 3. Start E1.1 (Pydantic schemas)
```bash
python scripts/pr_guard.py --check-scope   # 0 violations
# → Implement `src/atlas/api/schemas.py` (150-200 lines)
# → Follow code examples in docs/E1_E3_ROADMAP.md
python scripts/pr_guard.py                  # Full validation
# → Create PR with PR_SCOPE_CHECKLIST.md template
```

---

## 📋 Pre-Implementation Checklist

- [ ] **Scope Locked:** Understand "Memory engine ONLY, not AGI"
  - Read: `docs/TZ_ATLAS_BETA.md` — ⚠️ Scope Clarification block
  - Understand: NO consciousness, NO HSI, NO attention policies

- [ ] **Safety Boundaries Understood:**
  - Read: `docs/SAFETY_BOUNDARIES.md` — ⚠️ System Classification
  - Know: What IS implemented (encoding, search, metrics, routing)
  - Know: What IS NOT (consciousness, HSI, agents, online learning)

- [ ] **Determinism Commitment:**
  - Same input → Same output (reproducible)
  - `python scripts/pr_guard.py` runs clean
  - All seeds are fixed (if randomness needed)

- [ ] **Configuration Understanding:**
  - All parameters in `src/atlas/configs/` (routes.yaml, *.yaml, schemas.json)
  - No hardcoded values in code
  - ConfigLoader is single source of truth

- [ ] **Tools Ready:**
  ```bash
  make validate --strict      # Config validation
  make smoke                  # Integration tests (RRF determinism)
  pytest tests/               # Unit tests
  python scripts/pr_guard.py  # Scope + determinism check
  ```

---

## 🎯 E1 Implementation Phases

### Phase 1: E1.1-E1.4 (API Foundation)
**Est. 30-40 hours, 4 PRs**

#### E1.1: Pydantic Schemas (150-200 lines)
- `src/atlas/api/schemas.py`
- 8 request/response classes
- Full code example in E1_E3_ROADMAP.md
- PR: `feature/E1-1-pydantic-schemas` (ALREADY CREATED)

#### E1.2: FastAPI Routes (200-300 lines)
- `src/atlas/api/routes.py`
- Routes from `configs/api/routes.yaml`
- Depends on E1.1

#### E1.3: FAB Router (150-200 lines)
- `src/atlas/fab/router.py`
- `src/atlas/fab/clients.py`
- RRF deterministic fusion
- Depends on E1.1

#### E1.4: ConfigLoader Integration (50-100 lines)
- Update E1.2 to use ConfigLoader
- Validation at startup
- Depends on E1.3

### Phase 2: E1.5-E1.9 (Endpoint Implementation)
**Est. 60-80 hours, 5 PRs**

#### E1.5-E1.9: Individual Endpoints
- `/encode`, `/encode_h`, `/decode_h`, `/manipulate_h`, `/search`
- `/health`, `/ready`, `/metrics`
- Full specs in docs/E1_E3_ROADMAP.md

### Phase 3: E2-E3 (Indices & Metrics)
**Est. 50-60 hours, 3 PRs**

#### E2.1: Index Builders
- `tools/index_builders.py`
- HNSW and FAISS index creation

#### E2.2: MANIFEST Generator
- `tools/make_manifest.py`
- SHA256 checksums, versioning

#### E3.1-E3.2: H-Coherence & H-Stability Metrics
- Metrics computation and validation
- Acceptance thresholds from `configs/metrics/h_metrics.yaml`

---

## 📊 Configuration Inventory

**All parameters read from configs** (never hardcoded):

### API Contracts
- `src/atlas/configs/api/routes.yaml` — 8 endpoints (path, method, description)
- `src/atlas/configs/api/schemas.json` — Pydantic validators

### Index Parameters
- `src/atlas/configs/indices/sent_hnsw.yaml` — M=32, ef_construction=200, ef_search=64
- `src/atlas/configs/indices/para_hnsw.yaml` — M=48, ef_construction=400, ef_search=96
- `src/atlas/configs/indices/doc_faiss.yaml` — FAISS IVF-PQ parameters
- `src/atlas/configs/indices/manifest_schema.json` — MANIFEST validation

### Metrics & Quality
- `src/atlas/configs/metrics/h_metrics.yaml` — H-Coherence≥0.78, H-Stability<0.08, latency p50≤60ms

### ConfigLoader
- `src/atlas/configs/__init__.py` — Read-only access to all configs
- Convenience methods: `get_api_routes()`, `get_index_config()`, `get_metrics_config()`

---

## 🛡️ Critical Scope Boundaries

### ✅ ALLOWED (Do This)
- Deterministic encoding (token/sent/para/doc → embeddings)
- Deterministic search (RRF or max_sim fusion)
- Configuration-driven parameters (routes.yaml, h_metrics.yaml)
- Deterministic metrics (H-Coherence, H-Stability, Recall@k)
- Stateless FAB routing (query → results, no history)
- MANIFEST versioning (SHA256 checksums)

### ❌ NOT ALLOWED (Don't Do This)
- Consciousness, awareness, observer concepts
- Self-improvement or self-modification
- Attention policies (weighting by "importance")
- Online learning or feedback loops
- Hidden state in FAB (should be stateless)
- Auto-reconfiguration (parameters change manually)
- HSI boundaries or crossing (explicitly OUT OF SCOPE)
- Agent autonomy or goal-seeking behavior

**Red flags:** If you catch yourself saying "the system learns" or "improves itself", STOP. This is out of scope.

---

## 🔧 Daily Commands

### Before starting work
```bash
git pull origin main
git checkout -b feature/E1-X-description
```

### While coding
```bash
make validate --strict  # Validate configs after any change
make smoke              # Test wiring determinism
pytest tests/           # Run unit tests
python scripts/pr_guard.py  # Check scope & determinism
```

### Before submitting PR
```bash
# 1. Run full validation
python scripts/pr_guard.py

# 2. Check commit message is clear and factual
git log --oneline -3

# 3. Fill out PR_SCOPE_CHECKLIST.md template
# (See docs/PR_SCOPE_CHECKLIST.md)

# 4. Push and create PR
git push origin feature/E1-X-description

# 5. Reference in PR description:
#    - "Follows PR_SCOPE_CHECKLIST.md"
#    - "Scope validated per TZ_ATLAS_BETA.md"
#    - "Acceptance criteria from E1_E3_ROADMAP.md"
```

### After PR merges
```bash
git checkout main
git pull origin main
Update docs/ATLAS_BETA_DEVELOPMENT_STATUS.md
```

---

## 📁 File Structure Reference

```
src/atlas/
├── configs/                         # Single source of truth
│   ├── api/
│   │   ├── routes.yaml             # 8 endpoints
│   │   └── schemas.json            # Pydantic validators
│   ├── indices/
│   │   ├── sent_hnsw.yaml
│   │   ├── para_hnsw.yaml
│   │   ├── doc_faiss.yaml
│   │   └── manifest_schema.json
│   ├── metrics/
│   │   └── h_metrics.yaml
│   └── __init__.py                 # ConfigLoader class
├── api/
│   ├── app.py                      # FastAPI app
│   ├── schemas.py                  # Pydantic models (E1.1)
│   ├── routes.py                   # Endpoints (E1.2)
│   └── routes/
│       ├── encode.py
│       ├── encode_h.py
│       ├── decode_h.py
│       ├── manipulate_h.py
│       ├── search.py
│       └── health.py
├── fab/
│   ├── router.py                   # RRF fusion (E1.3)
│   ├── clients.py                  # Index clients (E1.3)
│   └── merger.py                   # Result merging
├── metrics/
│   ├── h_memory.py                 # H-Coherence, H-Stability
│   └── compute.py
└── ...

docs/
├── TZ_ATLAS_BETA.md                # ⚠️ SCOPE CLARIFICATION
├── SAFETY_BOUNDARIES.md            # ⚠️ SYSTEM CLASSIFICATION
├── E1_E3_ROADMAP.md                # Detailed plan + code examples
├── PR_SCOPE_CHECKLIST.md           # Pre-PR validation template
├── ARCHITECTURE.md                 # 6 linkages
└── WIRING_DIAGRAM.md               # 3 data flows

scripts/
├── pr_guard.py                     # Automated scope validator
├── validate_baseline.py            # Config validator
├── smoke_test_wiring.py            # Integration tests
└── db/
    └── migrate.py

tests/
├── test_api_schemas.py             # E1.1 tests
├── test_api.py                     # E1.2-E1.4 tests
├── test_fab_router.py              # E1.3 tests
└── ...
```

---

## 🧪 Testing Philosophy

**All new code must be reproducible.**

- **Determinism:** Same input → Same output (verified by `pr_guard.py`)
- **Testability:** Pure functions, no side effects
- **Validation:** `make validate` + `make smoke` must pass
- **Safety:** `pr_guard.py` checks for scope violations

### Example test structure:
```python
def test_encode_request_validates():
    """EncodeRequest schema validates correctly."""
    req = EncodeRequest(text="hello", dimension=384)
    assert req.text == "hello"
    assert req.dimension == 384

def test_encode_request_rejects_invalid_dimension():
    """EncodeRequest rejects invalid dimensions."""
    with pytest.raises(ValidationError):
        EncodeRequest(text="hello", dimension=256)  # Only 384 allowed
```

---

## 💾 Git Workflow

### Branch naming
- Feature: `feature/E1-1-pydantic-schemas`
- Fix: `fix/E1-2-route-validation`
- Docs: `docs/add-pr-checklist`

### Commit messages (clear, factual)
```
feat(api): Add Pydantic schemas from configs/api/schemas.json

- Add EncodeRequest, EncodeResponse classes
- Add SearchRequest, SearchResponse classes
- Validation against configs/api/schemas.json
- All imports work per acceptance criteria

Fixes #123
```

### PR size limit
- Max 200-400 lines per PR
- Smaller PRs = faster review = faster merge

### Branch protection
- `main`: CI must pass (validate + smoke + tests)
- Auto-delete head branches after merge
- Require PR review before merge (1 reviewer)

---

## 📞 Questions?

**If you're unsure about scope:** Check `docs/TZ_ATLAS_BETA.md` ⚠️ Scope Clarification block.

**If you're unsure about safety:** Check `docs/SAFETY_BOUNDARIES.md` ⚠️ System Classification block.

**If you're unsure about implementation:** Check `docs/E1_E3_ROADMAP.md` — has full code examples.

**If you're unsure about your code:** Run `python scripts/pr_guard.py` — should be 🟢 ALL CHECKS PASSED.

---

## 🎉 You're Ready!

Everything is prepared. Architecture is locked. Configuration is set. Scope is crystal clear.

**Next step:** Implement E1.1 (Pydantic schemas).

**Your command:**
```bash
python scripts/pr_guard.py --check-scope  # Verify clean state
# → Edit src/atlas/api/schemas.py
python scripts/pr_guard.py                 # Full validation
# → Create PR with docs/PR_SCOPE_CHECKLIST.md template
```

**Time estimate:** E1.1 should take 3-4 hours of focused coding.

**Status:** 🟢 ALL SYSTEMS GO

---

**Last updated:** 27.10.2025  
**Branch:** `feature/E1-1-pydantic-schemas`  
**Commits since prep started:** 12 (3 scope-lock + 9 infrastructure)

