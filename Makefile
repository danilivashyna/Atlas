.PHONY: help setup install dev test lint format api api-docs bench clean

help:
	@echo "Atlas - Semantic Space Control Panel"
	@echo ""
	@echo "Commands:"
	@echo "  make setup          - Setup virtual environment"
	@echo "  make install        - Install dependencies"
	@echo "  make dev            - Install with dev dependencies"
	@echo "  make test           - Run tests (pytest)"
	@echo "  make lint           - Run linters (ruff, mypy)"
	@echo "  make format         - Format code (black)"
	@echo "  make api            - Start dev API server"
	@echo "  make api-docs       - Open API docs (after 'make api')"
	@echo "  make bench          - Run benchmarks"
	@echo "  make clean          - Clean build artifacts"
	@echo ""

setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -U pip wheel
	@echo "✓ Virtual environment created. Activate with: source .venv/bin/activate"

install:
	pip install -U pip wheel
	pip install -r requirements.txt
	pip install -e .

dev: install
	pip install pytest pytest-cov black ruff mypy

test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ -v --cov=src/atlas --cov-report=term-missing

lint:
	ruff check src/ tests/
	mypy src/atlas || true

format:
	black src/ tests/ examples/ --line-length=88

api:
	uvicorn src.atlas.api.app:app --reload --host 0.0.0.0 --port 8000

api-docs:
	open http://localhost:8000/docs

bench:
	python scripts/benchmark_hierarchical.py

clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

.DEFAULT_GOAL := help
