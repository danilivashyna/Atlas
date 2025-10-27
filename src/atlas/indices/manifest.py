"""
Atlas β — MANIFEST Generator

Generates and validates MANIFEST.v0_2.json for index versioning and integrity.
Includes SHA256 checksums for all models and indices.

Version: 0.2.0-beta
"""

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from atlas.configs import ConfigLoader


class MANIFESTGenerator:
    """
    Generator for MANIFEST.v0_2.json.
    
    Creates JSON manifest with:
    - Git metadata (commit SHA, branch, tag)
    - Model artifacts (encoders with SHA256)
    - Index artifacts (HNSW/FAISS with SHA256, hparams)
    
    ⚠️ Safety: SHA256 checksums ensure integrity, reproducible builds.
    """
    
    def __init__(self, version: str = "0.2", api_version: str = "beta"):
        """
        Initialize MANIFEST generator.
        
        Args:
            version: MANIFEST schema version (default: "0.2")
            api_version: Atlas API version (default: "beta")
        """
        self.version = version
        self.api_version = api_version
        self.git_info: Dict = {}
        self.models: List[Dict] = []
        self.indices: List[Dict] = []
    
    def add_git_info(
        self,
        head: Optional[str] = None,
        branch: Optional[str] = None,
        tag: Optional[str] = None,
    ):
        """
        Add git metadata to manifest.
        
        Args:
            head: Git commit SHA (defaults to current HEAD)
            branch: Git branch name (defaults to current branch)
            tag: Optional git tag
        
        Notes:
            - Auto-detects git info if not provided
            - Requires git CLI available
        """
        if head is None:
            head = self._get_git_head()
        if branch is None:
            branch = self._get_git_branch()
        
        self.git_info = {
            "head": head,
            "branch": branch,
        }
        
        if tag:
            self.git_info["tag"] = tag
    
    def add_model(
        self,
        name: str,
        file: Path,
        model_format: str,
        model_type: str,
        optional: bool = False,
    ):
        """
        Add model artifact to manifest.
        
        Args:
            name: Model name (e.g., "encoder_base")
            file: Path to model file
            model_format: Model format ("mxfp16", "mxfp4", "float32")
            model_type: Model role ("teacher", "student")
            optional: Whether model is optional (fallback to rule-based)
        
        Raises:
            FileNotFoundError: If model file doesn't exist
        """
        file = Path(file)
        if not file.exists():
            raise FileNotFoundError(f"Model file not found: {file}")
        
        sha256 = self._compute_sha256(file)
        size_bytes = file.stat().st_size
        
        self.models.append({
            "name": name,
            "file": str(file),
            "format": model_format,
            "sha256": sha256,
            "size_bytes": size_bytes,
            "type": model_type,
            "optional": optional,
        })
    
    def add_index(
        self,
        level: str,
        file: Path,
        index_type: str,
        vector_dim: int,
        num_vectors: int,
        metric: str,
        hparams: Optional[Dict] = None,
    ):
        """
        Add index artifact to manifest.
        
        Args:
            level: Hierarchical level ("sentence", "paragraph", "document")
            file: Path to index file
            index_type: Index algorithm ("HNSW", "FAISS", "BRUTE_FORCE")
            vector_dim: Vector dimensionality (384 or 768)
            num_vectors: Number of vectors in index
            metric: Distance metric ("cosine", "L2", "dot")
            hparams: Optional index hyperparameters (M, efC, nlist, etc.)
        
        Raises:
            FileNotFoundError: If index file doesn't exist
        """
        file = Path(file)
        if not file.exists():
            raise FileNotFoundError(f"Index file not found: {file}")
        
        sha256 = self._compute_sha256(file)
        size_bytes = file.stat().st_size
        created_at = datetime.now(timezone.utc).isoformat()
        
        index_entry = {
            "level": level,
            "file": str(file),
            "index_type": index_type,
            "vector_dim": vector_dim,
            "sha256": sha256,
            "size_bytes": size_bytes,
            "num_vectors": num_vectors,
            "metric": metric,
            "created_at": created_at,
        }
        
        if hparams:
            index_entry["hparams"] = hparams
        
        self.indices.append(index_entry)
    
    def generate(self) -> Dict:
        """
        Generate MANIFEST dictionary.
        
        Returns:
            MANIFEST dict ready for JSON serialization
        
        Raises:
            ValueError: If no indices added (at least 1 required)
        """
        if not self.indices:
            raise ValueError("MANIFEST requires at least 1 index")
        
        manifest = {
            "version": self.version,
            "api_version": self.api_version,
            "git": self.git_info,
            "models": self.models,
            "indices": self.indices,
        }
        
        return manifest
    
    def save(self, path: Path) -> Path:
        """
        Save MANIFEST to JSON file.
        
        Args:
            path: Output path (e.g., "MANIFEST.v0_2.json")
        
        Returns:
            Path to saved file
        
        Notes:
            - Pretty-printed with indent=2
            - Validates against schema before saving
        """
        manifest = self.generate()
        
        # Validate against schema
        self._validate_manifest(manifest)
        
        # Save to file
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        return path
    
    def _validate_manifest(self, manifest: Dict):
        """
        Validate MANIFEST against JSON schema.
        
        Args:
            manifest: MANIFEST dict
        
        Raises:
            jsonschema.ValidationError: If invalid
        """
        from jsonschema import validate
        
        schema = ConfigLoader.get_manifest_schema()
        validate(instance=manifest, schema=schema)
    
    def _compute_sha256(self, path: Path) -> str:
        """Compute SHA256 checksum of file."""
        sha256_hash = hashlib.sha256()
        
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    def _get_git_head(self) -> str:
        """Get current git HEAD SHA."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "unknown"
    
    def _get_git_branch(self) -> str:
        """Get current git branch name."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "unknown"


def load_manifest(path: Path) -> Dict:
    """
    Load and validate MANIFEST from JSON file.
    
    Args:
        path: Path to MANIFEST.v0_2.json
    
    Returns:
        Validated MANIFEST dict
    
    Raises:
        FileNotFoundError: If file doesn't exist
        jsonschema.ValidationError: If invalid
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"MANIFEST not found: {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    
    # Validate
    from jsonschema import validate
    schema = ConfigLoader.get_manifest_schema()
    validate(instance=manifest, schema=schema)
    
    return manifest


def verify_manifest_integrity(manifest: Dict, base_path: Path = Path(".")) -> bool:
    """
    Verify MANIFEST integrity by checking SHA256 checksums.
    
    Args:
        manifest: MANIFEST dict
        base_path: Base directory for resolving relative paths
    
    Returns:
        True if all checksums match
    
    Raises:
        FileNotFoundError: If any file missing
        ValueError: If checksum mismatch
    
    Notes:
        - Checks all models and indices
        - Returns False if any mismatch (with details in exception)
    """
    base_path = Path(base_path)
    
    # Verify models
    for model in manifest.get("models", []):
        file_path = base_path / model["file"]
        if not file_path.exists():
            raise FileNotFoundError(f"Model file missing: {file_path}")
        
        expected_sha256 = model["sha256"]
        actual_sha256 = _compute_sha256(file_path)
        
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"SHA256 mismatch for {file_path}: "
                f"expected {expected_sha256}, got {actual_sha256}"
            )
    
    # Verify indices
    for index in manifest.get("indices", []):
        file_path = base_path / index["file"]
        if not file_path.exists():
            raise FileNotFoundError(f"Index file missing: {file_path}")
        
        expected_sha256 = index["sha256"]
        actual_sha256 = _compute_sha256(file_path)
        
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"SHA256 mismatch for {file_path}: "
                f"expected {expected_sha256}, got {actual_sha256}"
            )
    
    return True


def _compute_sha256(path: Path) -> str:
    """Helper: Compute SHA256 checksum."""
    sha256_hash = hashlib.sha256()
    
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    
    return sha256_hash.hexdigest()
