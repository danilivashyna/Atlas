# SPDX-License-Identifier: AGPL-3.0-or-later
# Atlas Makefile — quick commands for development & deployment

.PHONY: help venv install test lint format run docker docker-build docker-run clean

help:
	@echo "Atlas — Semantic Space Control Panel"
	@echo ""
	@echo "Available targets:"
	@echo "  make venv          Create Python virtual environment"
	@echo "  make install       Install dependencies (dev + main)"
	@echo "  make test          Run pytest suite (tests/)"
	@echo "  make lint          Run ruff + black check"
	@echo "  make format        Format code with black + isort"
	@echo "  make run           Run API server (uvicorn :8010)"
	@echo "  make docker        Build Docker image"
	@echo "  make docker-run    Run Docker container (:8010)"
	@echo "  make clean         Remove cache, venv, __pycache__"
	@echo ""

venv:
	python3 -m venv venv
	@echo "✅ Virtual environment created. Activate with: source venv/bin/activate"

install: venv
	./venv/bin/pip install -e .[dev]
	@echo "✅ Dependencies installed"

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

.DEFAULT_GOAL := help
