# SPDX-License-Identifier: AGPL-3.0-or-later
# Atlas Makefile — quick commands for development & deployment

.PHONY: help venv install test lint format run docker docker-build docker-run validate smoke clean self-smoke self-test self-clean

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

.DEFAULT_GOAL := help

