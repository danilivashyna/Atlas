#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Quick verification script for v0.2 setup
Checks that all components are properly installed and importable
"""

import sys
from pathlib import Path


def check_imports():
    """Check that all key modules can be imported"""
    print("🔍 Checking imports...")
    
    checks = [
        ("atlas", "Main package"),
        ("atlas.encoder", "Rule-based encoder"),
        ("atlas.decoder", "Rule-based decoder"),
        ("atlas.dimensions", "Dimensions"),
        ("atlas.space", "Semantic space"),
        ("atlas.hierarchical", "Hierarchical module"),
        ("atlas.cli", "CLI"),
        ("atlas.api.app", "FastAPI app"),
        ("atlas.models.encoder_bert", "BERT encoder (v0.2)"),
        ("atlas.models.decoder_transformer", "Transformer decoder (v0.2)"),
        ("atlas.models.losses_hier", "Hierarchical losses (v0.2)"),
        ("atlas.metrics.metrics_hier", "Hierarchical metrics (v0.2)"),
        ("atlas.training.distill", "Distillation (v0.2)"),
    ]
    
    failed = []
    for module, description in checks:
        try:
            __import__(module)
            print(f"  ✓ {module:40s} - {description}")
        except ImportError as e:
            print(f"  ✗ {module:40s} - {description}")
            print(f"    Error: {e}")
            failed.append((module, str(e)))
    
    return len(failed) == 0, failed


def check_files():
    """Check that all v0.2 files exist"""
    print("\n🔍 Checking files...")
    
    required_files = [
        "src/atlas/models/__init__.py",
        "src/atlas/models/encoder_bert.py",
        "src/atlas/models/decoder_transformer.py",
        "src/atlas/models/losses_hier.py",
        "src/atlas/metrics/__init__.py",
        "src/atlas/metrics/metrics_hier.py",
        "src/atlas/training/__init__.py",
        "src/atlas/training/distill.py",
        ".vscode/launch.json",
        ".vscode/settings.json",
        "Makefile",
        "DEVELOPMENT_LOCAL_SETUP.md",
        "v0.2_DEVELOPMENT_PLAN.md",
        "docs/LICENSING.md",
    ]
    
    failed = []
    for filepath in required_files:
        if Path(filepath).exists():
            print(f"  ✓ {filepath}")
        else:
            print(f"  ✗ {filepath} (MISSING)")
            failed.append(filepath)
    
    return len(failed) == 0, failed


def check_dependencies():
    """Check that required dependencies are installed"""
    print("\n🔍 Checking dependencies...")
    
    dependencies = [
        ("torch", "PyTorch"),
        ("transformers", "Hugging Face Transformers"),
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("numpy", "NumPy"),
        ("pydantic", "Pydantic"),
        ("pytest", "pytest (optional)"),
        ("black", "Black (optional)"),
        ("ruff", "Ruff (optional)"),
    ]
    
    failed = []
    for package, description in dependencies:
        try:
            __import__(package)
            print(f"  ✓ {package:20s} - {description}")
        except ImportError:
            optional = "(optional)" in description
            status = "⚠" if optional else "✗"
            print(f"  {status} {package:20s} - {description}")
            if not optional:
                failed.append(package)
    
    return len(failed) == 0, failed


def print_summary(checks_results):
    """Print summary of all checks"""
    print("\n" + "="*70)
    print("📊 VERIFICATION SUMMARY")
    print("="*70)
    
    all_passed = True
    for check_name, (passed, failed_items) in checks_results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"\n{check_name}: {status}")
        if failed_items:
            print("  Failed items:")
            for item in failed_items:
                if isinstance(item, tuple):
                    print(f"    - {item[0]}: {item[1]}")
                else:
                    print(f"    - {item}")
            all_passed = False
    
    print("\n" + "="*70)
    if all_passed:
        print("✅ All checks passed! v0.2 setup is complete.")
        print("\n🚀 Next steps:")
        print("  1. make api                    # Start API server")
        print("  2. curl http://localhost:8000/docs  # Open API docs")
        print("  3. python examples/basic_usage.py   # Run example")
        print("  4. Read DEVELOPMENT_LOCAL_SETUP.md  # Full guide")
        return 0
    else:
        print("⚠️  Some checks failed. Please review and install missing dependencies.")
        print("\n🔧 Quick fix:")
        print("  pip install -r requirements.txt")
        print("  pip install torch transformers")
        print("  pip install -e .")
        return 1


def main():
    """Run all checks"""
    print("\n" + "="*70)
    print("🔍 ATLAS v0.2 VERIFICATION")
    print("="*70)
    
    results = {
        "File Structure": check_files(),
        "Imports": check_imports(),
        "Dependencies": check_dependencies(),
    }
    
    exit_code = print_summary(results)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
