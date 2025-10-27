"""
Atlas β Configuration Loader
Version: 0.2.0-beta

Provides unified access to all configuration baseline files:
- API routes & schemas
- Index parameters (HNSW, FAISS)
- Metrics targets & thresholds
"""

import json
import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigLoader:
    """Unified configuration loader for Atlas β"""
    
    CONFIG_DIR = Path(__file__).parent
    
    _cached_configs: Dict[str, Any] = {}
    
    @classmethod
    def get_config_path(cls, filename: str) -> Path:
        """Get full path to config file"""
        path = cls.CONFIG_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Config not found: {path}")
        return path
    
    @classmethod
    def load_yaml(cls, filename: str) -> Dict[str, Any]:
        """Load and cache YAML config"""
        if filename in cls._cached_configs:
            return cls._cached_configs[filename]
        
        path = cls.get_config_path(filename)
        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        cls._cached_configs[filename] = config
        return config
    
    @classmethod
    def load_json(cls, filename: str) -> Dict[str, Any]:
        """Load and cache JSON config"""
        if filename in cls._cached_configs:
            return cls._cached_configs[filename]
        
        path = cls.get_config_path(filename)
        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        cls._cached_configs[filename] = config
        return config
    
    @classmethod
    def get_api_routes(cls) -> Dict[str, Any]:
        """Load API routes configuration"""
        return cls.load_yaml('api/routes.yaml')
    
    @classmethod
    def get_api_schemas(cls) -> Dict[str, Any]:
        """Load API JSON schemas"""
        return cls.load_json('api/schemas.json')
    
    @classmethod
    def get_api_schema(cls, schema_name: str) -> Dict[str, Any]:
        """Get specific API schema by name"""
        schemas = cls.get_api_schemas()
        if schema_name not in schemas.get('definitions', {}):
            raise ValueError(f"Schema not found: {schema_name}")
        return schemas['definitions'][schema_name]
    
    @classmethod
    def get_index_config(cls, level: str) -> Dict[str, Any]:
        """Load index configuration by level (sentence|paragraph|document)"""
        if level == 'sentence':
            return cls.load_yaml('indices/sent_hnsw.yaml')
        elif level == 'paragraph':
            return cls.load_yaml('indices/para_hnsw.yaml')
        elif level == 'document':
            return cls.load_yaml('indices/doc_faiss.yaml')
        else:
            raise ValueError(f"Unknown level: {level}")
    
    @classmethod
    def get_all_index_configs(cls) -> Dict[str, Dict[str, Any]]:
        """Load all index configurations"""
        return {
            'sentence': cls.get_index_config('sentence'),
            'paragraph': cls.get_index_config('paragraph'),
            'document': cls.get_index_config('document')
        }
    
    @classmethod
    def get_manifest_schema(cls) -> Dict[str, Any]:
        """Load MANIFEST validation schema"""
        return cls.load_json('indices/manifest_schema.json')
    
    @classmethod
    def get_metrics_config(cls) -> Dict[str, Any]:
        """Load metrics configuration"""
        return cls.load_yaml('metrics/h_metrics.yaml')
    
    @classmethod
    def get_h_coherence_targets(cls) -> Dict[str, float]:
        """Get H-Coherence targets"""
        config = cls.get_metrics_config()
        return {
            'sent_to_para': config['h_coherence']['sent_to_para']['target'],
            'para_to_doc': config['h_coherence']['para_to_doc']['target']
        }
    
    @classmethod
    def get_h_stability_targets(cls) -> Dict[str, float]:
        """Get H-Stability targets"""
        config = cls.get_metrics_config()
        return {
            'max_drift': config['h_stability']['max_drift'],
            'warning_drift': config['h_stability']['warning_drift']
        }
    
    @classmethod
    def get_ir_targets(cls) -> Dict[str, float]:
        """Get IR metrics targets (Recall, nDCG)"""
        config = cls.get_metrics_config()
        return config['ir_metrics']['targets']
    
    @classmethod
    def get_latency_targets(cls, device: str = 'gpu') -> Dict[str, Dict[str, int]]:
        """Get latency targets (ms) for each endpoint
        
        Args:
            device: 'gpu' or 'cpu'
        """
        config = cls.get_metrics_config()
        latency = config['latency']
        
        if device.lower() == 'gpu':
            search_targets = latency['search']['gpu']
        else:
            search_targets = latency['search']['cpu']
        
        return {
            'encode': latency['encode'],
            'decode': latency['decode'],
            'search': search_targets,
            'cold_start': latency['cold_start']
        }
    
    @classmethod
    def validate_manifest(cls, manifest: Dict[str, Any]) -> bool:
        """Validate MANIFEST against schema
        
        Args:
            manifest: MANIFEST.v0_2.json content
        
        Returns:
            True if valid
        
        Raises:
            jsonschema.ValidationError if invalid
        """
        from jsonschema import validate
        schema = cls.get_manifest_schema()
        validate(instance=manifest, schema=schema)
        return True
    
    @classmethod
    def clear_cache(cls):
        """Clear cached configurations"""
        cls._cached_configs.clear()


# Convenience exports
def get_api_routes() -> Dict[str, Any]:
    """Get API routes configuration"""
    return ConfigLoader.get_api_routes()


def get_api_schemas() -> Dict[str, Any]:
    """Get API schemas"""
    return ConfigLoader.get_api_schemas()


def get_index_configs() -> Dict[str, Dict[str, Any]]:
    """Get all index configurations"""
    return ConfigLoader.get_all_index_configs()


def get_metrics_config() -> Dict[str, Any]:
    """Get metrics configuration"""
    return ConfigLoader.get_metrics_config()


def get_h_coherence_targets() -> Dict[str, float]:
    """Get H-Coherence targets"""
    return ConfigLoader.get_h_coherence_targets()


def get_h_stability_targets() -> Dict[str, float]:
    """Get H-Stability targets"""
    return ConfigLoader.get_h_stability_targets()


def get_latency_targets(device: str = 'gpu') -> Dict[str, Any]:
    """Get latency targets for endpoint"""
    return ConfigLoader.get_latency_targets(device)


if __name__ == '__main__':
    # Quick test of config loader
    print("Testing ConfigLoader...")
    
    try:
        routes = ConfigLoader.get_api_routes()
        print(f"✅ API routes loaded: {len(routes)} endpoints")
        
        api_schemas = ConfigLoader.get_api_schemas()
        print(f"✅ API schemas loaded: {len(api_schemas['definitions'])} schemas")
        
        indices = ConfigLoader.get_all_index_configs()
        print(f"✅ Index configs loaded: {list(indices.keys())}")
        
        metrics = ConfigLoader.get_metrics_config()
        print("✅ Metrics config loaded")
        
        targets = ConfigLoader.get_h_coherence_targets()
        print(f"✅ H-Coherence targets: {targets}")
        
        print("\n✅ All configurations loaded successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
