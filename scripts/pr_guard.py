#!/usr/bin/env python3
"""PR Guard: Scope validation before PR submission."""
import os
import re
import subprocess
import sys
from pathlib import Path


# Forbidden patterns (HSI, consciousness, learning, hidden state)
FORBIDDEN = {
    r'\bconscious': "Consciousness concept",
    r'\bself.{0,10}improve': "Self-improvement",
    r'\battention\b': "Attention policy",
    r'self\.session': "Hidden session state",
    r'self\.history': "History tracking",
}

# Non-determinism patterns
DETERMINISM = {
    r'import\s+time\b': "Non-deterministic time",
    r'import\s+random\b': "Non-deterministic random",
    r'datetime\.now': "Non-deterministic datetime",
}

EXEMPT = {r'random\.seed', r'np\.random\.seed', r'# seed'}


def check_file(filepath):
    """Check file for violations."""
    violations = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except (OSError, IOError):
        return violations
    
    for line_num, line in enumerate(lines, 1):
        if line.strip().startswith('#'):
            continue
        
        for pattern, reason in FORBIDDEN.items():
            if re.search(pattern, line, re.IGNORECASE):
                violations.append((line_num, "SCOPE", reason))
        
        is_exempt = any(re.search(e, line) for e in EXEMPT)
        if not is_exempt:
            for pattern, reason in DETERMINISM.items():
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append((line_num, "DETERMINISM", reason))
    
    return violations


def main():
    """Main entry point."""
    patterns = ["src/atlas", "tests"]
    scope_violations = 0
    determ_warnings = 0
    
    print("=" * 60)
    print("🛡️  PR GUARD: Atlas β Scope & Determinism Validator")
    print("=" * 60)
    
    for pattern in patterns:
        if os.path.isfile(pattern):
            files = [pattern]
        else:
            files = list(Path(pattern).rglob("*.py"))
        
        for filepath in files:
            violations = check_file(str(filepath))
            for line_num, v_type, msg in violations:
                if v_type == "SCOPE":
                    scope_violations += 1
                    print(f"🚩 SCOPE VIOLATION: {filepath}:{line_num} — {msg}")
                else:
                    determ_warnings += 1
                    print(f"⚠️  DETERMINISM WARNING: {filepath}:{line_num} — {msg}")
    
    if scope_violations > 0:
        print(f"\n❌ Found {scope_violations} SCOPE VIOLATIONS")
        return 1
    
    if determ_warnings > 0:
        print(f"\n⚠️  Found {determ_warnings} DETERMINISM WARNINGS")
    else:
        print("\n✅ No violations found")
    
    print("\n🔧 Running validation tools...")
    result = subprocess.run(["make", "validate", "--strict"], capture_output=True, check=False)
    if result.returncode != 0:
        print("❌ `make validate` failed")
        return 1
    print("✅ `make validate` passed")
    
    result = subprocess.run(["make", "smoke"], capture_output=True, check=False)
    if result.returncode != 0:
        print("❌ `make smoke` failed")
        return 1
    print("✅ `make smoke` passed")
    
    print("\n✨ ALL CHECKS PASSED — Ready for PR submission!")
    print("📋 Use PR_SCOPE_CHECKLIST.md before submitting")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
