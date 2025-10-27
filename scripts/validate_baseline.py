#!/usr/bin/env python3
"""
Validate baseline configs:
- api/routes.yaml & schemas.json are loadable and consistent
- indices/*.yaml have sane ranges
- metrics/h_metrics.yaml has required keys
- manifest_schema.json validates a sample MANIFEST (if provided)

Usage:
  python scripts/validate_baseline.py [--manifest MANIFEST.json] [--strict]

Exit codes: 0 ok, 1 validation failed.
"""
import sys
import json
import argparse
import pathlib
from typing import Any, Dict

try:
    import yaml
except ImportError as e:
    print("Error: PyYAML not found. Install: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

BASE = pathlib.Path(__file__).resolve().parents[1]  # repo root
CFG = BASE / "src" / "atlas" / "configs"

def load_yaml(path: pathlib.Path) -> Dict[str, Any]:
    """Load YAML file, raise ValueError on parse error."""
    with path.open("r", encoding="utf-8") as handle:
        result = yaml.safe_load(handle)
    if not isinstance(result, dict):
        raise ValueError(f"{path.name}: YAML did not parse to dict")
    return result

def load_json(path: pathlib.Path) -> Dict[str, Any]:
    """Load JSON file, raise ValueError on parse error."""
    with path.open("r", encoding="utf-8") as handle:
        result = json.load(handle)
    if not isinstance(result, dict):
        raise ValueError(f"{path.name}: JSON did not parse to dict")
    return result

def check_api(strict: bool) -> None:
    """Validate API routes and schemas."""
    routes_path = CFG / "api" / "routes.yaml"
    schemas_path = CFG / "api" / "schemas.json"
    
    if not routes_path.exists():
        raise ValueError(f"routes.yaml not found at {routes_path}")
    if not schemas_path.exists():
        raise ValueError(f"schemas.json not found at {schemas_path}")
    
    routes = load_yaml(routes_path)
    schemas = load_json(schemas_path)
    
    # Verify required routes
    required_routes = [
        "/encode", "/decode", "/explain",
        "/encode_h", "/decode_h", "/manipulate_h", "/search",
        "/health"
    ]
    routes_dict = routes.get("routes", {})
    missing = [p for p in required_routes if p not in routes_dict]
    if missing:
        raise ValueError(f"routes.yaml missing routes: {missing}")
    
    # Verify required schema definitions
    required_schemas = [
        "EncodeRequest", "EncodeResponse",
        "SearchRequest", "SearchResponse",
        "EncodeHierarchicalRequest", "EncodeHierarchicalResponse"
    ]
    defs = schemas.get("$defs", {})
    missing_defs = [n for n in required_schemas if n not in defs]
    if missing_defs:
        raise ValueError(f"schemas.json missing $defs: {missing_defs}")
    
    # Strict check: rate_limit must be positive
    if strict:
        rate_limit = routes.get("security", {}).get("rate_limit", 0)
        if rate_limit <= 0:
            raise ValueError("strict mode: rate_limit must be > 0")

def check_indices() -> None:
    """Validate HNSW and FAISS configuration files."""
    sent_path = CFG / "indices" / "sent_hnsw.yaml"
    para_path = CFG / "indices" / "para_hnsw.yaml"
    doc_path = CFG / "indices" / "doc_faiss.yaml"
    
    for path in [sent_path, para_path, doc_path]:
        if not path.exists():
            raise ValueError(f"Index config not found: {path}")
    
    sent = load_yaml(sent_path)
    para = load_yaml(para_path)
    doc = load_yaml(doc_path)
    
    def validate_hnsw(cfg: Dict[str, Any], name: str) -> None:
        """Check HNSW parameter ranges."""
        M = cfg.get("M", 0)
        efC = cfg.get("ef_construction", 0)
        efS = cfg.get("ef_search", 0)
        
        if not (4 <= M <= 128):
            raise ValueError(f"{name}: M={M} out of range [4, 128]")
        if not (50 <= efC <= 2000):
            raise ValueError(f"{name}: ef_construction={efC} out of range [50, 2000]")
        if not (16 <= efS <= 1024):
            raise ValueError(f"{name}: ef_search={efS} out of range [16, 1024]")
    
    def validate_faiss(cfg: Dict[str, Any]) -> None:
        """Check FAISS parameter ranges."""
        ivf = cfg.get("ivf", {})
        pq = cfg.get("pq", {})
        
        nlist = ivf.get("nlist", 0)
        m = pq.get("m", 0)
        nbits = pq.get("nbits", 0)
        
        if not (64 <= nlist <= 65536):
            raise ValueError(f"doc_faiss: nlist={nlist} out of range [64, 65536]")
        if not (8 <= m <= 64):
            raise ValueError(f"doc_faiss: pq.m={m} out of range [8, 64]")
        if nbits not in (4, 6, 8):
            raise ValueError(f"doc_faiss: pq.nbits={nbits} must be in [4, 6, 8]")
    
    validate_hnsw(sent, "sent_hnsw")
    validate_hnsw(para, "para_hnsw")
    validate_faiss(doc)

def check_metrics() -> None:
    """Validate metrics configuration file."""
    metrics_path = CFG / "metrics" / "h_metrics.yaml"
    
    if not metrics_path.exists():
        raise ValueError(f"h_metrics.yaml not found at {metrics_path}")
    
    hm = load_yaml(metrics_path)
    
    # Verify required sections
    required_sections = ["h_coherence", "h_stability", "ir", "latency"]
    missing_sections = [k for k in required_sections if k not in hm]
    if missing_sections:
        raise ValueError(f"h_metrics.yaml missing sections: {missing_sections}")

def check_manifest(manifest_path: pathlib.Path) -> None:
    """Validate MANIFEST.v0_2.json against manifest_schema.json."""
    try:
        from jsonschema import validate, Draft202012Validator
    except ImportError as e:
        raise RuntimeError(
            "jsonschema not found. Install: pip install jsonschema"
        ) from e
    
    schema_path = CFG / "indices" / "manifest_schema.json"
    
    if not schema_path.exists():
        raise ValueError(f"manifest_schema.json not found at {schema_path}")
    if not manifest_path.exists():
        raise ValueError(f"MANIFEST not found at {manifest_path}")
    
    schema = load_json(schema_path)
    manifest = load_json(manifest_path)
    
    # Validate schema itself
    try:
        Draft202012Validator.check_schema(schema)
    except ValueError as e:
        raise ValueError(f"manifest_schema.json is invalid: {e}") from e
    
    # Validate manifest against schema
    try:
        validate(instance=manifest, schema=schema)
    except Exception as e:
        raise ValueError(f"MANIFEST validation failed: {e}") from e

def main() -> int:
    """Parse args and run all validation checks."""
    ap = argparse.ArgumentParser(
        description="Validate Atlas baseline configurations"
    )
    ap.add_argument(
        "--manifest",
        type=pathlib.Path,
        default=None,
        help="Path to MANIFEST.v0_2.json for validation"
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Enable stricter checks (e.g., rate_limit > 0)"
    )
    
    args = ap.parse_args()
    
    checks = [
        ("API routes & schemas", lambda: check_api(args.strict)),
        ("Index configs (HNSW/FAISS)", check_indices),
        ("Metrics config", check_metrics),
    ]
    
    if args.manifest:
        checks.append(("MANIFEST validation", lambda: check_manifest(args.manifest)))
    
    failed = []
    for check_name, check_fn in checks:
        try:
            check_fn()
            print(f"✅ {check_name}")
        except (ValueError, RuntimeError) as e:
            print(f"❌ {check_name}: {e}", file=sys.stderr)
            failed.append(check_name)
    
    if failed:
        print(f"\n❌ Validation failed ({len(failed)}/{len(checks)} checks)", file=sys.stderr)
        return 1
    
    print(f"\n✅ All {len(checks)} baseline validation checks passed")
    return 0

if __name__ == "__main__":
    sys.exit(main())
