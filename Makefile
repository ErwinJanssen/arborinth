.PHONY: help install test lint format clean coverage

help:
	@echo "Arborinth Development Targets"
	@echo "==========================="
	@echo ""
	@echo "install   - Install the package in development mode"
	@echo "test      - Run all tests"
	@echo "test-cov  - Run tests with coverage"
	@echo "lint      - Run linting checks"
	@echo "format    - Format code"
	@echo "clean     - Remove build and test artifacts"
	@echo "coverage  - Show coverage report"
	@echo ""

install:
	pip install -e ".[dev]"

test:
	pytest -v

test-cov:
	pytest --cov=src/arborinth --cov-report=term-missing -v

lint:
	ruff check src/ tests/
	mypy src/

format:
	ruff check --fix src/ tests/
	ruff format src/ tests/

coverage:
	pytest --cov=src/arborinth --cov-report=term-missing --cov-report=html -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
