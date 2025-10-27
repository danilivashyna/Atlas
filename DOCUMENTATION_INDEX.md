# Atlas β Documentation Index

**Last updated:** 27.10.2025  
**Status:** 🟢 Ready for E1 implementation  
**Scope:** Memory engine (NOT AGI)

---

## 📚 Navigation Guide

### For New Developers (Start Here)

1. **[READY_TO_CODE.md](READY_TO_CODE.md)** ⭐ START HERE
   - Everything needed to begin E1 implementation
   - Quick reference guide (15 minutes to read)
   - Pre-implementation checklist
   - Daily commands
   - File structure reference

2. **[docs/TZ_ATLAS_BETA.md](docs/TZ_ATLAS_BETA.md)** — Full Specification
   - ⚠️ **Scope Clarification block** (at top of file) — CRITICAL
   - Complete technical specification for β release
   - API endpoints, config parameters, acceptance criteria
   - 43 tasks mapped to 7 epics

### For Code Review & Safety

3. **[docs/SAFETY_BOUNDARIES.md](docs/SAFETY_BOUNDARIES.md)** — Safety Enforcement
   - ⚠️ **System Classification block** (below title) — CRITICAL
   - HSI boundaries and 5 safeguards
   - What IS implemented vs what IS NOT
   - Pre-deployment checklist

4. **[docs/PR_SCOPE_CHECKLIST.md](docs/PR_SCOPE_CHECKLIST.md)** — PR Validation
   - Pre-submission checklist for every PR
   - Common mistakes to avoid (attention policies, online learning, hidden state)
   - Determinism verification
   - Red flags for reviewers
   - PR template with acceptance criteria

### For Implementation

5. **[docs/E1_E3_ROADMAP.md](docs/E1_E3_ROADMAP.md)** — Implementation Plan
   - Detailed roadmap for E1-E3 (6-7 weeks)
   - Code examples for each epic
   - Acceptance criteria per task
   - Estimated hours per PR
   - CI/GitHub Actions template

6. **[E1_START.md](E1_START.md)** — Quick Reference
   - 8 commits summary
   - 5-step quick start for E1-E3
   - Navigation guide to all docs
   - Common commands
   - Progress tracking template

### For Architecture Understanding

7. **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — System Design
   - 6 interconnected linkages
   - How configs flow through the system
   - How FAB router works
   - How metrics are computed

8. **[docs/WIRING_DIAGRAM.md](docs/WIRING_DIAGRAM.md)** — Data Flows
   - 3 detailed flow diagrams
   - `/search` endpoint flow
   - `/encode_h` endpoint flow
   - `/encode` endpoint flow

### For Configuration Reference

9. **[src/atlas/configs/__init__.py](src/atlas/configs/__init__.py)** — ConfigLoader
   - Python class for reading all configs
   - Convenience methods (get_api_routes, get_index_config, etc.)
   - Validation helpers
   - Read-only access pattern

10. **[src/atlas/configs/](src/atlas/configs/)** — Configuration Files
    - `api/routes.yaml` — 8 API endpoints
    - `api/schemas.json` — Pydantic validators
    - `indices/sent_hnsw.yaml` — Sentence index parameters
    - `indices/para_hnsw.yaml` — Paragraph index parameters
    - `indices/doc_faiss.yaml` — Document index parameters
    - `indices/manifest_schema.json` — MANIFEST validation schema
    - `metrics/h_metrics.yaml` — H-Coherence, H-Stability thresholds

### For Development Tracking

11. **[docs/ATLAS_BETA_DEVELOPMENT_STATUS.md](docs/ATLAS_BETA_DEVELOPMENT_STATUS.md)** — Live Tracker
    - Current progress for all 43 tasks
    - Status per epic (E1-E7)
    - Links to related documentation
    - Updated after each PR merge

12. **[PREPARATION_COMPLETE.md](PREPARATION_COMPLETE.md)** — Completion Summary
    - Full summary of preparation phase
    - 19 hours of setup work documented
    - Timeline and estimates
    - What's next

### For Validation & Testing

13. **[scripts/pr_guard.py](scripts/pr_guard.py)** — Automated Validation
    - Detects scope violations (consciousness, attention, hidden state)
    - Detects non-determinism (datetime, random without seed)
    - Run before every PR: `python scripts/pr_guard.py`

14. **[scripts/validate_baseline.py](scripts/validate_baseline.py)** — Config Validator
    - Validates all config files
    - JSON schema checking
    - YAML parsing
    - Range validation

15. **[scripts/smoke_test_wiring.py](scripts/smoke_test_wiring.py)** — Integration Tests
    - Validates wiring between configs and code
    - Verifies determinism (reproducibility)
    - Tests RRF fusion logic

---

## 🎯 Quick Navigation by Role

### Developer Starting E1 Implementation
```
1. READY_TO_CODE.md (15 min)
2. docs/E1_E3_ROADMAP.md — E1.1 section (10 min)
3. docs/PR_SCOPE_CHECKLIST.md (5 min)
4. Start coding: src/atlas/api/schemas.py
```

### Code Reviewer
```
1. docs/TZ_ATLAS_BETA.md — Scope Clarification (3 min)
2. docs/SAFETY_BOUNDARIES.md — System Classification (3 min)
3. docs/PR_SCOPE_CHECKLIST.md — Red flags section (5 min)
4. Run: python scripts/pr_guard.py (2 min)
5. Review PR against acceptance criteria from E1_E3_ROADMAP.md
```

### Project Manager / Status Checker
```
1. docs/ATLAS_BETA_DEVELOPMENT_STATUS.md (5 min)
2. PREPARATION_COMPLETE.md (10 min)
3. Check git: git log --oneline feature/E1-1-pydantic-schemas (2 min)
```

### System Architect
```
1. docs/ARCHITECTURE.md (10 min)
2. docs/WIRING_DIAGRAM.md (10 min)
3. src/atlas/configs/__init__.py (5 min)
4. docs/SAFETY_BOUNDARIES.md (10 min)
```

### QA / Testing Specialist
```
1. scripts/pr_guard.py — Understand checks (5 min)
2. scripts/validate_baseline.py — Config validation (5 min)
3. scripts/smoke_test_wiring.py — Integration tests (10 min)
4. docs/PR_SCOPE_CHECKLIST.md — Determinism section (5 min)
```

---

## 📊 Document Stats

| Document | Type | Lines | Purpose |
|----------|------|-------|---------|
| READY_TO_CODE.md | Guide | 364 | Quick reference for starting |
| docs/TZ_ATLAS_BETA.md | Spec | 1650+ | Full technical specification |
| docs/SAFETY_BOUNDARIES.md | Design | 600+ | Safety enforcement rules |
| docs/E1_E3_ROADMAP.md | Plan | 1100+ | Implementation roadmap |
| docs/PR_SCOPE_CHECKLIST.md | Checklist | 400+ | PR validation template |
| E1_START.md | Reference | 226 | Quick reference |
| PREPARATION_COMPLETE.md | Summary | 322 | Completion status |
| docs/ARCHITECTURE.md | Design | 600+ | System architecture |
| docs/WIRING_DIAGRAM.md | Diagram | 400+ | Data flow diagrams |
| docs/ATLAS_BETA_DEVELOPMENT_STATUS.md | Tracker | 400+ | Live progress tracker |
| — | — | — | — |
| **TOTAL** | — | **~7000 lines** | **Comprehensive documentation** |

---

## 🔒 Critical Scope Boundaries

### Locked Statements (Do Not Change)

**In TZ_ATLAS_BETA.md (Scope Clarification block):**
> "Atlas β implements only Memory and Hierarchical Encoding subsystem"
> "Not an AGI prototype — it is a memory engine"
> "FAB acts only as stateless routing layer"
> "HSI/consciousness behaviors EXPLICITLY OUT OF SCOPE"

**In SAFETY_BOUNDARIES.md (System Classification block):**
> "IS: Deterministic encoding, search, metrics, routing, versioning"
> "IS NOT: Consciousness, HSI, attention policies, online learning, agent autonomy"

### Automated Enforcement
- `pr_guard.py` detects violations automatically
- Runs on every PR (can be run locally: `python scripts/pr_guard.py`)
- Forbidden patterns: consciousness, attention, self-improve, hidden state

---

## ✅ Validation Checklist

### Before Starting Development
- [ ] Read READY_TO_CODE.md
- [ ] Run `make validate --strict` (should pass)
- [ ] Run `make smoke` (should pass)
- [ ] Run `python scripts/pr_guard.py --check-scope` (should have 0 violations)

### Before Every Commit
- [ ] Code follows PR_SCOPE_CHECKLIST.md template
- [ ] `python scripts/pr_guard.py` passes (🟢 ALL CHECKS PASSED)
- [ ] Commit message is clear and factual (no marketing language)

### Before Submitting PR
- [ ] All tests pass (`pytest tests/`)
- [ ] References E1_E3_ROADMAP.md acceptance criteria
- [ ] Uses PR_SCOPE_CHECKLIST.md template
- [ ] References TZ_ATLAS_BETA.md scope clarification
- [ ] References SAFETY_BOUNDARIES.md system classification

### After PR Merge
- [ ] Update docs/ATLAS_BETA_DEVELOPMENT_STATUS.md
- [ ] Create next feature branch (e.g., feature/E1-2-fastapi-routes)
- [ ] Update roadmap progress

---

## 🔗 Related Commands

```bash
# Validate everything
make validate --strict && make smoke && pytest tests/

# Check for scope violations
python scripts/pr_guard.py --check-scope

# Full validation before PR
python scripts/pr_guard.py

# View all commits on feature branch
git log --oneline feature/E1-1-pydantic-schemas

# View commits since main
git log --oneline main..feature/E1-1-pydantic-schemas

# Check branch status
git branch -vv | grep E1-1
```

---

## 📞 Quick Reference

**Scope is locked in:** TZ_ATLAS_BETA.md (⚠️ Scope Clarification block at top)

**Safety is enforced by:** SAFETY_BOUNDARIES.md + pr_guard.py + PR_SCOPE_CHECKLIST.md

**Implementation is guided by:** E1_E3_ROADMAP.md + READY_TO_CODE.md

**Quality is verified by:** make validate, make smoke, pytest, pr_guard.py

---

**Version:** 1.0  
**Status:** Complete and ready for use  
**Last Updated:** 27.10.2025  
**Next Milestone:** E1 complete in 3-4 weeks

