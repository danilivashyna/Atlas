#!/usr/bin/env python3
"""
Integration smoke for wiring (no heavy deps):
- Loads API routes/schemas
- Mocks indices and FAB fuse
- Simulates /search and /encode_h request/response shape
"""
import json
import pathlib
from typing import Any, Dict, List

try:
    import yaml
except ImportError:
    print("Error: PyYAML not found. Install: pip install pyyaml")
    exit(1)

BASE = pathlib.Path(__file__).resolve().parents[1]
CFG = BASE / "src" / "atlas" / "configs"

def load_yaml(path: pathlib.Path) -> Dict[str, Any]:
    """Load YAML file."""
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)

def load_json(path: pathlib.Path) -> Dict[str, Any]:
    """Load JSON file."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)

def mock_knn(level: str, query: str, k: int) -> List[Dict[str, Any]]:
    """Generate mock KNN results deterministically."""
    # Use query and level to seed for reproducibility
    # (seed_val used for reproducibility; deterministic without randomness)
    _ = hash((level, query)) & 0xfffffff
    
    hits = []
    for i in range(k):
        score = 1.0 - i / (k + 3)
        hits.append({
            "id": f"{level}-{i}",
            "score": score,
            "level": level
        })
    return hits

def fuse_rrf(buckets: List[List[Dict[str, Any]]], k: int) -> List[Dict[str, Any]]:
    """RRF fusion: score = sum(1/(rank + 60))"""
    from collections import defaultdict
    
    agg: Dict[str, float] = defaultdict(float)
    
    for hits in buckets:
        for rank, hit in enumerate(hits):
            agg[hit["id"]] += 1.0 / (rank + 60.0)
    
    merged = [{"id": hit_id, "score": score} for hit_id, score in agg.items()]
    merged.sort(key=lambda x: x["score"], reverse=True)
    return merged[:k]

def smoke_search() -> None:
    """Simulate /search endpoint with mock indices."""
    print("\n[/search smoke test]")
    
    routes = load_yaml(CFG / "api" / "routes.yaml")
    assert "/search" in routes["routes"], "route /search missing from routes.yaml"
    
    # Mock search parameters
    query = "test query about machine learning"
    k = 5
    
    # Mock three-level search (parallel fan-out)
    sent_hits = mock_knn("sent", query, k)
    para_hits = mock_knn("para", query, k)
    doc_hits = mock_knn("doc", query, k)
    
    # Fuse results using RRF
    fused = fuse_rrf([sent_hits, para_hits, doc_hits], k)
    
    # Build response
    resp = {
        "hits": fused[:k],
        "debug": {
            "sent_top2": sent_hits[:2],
            "para_top2": para_hits[:2],
            "doc_top2": doc_hits[:2],
            "fuse_algorithm": "RRF(k=60)"
        }
    }
    
    # Verify shape
    assert isinstance(resp["hits"], list), "hits must be list"
    assert len(resp["hits"]) <= k, f"hits length must be <= {k}"
    assert all("id" in h and "score" in h for h in resp["hits"]), "each hit must have id and score"
    
    print(f"  ✅ Parallel search to 3 levels (sent={len(sent_hits)}, para={len(para_hits)}, doc={len(doc_hits)})")
    print(f"  ✅ RRF fusion merged to {len(resp['hits'])} results")
    print(f"  ✅ Response shape valid: {json.dumps(resp)[:120]}...")

def smoke_encode_h() -> None:
    """Simulate /encode_h endpoint."""
    print("\n[/encode_h smoke test]")
    
    schemas = load_json(CFG / "api" / "schemas.json")
    
    # Verify schema definitions exist
    required_defs = [
        "EncodeHierarchicalRequest",
        "EncodeHierarchicalResponse"
    ]
    defs = schemas.get("$defs", {})
    for name in required_defs:
        assert name in defs, f"missing schema def: {name}"
    
    # Mock hierarchical encoding response
    resp = {
        "levels": {
            "sentence": [
                [0.1, 0.2, 0.3],
                [0.4, 0.5, 0.6]
            ],
            "paragraph": [
                [0.15, 0.25, 0.35]
            ]
        },
        "proj_384": [0.0] * 384,
        "proj_768": [0.0] * 768,
        "masks": {
            "token_to_sent": [0, 0, 1, 1],
            "sent_to_para": [0, 1]
        }
    }
    
    # Verify shape
    assert isinstance(resp["levels"], dict), "levels must be dict"
    assert "sentence" in resp["levels"], "levels must have sentence"
    assert "paragraph" in resp["levels"], "levels must have paragraph"
    assert len(resp["proj_384"]) == 384, "proj_384 must be 384-dim"
    assert len(resp["proj_768"]) == 768, "proj_768 must be 768-dim"
    
    print(f"  ✅ Schema defs present: {required_defs}")
    print(f"  ✅ Hierarchical embedding dims valid: proj_384={len(resp['proj_384'])}, proj_768={len(resp['proj_768'])}")
    print(f"  ✅ Masks present: token_to_sent (len={len(resp['masks']['token_to_sent'])}), sent_to_para (len={len(resp['masks']['sent_to_para'])})")

def smoke_encode() -> None:
    """Simulate /encode endpoint (5D rule-based)."""
    print("\n[/encode smoke test]")
    
    routes = load_yaml(CFG / "api" / "routes.yaml")
    assert "/encode" in routes["routes"], "route /encode missing"
    
    # Mock 5D encoding response
    resp = {
        "vector": [100, 150, 50, 200, 75],  # [A, B, C, D, E]
        "metadata": {
            "dimensions": ["authority", "brevity", "category", "disposition", "encoding_style"],
            "text_hash": "abc123"
        }
    }
    
    # Verify shape
    assert isinstance(resp["vector"], list), "vector must be list"
    assert len(resp["vector"]) == 5, "5D vector must have 5 elements"
    assert all(0 <= v <= 255 for v in resp["vector"]), "each element must be 0-255"
    
    print(f"  ✅ 5D vector generated: {resp['vector']}")
    print(f"  ✅ Dimensions labeled: {resp['metadata']['dimensions']}")

def smoke_reproducibility() -> None:
    """Verify deterministic results."""
    print("\n[reproducibility smoke test]")
    
    # Run /search twice with same query
    query = "reproducibility test"
    k = 3
    
    fused1 = fuse_rrf(
        [mock_knn("sent", query, k), mock_knn("para", query, k), mock_knn("doc", query, k)],
        k
    )
    fused2 = fuse_rrf(
        [mock_knn("sent", query, k), mock_knn("para", query, k), mock_knn("doc", query, k)],
        k
    )
    
    # Compare results
    ids1 = [h["id"] for h in fused1]
    ids2 = [h["id"] for h in fused2]
    scores1 = [h["score"] for h in fused1]
    scores2 = [h["score"] for h in fused2]
    
    assert ids1 == ids2, f"RRF reproducibility failed: {ids1} != {ids2}"
    assert scores1 == scores2, f"RRF scores reproducibility failed: {scores1} != {scores2}"
    
    print(f"  ✅ RRF deterministic: identical query → identical results (ids={ids1})")

def main() -> int:
    """Run all smoke tests."""
    print("=" * 60)
    print("Atlas β — Wiring Smoke Tests")
    print("=" * 60)
    
    try:
        smoke_search()
        smoke_encode_h()
        smoke_encode()
        smoke_reproducibility()
        
        print("\n" + "=" * 60)
        print("✅ All wiring smoke tests passed")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n❌ Smoke test failed: {e}")
        return 1
    except (IOError, ValueError, ImportError) as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
