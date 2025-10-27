# Atlas β — Configuration Baseline

**Version:** 0.2.0-beta  
**Purpose:** Define architectural contracts for API, indices, and metrics  
**Status:** Locked for Sprint 0.2.0-beta development

---

## 📁 Structure

```
src/atlas/configs/
├── api/
│   ├── routes.yaml            # REST endpoint definitions & contract
│   └── schemas.json           # Pydantic/JSON Schema for Request/Response
├── indices/
│   ├── sent_hnsw.yaml         # HNSW config for sentence-level index
│   ├── para_hnsw.yaml         # HNSW config for paragraph-level index
│   ├── doc_faiss.yaml         # FAISS config for document-level index
│   └── manifest_schema.json   # MANIFEST.v0_2.json validation schema
└── metrics/
    └── h_metrics.yaml         # H-Coherence, H-Stability, IR thresholds
```

---

## 🔧 API Configurations (`configs/api/`)

### `routes.yaml`
Defines all REST endpoints for Atlas β:

**Endpoints:**
- `/encode` — Encode text → 5D vector
- `/decode` — Decode 5D → text
- `/explain` — Explain 5D dimensions
- `/encode_h` — Hierarchical encoding
- `/decode_h` — Hierarchical decoding
- `/manipulate_h` — Hierarchical operations
- `/search` — Multi-level search with FAB
- `/health` — Liveness probe
- `/ready` — Readiness probe
- `/metrics` — Prometheus metrics
- `/admin/indices/rollback` — Admin: rollback indices
- `/admin/indices/switch` — Admin: atomically switch indices

**Key Settings:**
- Default timeout: 30s
- Cache TTL per endpoint (0 for no cache)
- CORS allowed origins, rate limits, logging

### `schemas.json`
JSON Schema for all API request/response bodies:

**Coverage:**
- ✅ EncodeRequest/Response
- ✅ DecodeRequest/Response
- ✅ ExplainRequest/Response
- ✅ EncodeHierarchicalRequest/Response
- ✅ DecodeHierarchicalRequest/Response
- ✅ ManipulateHierarchicalRequest/Response
- ✅ SearchRequest/Response with per-level debug info
- ✅ HealthResponse, ReadyResponse
- ✅ ErrorResponse

**Usage in code:**
```python
from jsonschema import validate
import json

schemas = json.load(open('configs/api/schemas.json'))
encode_schema = schemas['definitions']['EncodeRequest']

# Validate request
validate(instance=request_body, schema=encode_schema)
```

---

## 📊 Index Configurations (`configs/indices/`)

### Sentence-level: `sent_hnsw.yaml`

**Index Type:** HNSW (Hierarchical Navigable Small World)

**Key Parameters:**
- **M = 32**: Moderate connectivity (balanced recall/memory)
- **ef_construction = 200**: Good quality during build
- **ef_search = 64**: Fast search, high recall
- **Vector dim:** 384
- **Metric:** cosine (L2-normalized)

**Performance Targets:**
- Latency p50: ≤ 15 ms
- Latency p95: ≤ 35 ms
- Recall@10: ≥ 0.95

### Paragraph-level: `para_hnsw.yaml`

**Index Type:** HNSW (denser variant)

**Key Differences:**
- **M = 48**: Denser graph (broader semantic context)
- **ef_construction = 400**: Higher quality for richer semantics
- **ef_search = 96**: Larger search window
- **Same vector_dim & metric**

**Performance Targets:**
- Latency p50: ≤ 25 ms
- Latency p95: ≤ 60 ms
- Recall@10: ≥ 0.93

### Document-level: `doc_faiss.yaml`

**Index Type:** FAISS IVF-PQ (Inverted File + Product Quantization)

**Key Parameters:**
- **nlist ≈ √N**: Adaptive clustering (1000 for 1M docs, 2236 for 5M)
- **nprobe = 100**: Search 100/1000 clusters (10% of nlist)
- **m = 16**: 16 subquantizers (code blocks)
- **nbits = 8**: 256 codewords per block

**Training:**
- **training_size = 100k**: Vectors to train IVF/PQ codebooks
- **batch_size = 10k**: Training batch

**Performance Targets:**
- Latency p50: ≤ 30 ms
- Latency p95: ≤ 80 ms
- Recall@10: ≥ 0.90

### MANIFEST Schema: `manifest_schema.json`

Validates `MANIFEST.v0_2.json` structure:

```json
{
  "version": "0.2",
  "api_version": "beta",
  "git": { "head": "...", "branch": "main" },
  "models": [
    {
      "name": "encoder_base",
      "file": "models/encoder_base.mxfp16",
      "format": "mxfp16",
      "sha256": "...",
      "type": "teacher"
    }
  ],
  "indices": [
    {
      "level": "sentence",
      "file": "indexes/sent.hnsw",
      "index_type": "HNSW",
      "vector_dim": 384,
      "sha256": "...",
      "num_vectors": 1000000,
      "hparams": { "M": 32, "efC": 200, "efSearch": 64 }
    }
  ],
  "metadata": { "created_at": "..." },
  "compatibility": { "api_version": "beta", "vector_dim": 384 }
}
```

**Validation checks:**
- ✅ SHA256 checksums match files
- ✅ vector_dim compatibility (384 or 768)
- ✅ Git commit is valid
- ✅ All required files present

---

## 📈 Metrics Configuration (`configs/metrics/h_metrics.yaml`)

### H-Coherence
**Definition:** Average cosine similarity between adjacent hierarchical levels

**Targets:**
- Sentence → Paragraph: ≥ 0.78
- Paragraph → Document: ≥ 0.80

**Test set:** 1000 doc samples  
**Frequency:** Hourly measurement

```python
coherence = mean([cos(sent_vec_i, para_vec_i) for all i])
```

### H-Stability
**Definition:** Robustness under perturbations (typos, punctuation, case)

**Max acceptable drift:** ≤ 0.08  
(Means: cos_sim(original, perturbed) ≥ 0.92)

**Perturbation types:**
- Punctuation removal/addition
- Case changes
- Tokenization (it's vs it is)
- Character-level noise (5%)
- Whitespace normalization

**Test set:** 500 examples  
**Frequency:** Daily measurement

### IR Metrics
**Recall@k:** Fraction of relevant docs in top-k results

**Targets:**
- Sentence level Recall@10: ≥ 0.85
- Paragraph level Recall@10: ≥ 0.88
- Document level Recall@10: ≥ 0.90

**nDCG@k:** Normalized Discounted Cumulative Gain

**Targets:**
- Sentence nDCG@10: ≥ 0.82
- Paragraph nDCG@10: ≥ 0.85
- Document nDCG@10: ≥ 0.88

**Test queries:** 100 per level  
**Ground truth:** `samples/metrics_qrels.txt` (TREC format)

### Latency & Throughput

| Endpoint | p50 | p95 | p99 |
|----------|-----|-----|-----|
| /encode | 5ms | 15ms | 30ms |
| /decode | 3ms | 10ms | 25ms |
| /search (GPU) | 60ms | 150ms | 300ms |
| /search (CPU) | 200ms | 400ms | 800ms |

**Cold start:** < 5 seconds (indices load < 4 sec)  
**Throughput:** 1000 QPS, 100 concurrent requests

### Acceptance Criteria (Beta)
All must pass simultaneously:

```
✅ H-Coherence: sent_para >= 0.78, para_doc >= 0.80
✅ H-Stability: max_drift <= 0.08
✅ IR: sent_recall@10 >= 0.85, doc_recall@10 >= 0.90
✅ Latency: search p50 <= 60ms (GPU) / 200ms (CPU)
✅ Startup: cold_start <= 5 seconds
```

---

## 🔗 How Configs Drive Development

### E1: API & Contracts
- **Uses:** `configs/api/routes.yaml` + `schemas.json`
- **Output:** FastAPI routes with Pydantic validation
- **Example:**
  ```python
  from fastapi import FastAPI
  from pydantic import BaseModel
  import yaml, json
  
  routes = yaml.safe_load(open('configs/api/routes.yaml'))
  schemas = json.load(open('configs/api/schemas.json'))
  
  @app.post(routes['encode']['path'])
  async def encode(req: EncodeRequest):  # Schema from schemas.json
      ...
  ```

### E2: Indices & MANIFEST
- **Uses:** `configs/indices/{sent,para,doc}_*.yaml` + `manifest_schema.json`
- **Output:** Index builders following hyperparameters
- **Example:**
  ```python
  hnsw_config = yaml.safe_load(open('configs/indices/sent_hnsw.yaml'))
  index = hnswlib.Index(...)
  index.init_index(max_elements=N, ef_construction=hnsw_config['hnsw']['ef_construction'], M=hnsw_config['hnsw']['M'])
  ```

### E3: Metrics & Acceptance
- **Uses:** `configs/metrics/h_metrics.yaml`
- **Output:** Measurement code + Prometheus exporters
- **Example:**
  ```python
  metrics_config = yaml.safe_load(open('configs/metrics/h_metrics.yaml'))
  
  # Measure H-Coherence
  coherence = measure_h_coherence(test_set)
  assert coherence >= metrics_config['h_coherence']['sent_to_para']['target']
  ```

---

## 🚀 Getting Started (Dev Sprint)

### Step 1: Load Configs
```python
import yaml, json

api_routes = yaml.safe_load(open('src/atlas/configs/api/routes.yaml'))
api_schemas = json.load(open('src/atlas/configs/api/schemas.json'))
indices_config = {
    'sent': yaml.safe_load(open('src/atlas/configs/indices/sent_hnsw.yaml')),
    'para': yaml.safe_load(open('src/atlas/configs/indices/para_hnsw.yaml')),
    'doc': yaml.safe_load(open('src/atlas/configs/indices/doc_faiss.yaml'))
}
metrics_config = yaml.safe_load(open('src/atlas/configs/metrics/h_metrics.yaml'))
```

### Step 2: Implement API Schemas (E1.1)
```python
# src/atlas/api/schemas.py
from pydantic import BaseModel
from typing import List

EncodeRequest = pydantic_from_json_schema(
    api_schemas['definitions']['EncodeRequest']
)
EncodeResponse = pydantic_from_json_schema(
    api_schemas['definitions']['EncodeResponse']
)
```

### Step 3: Implement Index Builders (E2.1-E2.2)
```python
# src/atlas/indices/hnsw_builder.py
from src.atlas.configs import indices_config

sent_config = indices_config['sent']
sent_hnsw = build_hnsw(
    vectors=...,
    M=sent_config['hnsw']['M'],
    ef_construction=sent_config['hnsw']['ef_construction'],
    ef_search=sent_config['hnsw']['ef_search']
)
```

### Step 4: Implement Metrics (E3.1-E3.3)
```python
# src/atlas/metrics/h_coherence.py
from src.atlas.configs import metrics_config

target = metrics_config['h_coherence']['sent_to_para']['target']
coherence = measure_coherence(sent_vecs, para_vecs)
assert coherence >= target, f"Expected >= {target}, got {coherence}"
```

---

## 📝 Modifying Configs

⚠️ **Important:** Configs are **locked for Sprint 0.2.0-beta**

To propose changes:

1. **Create Issue:** `[CONFIG] Proposal: <change>`
2. **Discuss:** Impacts on all epics (E1-E7)
3. **PR Review:** Core team approval required
4. **Impact Analysis:** How it affects dependent tasks

---

## 🔍 Validation Tools

### Validate API schemas
```bash
python -c "
import json
from jsonschema import Draft7Validator
schemas = json.load(open('src/atlas/configs/api/schemas.json'))
Draft7Validator.check_schema(schemas['definitions']['EncodeRequest'])
print('✅ API schemas valid')
"
```

### Validate MANIFEST
```bash
python -c "
import json
from jsonschema import validate
manifest = json.load(open('MANIFEST.v0_2.json'))
manifest_schema = json.load(open('src/atlas/configs/indices/manifest_schema.json'))
validate(instance=manifest, schema=manifest_schema)
print('✅ MANIFEST valid')
"
```

### Validate indices config
```bash
python -c "
import yaml
for level in ['sent', 'para']:
    cfg = yaml.safe_load(open(f'src/atlas/configs/indices/{level}_hnsw.yaml'))
    assert cfg['index_type'] == 'HNSW'
    assert cfg['vector_dim'] == 384
print('✅ Indices configs valid')
"
```

---

## 📚 Links

- **TZ:** [docs/TZ_ATLAS_BETA.md](../../docs/TZ_ATLAS_BETA.md)
- **Tasks:** [docs/ATLAS_BETA_TASKS.md](../../docs/ATLAS_BETA_TASKS.md)
- **Status:** [docs/ATLAS_BETA_DEVELOPMENT_STATUS.md](../../docs/ATLAS_BETA_DEVELOPMENT_STATUS.md)

---

## 🏁 Summary

This baseline provides:

✅ **API Contract** — All 8 endpoints + schemas  
✅ **Index Parameters** — HNSW + FAISS hyperparameters  
✅ **Metrics Targets** — H-Coherence, H-Stability, IR, latency  
✅ **MANIFEST Schema** — Validation for index versioning  
✅ **Hard boundaries** — No ambiguity for E1-E7 implementation  

**Ready for E1 & E2 development!** 🚀
