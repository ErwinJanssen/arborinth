.PHONY: help install test lint format clean

help:
	@echo "Arborinth Development Targets"
	@echo "==========================="
	@echo ""
	@echo "install - Install the package in development mode"
	@echo "test    - Run all tests"
	@echo "lint    - Run linting checks"
	@echo "format  - Format code"
	@echo "clean   - Remove build and test artifacts"
	@echo ""

install:
	pip install -e ".[dev]"

test:
	pytest -v

lint:
	ruff check src/ tests/
	mypy src/

format:
	ruff check --fix src/ tests/
	ruff format src/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
