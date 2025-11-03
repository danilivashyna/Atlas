# SPDX-License-Identifier: AGPL-3.0-or-later
# Atlas Makefile — quick commands for development & deployment

.PHONY: help venv install test lint format run docker docker-build docker-run validate smoke clean self-smoke self-test self-clean ci cov exp-smoke

help:
	@echo "Atlas — Semantic Space Control Panel"
	@echo ""
	@echo "Available targets:"
	@echo "  make venv          Create Python virtual environment"
	@echo "  make install       Install dependencies (dev + main)"
	@echo "  make validate      Validate all baseline configs (--strict)"
	@echo "  make smoke         Run wiring smoke tests"
	@echo "  make test          Run pytest suite (tests/)"
	@echo "  make lint          Run ruff + black check"
	@echo "  make format        Format code with black + isort"
	@echo "  make run           Run API server (uvicorn :8010)"
	@echo "  make docker        Build Docker image"
	@echo "  make docker-run    Run Docker container (:8010)"
	@echo "  make clean         Remove cache, venv, __pycache__"
	@echo ""
	@echo "SELF Experimental (Phase C):"
	@echo "  make self-test     Run SELF unit tests (test_self_*.py)"
	@echo "  make self-smoke    Run SELF resonance smoke test (500 ticks)"
	@echo "  make self-clean    Remove SELF artifacts (identity.jsonl, resonance_trace.jsonl)"
	@echo ""
	@echo "Phase B CI (local parity):"
	@echo "  make ci            Run full CI suite (lint + test + exp-smoke)"
	@echo "  make cov           Run coverage with threshold gates"
	@echo "  make exp-smoke     Run experimental smoke tests (SELF + Stability + Hysteresis)"
	@echo ""

venv:
	python3 -m venv venv
	@echo "✅ Virtual environment created. Activate with: source venv/bin/activate"

install: venv
	./venv/bin/pip install -e .[dev]
	@echo "✅ Dependencies installed"

validate:
	python scripts/validate_baseline.py --strict
	@echo "✅ Baseline configs validated"

smoke:
	python scripts/smoke_test_wiring.py
	@echo "✅ Wiring smoke tests passed"

test:
	pytest tests/ -v --tb=short
	@echo "✅ Tests completed"

lint:
	ruff check src/ tests/
	black --check src/ tests/
	@echo "✅ Linting passed"

format:
	black src/ tests/
	isort src/ tests/
	@echo "✅ Code formatted"

run:
	@echo "Starting Atlas API on http://localhost:8010"
	@echo "Press Ctrl+C to stop"
	ATLAS_LOG_LEVEL=DEBUG uvicorn src.atlas.api.app:app --reload --port 8010

docker:
	docker build -t atlas:latest .
	@echo "✅ Docker image built: atlas:latest"

docker-run:
	@echo "Running Atlas in Docker on http://localhost:8010"
	docker run -p 8010:8010 \
	  -e ATLAS_LOG_LEVEL=INFO \
	  -e ATLAS_MEMORY_BACKEND=sqlite \
	  --name atlas-api \
	  atlas:latest
	@echo "✅ Container started. Use 'docker stop atlas-api' to stop"

clean:
	rm -rf build/ dist/ .eggs/ *.egg-info/
	rm -rf .pytest_cache/ .ruff_cache/ .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "✅ Cache cleaned"

# ──────────────────────────────────────────────────────────
# SELF Experimental Targets (Phase C)
# ──────────────────────────────────────────────────────────

self-test:
	@echo "🧪 Running SELF unit tests..."
	AURIS_SELF=on pytest tests/test_self_*.py -v --tb=short --cov=src/orbis_self --cov-report=term-missing
	@echo "✅ SELF tests completed"

self-smoke:
	@echo "🔮 Running SELF resonance smoke test (500 ticks)..."
	AURIS_SELF=on python scripts/resonance_test.py
	@echo ""
	@echo "✅ SELF smoke test completed"
	@echo "   Artifacts:"
	@echo "   - data/identity.jsonl (heartbeat log)"
	@echo "   - logs/resonance_trace.jsonl (resonance metrics)"

self-clean:
	@echo "🧹 Cleaning SELF artifacts..."
	rm -f data/identity.jsonl
	rm -f logs/resonance_trace.jsonl
	@echo "✅ SELF artifacts removed"

# ──────────────────────────────────────────────────────────
# Phase B CI Targets (local parity)
# ──────────────────────────────────────────────────────────

ci: lint test exp-smoke
	@echo "✅ Full CI suite passed"

cov:
	@echo "📊 Running coverage with threshold gates..."
	AURIS_SELF=off AURIS_STABILITY=off AURIS_HYSTERESIS=off AURIS_METRICS_EXP=off \
	  pytest --cov=src --cov-report=term-missing --cov-report=json
	@python -c 'import json; data = json.load(open("coverage.json")); tot = data["totals"]["percent_covered"]; print(f"Total coverage: {tot:.1f}%"); assert tot >= 85.0, f"Total coverage {tot}% < 85%"'
	@echo "✅ Coverage gates passed"

exp-smoke:
	@echo "🔬 Running experimental smoke tests..."
	@mkdir -p logs data
	@echo "  → SELF resonance..."
	@AURIS_SELF=on python scripts/resonance_test.py
	@test -f data/identity.jsonl || (echo "❌ identity.jsonl not found" && exit 1)
	@python -c 'import re, pathlib; t = pathlib.Path("data/identity.jsonl").read_text(encoding="utf-8"); cnt = len(re.findall(r"\"kind\":\s*\"heartbeat\"", t)); print(f"  ✓ Heartbeats: {cnt}"); assert cnt >= 5, f"heartbeats={cnt} < 5"'
	@echo "  → Stability/Hysteresis probes..."
	@AURIS_STABILITY=on AURIS_HYSTERESIS=on AURIS_METRICS_EXP=on python scripts/stability_probe_exp.py
	@AURIS_STABILITY=on AURIS_HYSTERESIS=on AURIS_METRICS_EXP=on python scripts/hysteresis_probe_exp.py
	@echo "✅ Experimental smoke tests passed"

.DEFAULT_GOAL := help

